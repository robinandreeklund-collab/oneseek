# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Multi-Round Debate Engine for DeerFlow

Implements a 3-round debate where all AI models (including OneSeek) participate as equal debaters.
Each model responds sequentially in a randomized order, with strict context control between rounds.
After round 3, external models vote on the best answer.
"""

import asyncio
import logging
import os
import random
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from backend.deer_flow.tools import get_web_search_tool, get_retriever_tool
from backend.deer_flow.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)


# Model configurations for debate (reuse from AI comparison)
DEBATE_MODELS = {
    "gpt-3.5-turbo": {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "display_name": "GPT-3.5 (OpenAI)",
    },
    "gemini-2.5-flash": {
        "provider": "google",
        "model": "gemini-2.5-flash",
        "display_name": "Gemini 2.5 Flash (Google)",
    },
    "deepseek-chat": {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "display_name": "DeepSeek Chat",
    },
    "grok-4-fast-reasoning": {
        "provider": "xai",
        "model": "grok-4-fast-reasoning",
        "display_name": "Grok-4 Fast Reasoning (xAI)",
    },
    "oneseek-local": {
        "provider": "local",
        "model": "local",
        "display_name": "OneSeek",
        "is_oneseek": True,  # Mark OneSeek for special handling
    },
}


class DebateFlow:
    """
    Manages multi-round debate with sequential chain-of-thought flow.
    
    Features:
    - 3 debate rounds with randomized model order
    - Sequential responses with chain_so_far accumulation
    - Strict context control between rounds
    - OneSeek internal analysis between responses
    - OneSeek synthesis in round 3
    - External model voting after round 3
    """

    def __init__(self, max_search_results: int = 3, resources: List[Any] = None):
        """Initialize debate flow with configured models and tools."""
        self.models = self._initialize_models()
        self.search_tool = None
        self.retriever_tool = None
        self.max_search_results = max_search_results
        self.debater_search_calls: dict[int, int] = {}
        
        # Debate state
        self.current_round = 0
        self.chain_so_far = []  # Responses in current round
        self.full_previous_round = []  # Complete previous round
        self.debate_history = []  # All rounds history
        self.oneseek_analyses = []  # OneSeek internal analyses
        self.facts = []  # Shared facts accumulated from tools
        self.internal_fact_checks = []  # Internal fact-check summaries per round
        self.internal_summaries = []  # Internal synthesis summaries per round
        self.oneseek_round1_presearch_done = False
        self.search_cache = {}
        self.crawl_cache = {}
        self.context_by_tool_call_id = {}
        
        # Token counting for context monitoring
        self.token_encoder = None
        try:
            import tiktoken
            self.token_encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
            logger.info("Token encoder initialized for context monitoring")
        except Exception as e:
            logger.warning(f"tiktoken not available, using character-based estimation: {e}")
        
        # Initialize tools
        try:
            self.search_tool = get_web_search_tool(max_search_results=max_search_results)
            logger.info("Web search tool initialized for debate")
        except Exception as e:
            logger.warning(f"Could not initialize web search tool: {e}")
        
        try:
            if resources:
                self.retriever_tool = get_retriever_tool(resources=resources)
                logger.info("Retriever tool initialized for debate")
        except Exception as e:
            logger.warning(f"Could not initialize retriever tool: {e}")

    def update_search_settings(self, max_search_results: int, resources: List[Any] | None = None) -> None:
        """Update debate tools when UI settings or resources change."""
        if max_search_results and max_search_results != self.max_search_results:
            self.max_search_results = max_search_results
            try:
                self.search_tool = get_web_search_tool(max_search_results=max_search_results)
                logger.info("Debate web search tool updated (max_results=%s)", max_search_results)
            except Exception as e:
                logger.warning(f"Could not update web search tool: {e}")
        if resources is not None:
            try:
                if resources:
                    self.retriever_tool = get_retriever_tool(resources=resources)
                    logger.info("Debate retriever tool updated")
                else:
                    self.retriever_tool = None
            except Exception as e:
                logger.warning(f"Could not update retriever tool: {e}")

    def _initialize_models(self) -> Dict[str, Any]:
        """Initialize available AI models based on API keys."""
        models = {}
        
        # GPT-3.5 Turbo (OpenAI)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                models["gpt-3.5-turbo"] = ChatOpenAI(
                    model="gpt-3.5-turbo",
                    api_key=openai_key,
                    temperature=0.7,
                    max_tokens=2048,
                )
                logger.info("GPT-3.5 Turbo model initialized for debate")
            except Exception as e:
                logger.warning(f"Failed to initialize GPT-3.5 Turbo: {e}")
        
        # Gemini 2.5 Flash (Google)
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            try:
                models["gemini-2.5-flash"] = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash",
                    google_api_key=google_key,
                    temperature=0.7,
                    max_tokens=2048,
                )
                logger.info("Gemini 2.5 Flash model initialized for debate")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini 2.5 Flash: {e}")
        
        # DeepSeek Chat
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_key:
            try:
                models["deepseek-chat"] = ChatDeepSeek(
                    model="deepseek-chat",
                    api_key=deepseek_key,
                    temperature=0.7,
                    max_tokens=2048,
                )
                logger.info("DeepSeek Chat model initialized for debate")
            except Exception as e:
                logger.warning(f"Failed to initialize DeepSeek Chat: {e}")
        
        # Grok-4 Fast Reasoning (xAI)
        xai_key = os.getenv("XAI_API_KEY")
        xai_base_url = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
        if xai_key:
            try:
                models["grok-4-fast-reasoning"] = ChatOpenAI(
                    model="grok-4-fast-reasoning",
                    api_key=xai_key,
                    base_url=xai_base_url,
                    temperature=0.7,
                    max_tokens=2048,
                )
                logger.info("Grok-4 Fast Reasoning model initialized for debate")
            except Exception as e:
                logger.warning(f"Failed to initialize Grok-4 Fast Reasoning: {e}")
        
        # OneSeek Local - this will be handled via tools, not directly
        # It needs access to web search and internal analysis
        try:
            local_llm = get_llm_by_type("basic")
            models["oneseek-local"] = local_llm
            model_name = getattr(local_llm, 'model_name', 'unknown')
            logger.info(f"OneSeek model initialized for debate: {model_name}")
        except Exception as e:
            logger.warning(f"Failed to initialize OneSeek: {e}")
            try:
                vllm_url = os.getenv("VLLM_URL", "http://localhost:8000/v1")
                vllm_model = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ")
                models["oneseek-local"] = ChatOpenAI(
                    base_url=vllm_url,
                    api_key="EMPTY",
                    model=vllm_model,
                    temperature=0.7,
                    max_tokens=2048,
                )
                logger.info(f"OneSeek model initialized from environment: {vllm_model}")
            except Exception as e2:
                logger.warning(f"Failed to initialize OneSeek from environment: {e2}")
        
        return models

    def get_randomized_order(self) -> List[str]:
        """
        Get randomized order of all available models (including OneSeek).
        OneSeek is treated as an equal participant, no special ordering.
        """
        available_models = list(self.models.keys())
        random.shuffle(available_models)
        logger.info(f"Round {self.current_round} order: {available_models}")
        return available_models

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text for context monitoring.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        if self.token_encoder:
            try:
                return len(self.token_encoder.encode(text))
            except Exception as e:
                logger.debug(f"Token encoding failed: {e}, using fallback")
        
        # Fallback: 1 token ≈ 4 characters (rough estimate)
        return len(text) // 4
    
    def _summarize_round(self, responses: List[Dict[str, Any]]) -> str:
        """
        Summarize a round's responses to reduce context size.
        
        Takes first 300 chars (~75 tokens) from each response to create
        a summary. With 95K token context, we can be less aggressive.
        
        Args:
            responses: List of response dicts from a round
            
        Returns:
            Summarized text for context
        """
        summary_parts = []
        for resp in responses:
            if not resp.get("error"):
                # Take first 300 chars (increased from 150 for better quality with 95K context)
                snippet = resp['response'][:300]
                if len(resp['response']) > 300:
                    snippet += "..."
                summary_parts.append(f"- **{resp['display_name']}**: {snippet}")
        
        summary = "\n".join(summary_parts)
        token_count = self._count_tokens(summary)
        logger.debug(f"Round summary created: {len(responses)} responses → {token_count} tokens")
        
        return summary

    def _truncate_internal(self, content: str, max_chars: int = 1400) -> str:
        """Truncate internal context to keep prompts bounded."""
        cleaned = content.strip() if isinstance(content, str) else str(content)
        if len(cleaned) > max_chars:
            return cleaned[:max_chars] + "... [trunkerat]"
        return cleaned

    def add_internal_fact_check(self, round_number: int, content: str) -> None:
        """Store internal fact-check results for a round."""
        entry = {
            "round": round_number,
            "content": self._truncate_internal(content, max_chars=1400),
        }
        self.internal_fact_checks.append(entry)
        # Keep last few entries
        if len(self.internal_fact_checks) > 6:
            self.internal_fact_checks = self.internal_fact_checks[-6:]

    def add_internal_summary(self, round_number: int, content: str) -> None:
        """Store internal synthesis summary for a round."""
        entry = {
            "round": round_number,
            "content": self._truncate_internal(content, max_chars=1400),
        }
        self.internal_summaries.append(entry)
        if len(self.internal_summaries) > 6:
            self.internal_summaries = self.internal_summaries[-6:]

    def _format_search_results(self, results: Any, max_items: int = 3) -> str:
        """Format search results into short bullets."""
        if not results:
            return ""
        items = results if isinstance(results, list) else [results]
        bullets = []
        for item in items[:max_items]:
            if isinstance(item, dict):
                title = item.get("title") or item.get("name") or "Källa"
                url = item.get("url") or item.get("link") or ""
                snippet = item.get("content") or item.get("snippet") or ""
                snippet = snippet[:200] + "..." if len(snippet) > 200 else snippet
                bullet = f"- {title} ({url}) {snippet}".strip()
            else:
                bullet = str(item)[:240]
            bullets.append(bullet)
        return "\n".join(bullets)

    async def run_oneseek_round1_presearch(self, user_query: str) -> str:
        """Run a lightweight internal web search before OneSeek's first response."""
        if not self.search_tool:
            return ""
        max_calls = int(os.getenv("DEBATE_WEB_SEARCH_MAX_CALLS", "3"))
        if not self.record_debate_search(self.current_round or 1, max_calls):
            logger.info("Debate search limit reached; skipping round 1 presearch")
            return ""
        try:
            search_results = await asyncio.wait_for(
                asyncio.to_thread(self.cached_web_search, user_query, self.current_round),
                timeout=5.0,
            )
            formatted = self._format_search_results(search_results, max_items=3)
            return self._truncate_internal(formatted, max_chars=900)
        except Exception as e:
            logger.warning(f"Round 1 presearch failed: {e}")
            return ""

    def cached_web_search(self, query: str, round_number: int) -> Any:
        """Cache web search results per round/query."""
        cache_key = f"{round_number}:{query.strip().lower()}"
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        if not self.search_tool:
            return []
        result = self.search_tool.invoke(query)
        self.search_cache[cache_key] = result
        return result

    def cached_crawl(self, url: str, round_number: int) -> Any:
        """Cache crawl results per round/url."""
        cache_key = f"{round_number}:{url.strip().lower()}"
        if cache_key in self.crawl_cache:
            return self.crawl_cache[cache_key]
        from backend.deer_flow.tools import crawl_tool
        result = crawl_tool.invoke(url)
        self.crawl_cache[cache_key] = result
        return result

    def store_tool_context(self, tool_call_id: str, context: str, max_chars: int = 120000) -> None:
        """Store full context for later retrieval."""
        if not tool_call_id:
            return
        context_text = context or ""
        if len(context_text) > max_chars:
            context_text = context_text[:max_chars] + "... [trunkerat]"
        self.context_by_tool_call_id[tool_call_id] = context_text

    def get_tool_context(self, tool_call_id: str) -> str:
        """Retrieve stored tool context by tool_call_id."""
        return self.context_by_tool_call_id.get(tool_call_id, "")

    def _build_internal_context(self, up_to_round: int) -> str:
        """Build cumulative internal context up to a given round."""
        if up_to_round < 1:
            return ""

        parts: list[str] = []
        for round_number in range(1, up_to_round + 1):
            round_parts: list[str] = []
            for entry in self.internal_fact_checks:
                if entry.get("round") == round_number:
                    round_parts.append(f"Faktakontroll Runda {round_number}:\n{entry.get('content', '')}")
            for entry in self.internal_summaries:
                if entry.get("round") == round_number:
                    round_parts.append(f"Syntes Runda {round_number}:\n{entry.get('content', '')}")
            if round_parts:
                parts.append("\n".join(round_parts))

        return "\n\n".join(parts)

    def start_new_round(self, round_number: int):
        """
        Start a new debate round with clean state.
        
        Args:
            round_number: Round number (1, 2, or 3)
        """
        self.current_round = round_number
        self.debater_search_calls[round_number] = 0
        
        # Save previous round before clearing
        if self.chain_so_far:
            self.full_previous_round = list(self.chain_so_far)
            self.debate_history.append({
                "round": round_number - 1,
                "responses": list(self.chain_so_far)
            })
        
        # Clear chain for new round
        self.chain_so_far = []
        
        logger.info(f"Starting Round {round_number}")
        logger.info(f"Previous round had {len(self.full_previous_round)} responses")

    def reset(self):
        """Reset debate state for a new session."""
        self.current_round = 0
        self.chain_so_far = []
        self.full_previous_round = []
        self.debate_history = []
        self.oneseek_analyses = []
        self.facts = []
        self.internal_fact_checks = []
        self.internal_summaries = []
        self.oneseek_round1_presearch_done = False
        self.search_cache = {}
        self.crawl_cache = {}
        self.context_by_tool_call_id = {}
        self.debater_search_calls = {}
        logger.info("DebateFlow state reset")

    def record_debate_search(self, round_number: int, max_calls: int) -> bool:
        """Track and limit debate web_search calls per round."""
        if max_calls <= 0:
            return False
        current = self.debater_search_calls.get(round_number, 0)
        if current >= max_calls:
            return False
        self.debater_search_calls[round_number] = current + 1
        return True

    def add_fact(self, fact: str, source: str = "web_search"):
        """
        Add a verified fact to the debate context.
        This is used when the Agent explicitly calls `debater_web_search`.
        These facts ARE shared with all models to ground the debate.
        
        FIX: Limit fact size and array length to prevent context explosion.
        """
        # Truncate individual facts to prevent bloat
        if len(fact) > 500:
            fact = fact[:500] + "... [trunkerat för kontextbegränsning]"
            logger.debug(f"Truncated fact to 500 chars")
        
        self.facts.append({"content": fact, "source": source, "round": self.current_round})
        logger.info(f"Added fact to debate context: {fact[:50]}...")
        
        # Keep only last 10 facts to prevent unbounded growth
        if len(self.facts) > 10:
            removed_count = len(self.facts) - 10
            self.facts = self.facts[-10:]
            logger.info(f"Trimmed facts array: removed {removed_count} oldest facts, kept last 10")

    def build_context_for_model(
        self, 
        model_key: str, 
        user_query: str, 
        locale: str = "sv-SE"
    ) -> str:
        """
        Build context for a model based on round and position.
        
        FIXED: Uses summarization for previous rounds to prevent context explosion.
        
        Round 1:
        - First model: user query + language rule + token limit
        - Other models: user query + limited chain_so_far (last 3)
        
        Round 2 & 3:
        - All models: user query + SUMMARY of full_previous_round + limited chain_so_far
        
        Args:
            model_key: Model identifier
            user_query: Original user question
            locale: Language locale (default: sv-SE for Swedish)
            
        Returns:
            Context string for the model
        """
        # Determine language from locale
        language = "svenska" if locale.startswith("sv") else "engelska"
        
        context_parts = []
        
        # Load OneSeek's dedicated debate prompt
        if model_key == "oneseek-local":
            from backend.deer_flow.prompts.template import get_prompt_template
            try:
                oneseek_system = get_prompt_template("oneseek_debater", locale)
                context_parts.append(f"\n### Din Strategi och Regler:\n{oneseek_system}\n\n")
                logger.info(f"Loaded oneseek_debater prompt for {model_key}")
            except FileNotFoundError:
                logger.warning(f"oneseek_debater prompt not found for locale {locale}")
        
        # Add user query
        context_parts.append(f"Användares fråga: {user_query}\n")
        
        # Add facts if available - ONLY for OneSeek and limited to last 5
        # Note: These are facts explicitly gathered by the Agent via debater_web_search
        # STRICT ISOLATION: Only share facts with OneSeek (to support synthesis)
        if self.facts and model_key == "oneseek-local":
            context_parts.append("\n**Verifierade Fakta (senaste 5):**\n")
            for fact in self.facts[-5:]:  # Last 5 facts to keep context small
                context_parts.append(f"- {fact['content']}\n")
        
        # Add instruction to include name
        display_name = DEBATE_MODELS.get(model_key, {}).get("display_name", model_key)
        context_parts.append(f"\nVIKTIGT: Inled ditt svar med ditt namn: **{display_name}**.\n")
        if model_key == "oneseek-local":
            context_parts.append("Du är OneSeek. Var medveten om din roll som OneSeek-debattör.\n")
            context_parts.append("Du ska alltid ge ditt bästa möjliga svar i varje runda.\n")
        
        # Round 1: First model gets minimal context
        if self.current_round == 1:
            if not self.chain_so_far:
                context_parts.append(f"Du deltar i en debatt med flera AI-modeller.")
                context_parts.append(f"Detta är runda 1. Du är först att svara.")
                context_parts.append(f"Svara på {language} och håll ditt svar under 500 tokens.")
                context_parts.append(f"Ge ett genomtänkt och välunderbyggt svar på frågan.")
            else:
                # FIXED: Limit to last 5 responses (increased from 3 for 95K context)
                recent = self.chain_so_far[-5:]
                context_parts.append(f"\nDetta är runda 1. Senaste {len(recent)} svar:\n")
                for resp in recent:
                    # Truncate to 500 chars (increased from 300 for better quality)
                    snippet = resp['response'][:500]
                    if len(resp['response']) > 500:
                        snippet += "..."
                    context_parts.append(f"\n{resp['display_name']}: {snippet}\n")
                context_parts.append(f"\nBemöt minst ett av ovanstående svar.")
                context_parts.append(f"\nDitt svar (på {language}, max 500 tokens):")
        
        # Round 2 & 3: Use full previous round + (internal results for OneSeek only)
        else:
            if self.full_previous_round:
                prev_round = self.current_round - 1
                context_parts.append(f"\n**Runda {prev_round} (fullständiga svar):**\n")
                for resp in self.full_previous_round:
                    if resp.get("error"):
                        continue
                    response_text = resp.get("response", "")
                    context_parts.append(f"\n{resp.get('display_name', resp.get('model', 'Model'))}: {response_text}\n")
                context_parts.append("\n")

            if model_key == "oneseek-local":
                internal_context = self._build_internal_context(self.current_round - 1)
                if internal_context:
                    context_parts.append("\n**Interna resultat (faktakontroll + syntes):**\n")
                    context_parts.append(internal_context)
                    context_parts.append("\n")
            
            # FIXED: Limit chain_so_far to last 5 responses (increased from 3)
            if self.chain_so_far:
                recent = self.chain_so_far[-5:]
                context_parts.append(f"\nRunda {self.current_round}, senaste {len(recent)} svar:\n")
                for resp in recent:
                    # Truncate to 500 chars (increased from 300)
                    snippet = resp['response'][:500]
                    if len(resp['response']) > 500:
                        snippet += "..."
                    context_parts.append(f"\n{resp['display_name']}: {snippet}\n")
                context_parts.append("\nBemöt minst ett svar från aktuell runda.")
            
            # Round 3 specific instructions for OneSeek
            if self.current_round == 3 and model_key == "oneseek-local":
                context_parts.append(f"\nDetta är runda 3 och din sista chans att ge ett syntetiserat svar.")
                context_parts.append(f"Du har tillgång till sammanfattningar av tidigare argument och dina interna analyser.")
                context_parts.append(f"Skapa ditt bästa, mest genomtänkta svar som väger alla perspektiv.")
            else:
                context_parts.append("Om relevant: referera till minst ett argument från föregående runda.")
                context_parts.append(f"\nDitt svar för runda {self.current_round} (på {language}, max 500 tokens):")
        
        context = "\n".join(context_parts)
        
        # NEW: Log token count for monitoring
        token_count = self._count_tokens(context)
        logger.info(f"Context for {model_key} round {self.current_round}: {token_count} tokens")
        
        # Warnings for large contexts (adjusted for 95K token model)
        if token_count > 50000:
            logger.error(f"⚠️ CRITICAL: Context {token_count} tokens exceeds 50K! Approaching limit!")
        elif token_count > 30000:
            logger.warning(f"⚠️ WARNING: Context {token_count} tokens exceeds 30K")
        
        return context

    async def query_model_in_debate(
        self,
        model_key: str,
        user_query: str,
        locale: str = "sv-SE"
    ) -> Dict[str, Any]:
        """
        Query a model with debate context.
        
        FIXED: Added context size guard to prevent VLLM crashes.
        """
        if model_key not in self.models:
            logger.warning(f"Model {model_key} not available")
            return {
                "model": model_key,
                "display_name": DEBATE_MODELS.get(model_key, {}).get("display_name", model_key),
                "response": f"Model {model_key} är inte tillgänglig.",
                "error": True,
                "context_used": "Model unavailable"
            }
        
        try:
            model = self.models[model_key]
            display_name = DEBATE_MODELS.get(model_key, {}).get("display_name", model_key)
            
            # Build context for this model
            context = self.build_context_for_model(model_key, user_query, locale)

            # Round 1: OneSeek performs an internal pre-search before its first response
            if model_key == "oneseek-local" and self.current_round == 1 and not self.oneseek_round1_presearch_done:
                presearch = await self.run_oneseek_round1_presearch(user_query)
                if presearch:
                    context += (
                        "\n\n**Intern webbsökning (endast OneSeek):**\n"
                        + presearch
                        + "\n"
                    )
                    self.add_internal_fact_check(1, presearch)
                self.oneseek_round1_presearch_done = True
            token_count = self._count_tokens(context)
            
            # Hard limit to prevent VLLM crashes (adjusted for 95K token model)
            # Keep safety margin: max 60K tokens (leaving 35K for response)
            if token_count > 60000:
                logger.error(f"Context too large ({token_count} tokens) for {model_key}, skipping")
                return {
                    "model": model_key,
                    "display_name": display_name,
                    "response": f"❌ Hoppades över: Kontexten ({token_count} tokens) överskrider gränsen på 60K tokens. Säkerhetsmarginal för 95K modell.",
                    "error": True,
                    "context_used": f"Context too large: {token_count} tokens"
                }
            
            logger.info(f"Querying {display_name} in round {self.current_round} (context: {token_count} tokens)")
            
            # Query the model
            import time
            start_time = time.monotonic()
            messages = [HumanMessage(content=context)]
            response = await model.ainvoke(messages)
            latency_ms = int((time.monotonic() - start_time) * 1000)
            
            response_text = response.content if hasattr(response, "content") else str(response)
            
            # Truncate if too long (enforce 500 token limit ~ 2000 chars)
            if len(response_text) > 2000:
                response_text = response_text[:2000] + "..."
            
            result = {
                "model": model_key,
                "display_name": display_name,
                "response": response_text,
                "round": self.current_round,
                "position": len(self.chain_so_far),
                "error": False,
                "context_used": context,
                "latency_ms": latency_ms,
                "tokens_in": token_count,
                "tokens_out": self._count_tokens(response_text),
            }
            
            # Add to chain_so_far
            self.chain_so_far.append(result)
            
            logger.info(f"{display_name} responded ({len(response_text)} chars)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error querying {model_key}: {e}")
            return {
                "model": model_key,
                "display_name": DEBATE_MODELS.get(model_key, {}).get("display_name", model_key),
                "response": f"Fel vid svar: {str(e)}",
                "round": self.current_round,
                "error": True,
                "context_used": "Error during query"
            }

    async def run_oneseek_internal_analysis(
        self,
        user_query: str,
        current_responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run OneSeek's internal analysis between responses.
        This analyzes other models' responses for:
        - Factual accuracy (via web search)
        - Logical consistency
        - Missing information
        - Potential counterarguments
        
        This analysis is NOT shared with other models, only used by OneSeek.
        
        Args:
            user_query: Original user question
            current_responses: Responses so far in current round
            
        Returns:
            Analysis results for OneSeek's use
        """
        logger.info(f"Running OneSeek internal analysis for round {self.current_round}")
        
        analysis = {
            "round": self.current_round,
            "timestamp": len(self.oneseek_analyses),
            "insights": []
        }
        
        # Analyze each response
        for resp in current_responses:
            if resp.get("error"):
                continue
                
            insight = {
                "model": resp["display_name"],
                "checks": []
            }
            
            # Use search_tool but DO NOT share results with other models in next round automatically
            # Only OneSeek uses this internal analysis.
            # We do NOT add to self.facts here.
            
            # Simple fact-check via web search if available
            if self.search_tool and len(resp["response"]) > 100:
                try:
                    max_calls = int(os.getenv("DEBATE_WEB_SEARCH_MAX_CALLS", "3"))
                    if not self.record_debate_search(self.current_round or 1, max_calls):
                        logger.info("Debate search limit reached; skipping internal analysis search")
                        break
                    # Extract key claims (simplified - just take first 200 chars)
                    claim = resp["response"][:200]
                    search_query = f"{user_query} {claim}"
                    
                    # Quick web search
                    search_results = await asyncio.wait_for(
                        asyncio.to_thread(self.cached_web_search, search_query, self.current_round),
                        timeout=5.0
                    )
                    
                    insight["checks"].append({
                        "type": "web_search",
                        "query": search_query[:100],
                        "results_count": len(search_results) if isinstance(search_results, list) else 1
                    })
                except asyncio.TimeoutError:
                    logger.warning("Web search timeout during internal analysis")
                except Exception as e:
                    logger.warning(f"Web search error during internal analysis: {e}")
            
            analysis["insights"].append(insight)
        
        self.oneseek_analyses.append(analysis)
        logger.info(f"Internal analysis complete: {len(analysis['insights'])} insights")
        
        return analysis

    async def collect_votes(
        self,
        user_query: str,
        round_3_responses: List[Dict[str, Any]],
        allowed_models: List[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Collect votes from external models on best answer from round 3.
        Models cannot vote for themselves.
        
        FIXED: Drastically reduced voting context to prevent VLLM crashes.
        Each response truncated to 300 chars instead of 1000.
        
        Args:
            user_query: Original user question
            round_3_responses: All responses from round 3
            
        Returns:
            Voting results with winner
        """
        logger.info("Collecting votes from external models")
        
        votes = {}
        vote_details = []
        
        # Build MINIMAL voting context (adjusted for 95K token model)
        voting_context = f"Fråga: {user_query}\n\nRunda 3 svar (sammanfattade):\n"
        
        for idx, resp in enumerate(round_3_responses):
            if not resp.get("error"):
                # Increased from 300 to 500 chars for better voting quality with 95K context
                response_text = resp['response']
                if len(response_text) > 500:
                    response_text = response_text[:500] + "... [fortsätter]"
                voting_context += f"\n[{idx}] {resp['display_name']}: {response_text}\n"
        
        voting_context += "\n\nRösta på det bästa svaret genom att ange numret [0-" + str(len(round_3_responses)-1) + "]. "
        voting_context += "Du får INTE rösta på ditt eget svar.\n"
        voting_context += "Svara i formatet:\n"
        voting_context += "Vote: [N]\n"
        voting_context += "Reasons:\n- punkt 1\n- punkt 2\n- punkt 3\n"
        
        # Log voting context size for monitoring
        token_count = self._count_tokens(voting_context)
        logger.info(f"Voting context: {token_count} tokens (adjusted for 95K model)")
        
        if token_count > 10000:
            logger.warning(f"⚠️ Voting context large: {token_count} tokens")
        
        # Ask each model to vote (including OneSeek)
        available_models = list(self.models.keys())
        if allowed_models:
            allowed_set = set(allowed_models)
            available_models = [m for m in available_models if m in allowed_set]

        def _tokenize(text: str) -> set[str]:
            import re
            return {t for t in re.findall(r"\b\w+\b", text.lower()) if len(t) > 2}

        def _closest_model_to_oneseek() -> str | None:
            oneseek_resp = None
            for resp in round_3_responses:
                if resp.get("model") == "oneseek-local":
                    oneseek_resp = resp.get("response", "")
                    break
            if not oneseek_resp:
                return None
            oneseek_tokens = _tokenize(oneseek_resp)
            best_model = None
            best_score = -1.0
            for resp in round_3_responses:
                model_key = resp.get("model")
                if not model_key or model_key == "oneseek-local":
                    continue
                response_text = resp.get("response", "")
                candidate_tokens = _tokenize(response_text)
                if not candidate_tokens:
                    continue
                score = len(oneseek_tokens & candidate_tokens) / max(len(oneseek_tokens | candidate_tokens), 1)
                if score > best_score:
                    best_score = score
                    best_model = model_key
            return best_model
        
        for model_key in available_models:
            if model_key not in self.models:
                continue
                
            try:
                model = self.models[model_key]
                display_name = DEBATE_MODELS.get(model_key, {}).get("display_name", model_key)
                
                # Find this model's index to prevent self-voting
                model_idx = None
                for idx, resp in enumerate(round_3_responses):
                    if resp["model"] == model_key:
                        model_idx = idx
                        break
                
                # Create voting prompt
                vote_prompt = voting_context
                if model_idx is not None:
                    vote_prompt += f" (Du är svar [{model_idx}], rösta inte på dig själv)"
                if model_key == "oneseek-local":
                    vote_prompt += (
                        "\nDu är OneSeek. Du FÅR INTE rösta på ditt eget svar. "
                        "Rösta istället på det svar som är mest likt ditt eget resonemang."
                    )
                
                logger.info(f"Asking {display_name} to vote")
                
                messages = [HumanMessage(content=vote_prompt)]
                # Disable callbacks to prevent streaming to UI for internal calls
                # Also truncate prompt significantly if needed, or rely on model to handle it
                # Note: For VLLM, extremely long prompts can cause OOM. We already truncated context above.
                response = await model.ainvoke(messages, config={"callbacks": []})
                vote_text = response.content if hasattr(response, "content") else str(response)
                
                # Extract vote number (enhanced regex to handle various formats)
                import re
                vote_match = re.search(r'(?:\[|\b)(\d+)(?:\]|\b)', vote_text)
                
                vote_parsed = "Unknown"
                if vote_match:
                    vote_idx = int(vote_match.group(1))
                    
                    # Prevent self-voting
                    if vote_idx == model_idx:
                        if model_key == "oneseek-local":
                            fallback_model = _closest_model_to_oneseek()
                            if fallback_model:
                                voted_for = DEBATE_MODELS.get(fallback_model, {}).get(
                                    "display_name", fallback_model
                                )
                                votes[voted_for] = votes.get(voted_for, 0) + 1
                                vote_parsed = voted_for
                                logger.warning(
                                    f"{display_name} self-vote redirected to closest model {voted_for}"
                                )
                            else:
                                logger.warning(f"{display_name} tried to vote for itself, invalidating")
                                vote_parsed = "INVALID (self-vote)"
                        else:
                            logger.warning(f"{display_name} tried to vote for itself, invalidating")
                            vote_parsed = "INVALID (self-vote)"
                    
                    # Valid vote
                    elif 0 <= vote_idx < len(round_3_responses):
                        voted_for = round_3_responses[vote_idx]["display_name"]
                        votes[voted_for] = votes.get(voted_for, 0) + 1
                        vote_parsed = voted_for
                        
                        logger.info(f"{display_name} voted for {voted_for}")
                    else:
                        logger.warning(f"{display_name} voted for invalid index {vote_idx}")
                        vote_parsed = f"INVALID (Index {vote_idx})"
                else:
                    logger.warning(f"{display_name} vote could not be parsed: {vote_text[:50]}")
                    vote_parsed = "Parse Error"
                
                # Extract up to 3 bullet-point reasons
                reasons = []
                for line in vote_text.splitlines():
                    cleaned = line.strip()
                    if cleaned.startswith(("-", "*")):
                        reasons.append(cleaned.lstrip("-* ").strip())
                    if len(reasons) >= 3:
                        break

                vote_details.append({
                    "voter": display_name,
                    "vote": vote_parsed,
                    "reasons": reasons,
                    "raw_response": vote_text[:200]
                })
                    
            except Exception as e:
                logger.error(f"Error collecting vote from {model_key}: {e}")
        
        # Determine winner
        winner = None
        max_votes = 0
        if votes:
            winner = max(votes, key=votes.get)
            max_votes = votes[winner]
        
        return {
            "votes": votes,
            "vote_details": vote_details,
            "winner": winner,
            "winner_votes": max_votes,
            "total_voters": len(vote_details),
            "voting_prompt": voting_context
        }


# Global instances per thread/session
_debate_flow_instances: Dict[str, DebateFlow] = {}


def get_debate_flow(
    max_search_results: int | None = None,
    resources: List[Any] | None = None,
    thread_id: str | None = None,
    reset: bool = False,
) -> DebateFlow:
    """Get or create a debate flow instance scoped to a thread/session."""
    global _debate_flow_instances
    thread_key = str(thread_id) if thread_id else "default"
    if thread_key not in _debate_flow_instances:
        init_max = max_search_results if isinstance(max_search_results, int) and max_search_results > 0 else 3
        _debate_flow_instances[thread_key] = DebateFlow(init_max, resources)
    elif reset:
        _debate_flow_instances[thread_key].reset()

    if max_search_results is not None or resources is not None:
        effective_max = (
            max_search_results
            if isinstance(max_search_results, int) and max_search_results > 0
            else _debate_flow_instances[thread_key].max_search_results
        )
        _debate_flow_instances[thread_key].update_search_settings(effective_max, resources)
    return _debate_flow_instances[thread_key]


def clear_debate_flow(thread_id: str | None = None) -> None:
    """Remove a debate flow instance (cleanup)."""
    global _debate_flow_instances
    thread_key = str(thread_id) if thread_id else "default"
    _debate_flow_instances.pop(thread_key, None)
