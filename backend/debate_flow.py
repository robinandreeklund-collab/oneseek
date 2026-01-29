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
        
        # Debate state
        self.current_round = 0
        self.chain_so_far = []  # Responses in current round
        self.full_previous_round = []  # Complete previous round
        self.debate_history = []  # All rounds history
        self.oneseek_analyses = []  # OneSeek internal analyses
        self.facts = []  # Shared facts accumulated from tools
        
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

    def start_new_round(self, round_number: int):
        """
        Start a new debate round with clean state.
        
        Args:
            round_number: Round number (1, 2, or 3)
        """
        self.current_round = round_number
        
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
        - OneSeek: gets internal web search knowledge building
        
        Round 2 & 3:
        - All models: user query + SUMMARY of full_previous_round + limited chain_so_far
        - OneSeek: also gets internal analysis from previous rounds
        
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
        
        # Add user query
        context_parts.append(f"Användares fråga: {user_query}\n")
        
        # Add facts if available - ONLY for OneSeek and limited to last 5
        # Note: These are facts explicitly gathered by the Agent via debater_web_search
        # STRICT ISOLATION: Only share facts with OneSeek (to support synthesis)
        if self.facts and model_key == "oneseek-local":
            context_parts.append("\n**Verifierade Fakta (senaste 5):**\n")
            for fact in self.facts[-5:]:  # Last 5 facts to keep context small
                context_parts.append(f"- {fact['content']}\n")
        
        # Add OneSeek's internal analyses - ONLY for OneSeek
        if model_key == "oneseek-local" and self.oneseek_analyses:
            context_parts.append("\n**Dina Interna Analyser:**\n")
            for analysis in self.oneseek_analyses[-2:]:  # Last 2 analyses to keep context manageable
                context_parts.append(f"- Runda {analysis['round']}: ")
                context_parts.append(f"{len(analysis['claims_extracted'])} påståenden, ")
                context_parts.append(f"{len(analysis['verified_facts'])} verifieringar, ")
                context_parts.append(f"{len(analysis['contradictions'])} motsättningar\n")
                
                # Add synthesis points
                if analysis.get('synthesis_points'):
                    for point in analysis['synthesis_points'][:3]:
                        context_parts.append(f"  • {point}\n")
        
        # Add instruction to include name
        context_parts.append(f"\nVIKTIGT: Inled ditt svar med ditt namn: **{model_key}** (eller ditt displaynamn).\n")
        
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
                context_parts.append(f"\nDitt svar (på {language}, max 500 tokens):")
        
        # Round 2 & 3: FIXED - Use SUMMARY instead of full previous round
        else:
            if self.full_previous_round:
                prev_round = self.current_round - 1
                # CRITICAL FIX: Summarize instead of including full responses
                summary = self._summarize_round(self.full_previous_round)
                context_parts.append(f"\n**Sammanfattning av Runda {prev_round}:**\n")
                context_parts.append(summary)
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
            
            # Round 3 specific instructions for OneSeek
            if self.current_round == 3 and model_key == "oneseek-local":
                context_parts.append(f"\nDetta är runda 3 och din sista chans att ge ett syntetiserat svar.")
                context_parts.append(f"Du har tillgång till sammanfattningar av tidigare argument och dina interna analyser.")
                context_parts.append(f"Skapa ditt bästa, mest genomtänkta svar som väger alla perspektiv.")
            else:
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
        
        SPECIAL: For OneSeek in Round 1, performs web search first to build knowledge.
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
            
            # SPECIAL: OneSeek does web search in Round 1 before responding (internal knowledge building)
            if model_key == "oneseek-local" and self.current_round == 1 and self.search_tool:
                logger.info(f"OneSeek performing internal web search before Round 1 response")
                try:
                    # Perform web search for knowledge building (NOT shared with external models)
                    search_results = await asyncio.wait_for(
                        asyncio.to_thread(self.search_tool.invoke, user_query),
                        timeout=5.0
                    )
                    
                    # Store search knowledge internally for OneSeek (NOT in self.facts - that's shared)
                    # CRITICAL: Aggressively limit to prevent context explosion (max ~500 chars = ~125 tokens)
                    search_summary = self._summarize_search_results(search_results, max_chars=500)
                    logger.info(f"OneSeek built internal knowledge from web search ({len(search_summary)} chars): {search_summary[:100]}...")
                    
                    # We'll add this to the context below
                    oneseek_internal_knowledge = search_summary
                except asyncio.TimeoutError:
                    logger.warning("Web search timeout for OneSeek internal knowledge building")
                    oneseek_internal_knowledge = None
                except Exception as e:
                    logger.warning(f"Web search error for OneSeek: {e}")
                    oneseek_internal_knowledge = None
            else:
                oneseek_internal_knowledge = None
            
            # Build context for this model
            context = self.build_context_for_model(model_key, user_query, locale)
            
            # Add OneSeek's internal knowledge if available (Round 1 only)
            # SAFETY: Double-check size before adding to prevent context explosion
            if oneseek_internal_knowledge and model_key == "oneseek-local":
                # Count tokens in internal knowledge
                knowledge_tokens = self._count_tokens(oneseek_internal_knowledge)
                if knowledge_tokens > 200:
                    # Still too large, truncate further
                    logger.warning(f"Internal knowledge still large ({knowledge_tokens} tokens), truncating further")
                    # Aggressively truncate to max 150 tokens (~600 chars)
                    oneseek_internal_knowledge = oneseek_internal_knowledge[:600]
                    knowledge_tokens = self._count_tokens(oneseek_internal_knowledge)
                
                logger.info(f"Adding internal knowledge to context ({knowledge_tokens} tokens)")
                context += f"\n\n**Din Interna Kunskapsbyggande (endast för dig, delas EJ):**\n{oneseek_internal_knowledge}\n"
            
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
            messages = [HumanMessage(content=context)]
            response = await model.ainvoke(messages)
            
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
                "context_used": context
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
        1. Analyzing all responses from external models
        2. Finding claims made by each model
        3. Verifying data and claims via web search
        4. Analyzing how external models' responses change through different rounds
        5. Creating synthesis between answers for OneSeek's own response
        6. Addressing others with verified data
        
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
            "insights": [],
            "claims_extracted": [],
            "verified_facts": [],
            "contradictions": [],
            "synthesis_points": [],
            "evolution_notes": []
        }
        
        # Analyze each response from external models
        for resp in current_responses:
            if resp.get("error") or resp["model"] == "oneseek-local":
                continue  # Skip errors and OneSeek's own responses
                
            insight = {
                "model": resp["display_name"],
                "model_key": resp["model"],
                "response_snippet": resp["response"][:300] + "..." if len(resp["response"]) > 300 else resp["response"],
                "checks": [],
                "claims": [],
                "verification_results": []
            }
            
            # 1. Extract key claims from the response
            claims = self._extract_claims(resp["response"])
            insight["claims"] = claims
            analysis["claims_extracted"].extend([{
                "model": resp["display_name"],
                "claim": claim
            } for claim in claims])
            
            analysis["insights"].append(insight)
        
        # 2. Verify only 2-3 TOTAL claims across all models (not per model)
        # Prioritize claims from different models for diversity
        if self.search_tool and analysis["claims_extracted"]:
            # Select up to 3 claims, trying to get one from each model
            claims_to_verify = []
            models_covered = set()
            
            # First pass: get one claim per model (up to 3 models)
            for claim_data in analysis["claims_extracted"]:
                if len(claims_to_verify) >= 3:
                    break
                if claim_data["model"] not in models_covered:
                    claims_to_verify.append(claim_data)
                    models_covered.add(claim_data["model"])
            
            # Second pass: fill remaining slots if we have less than 3
            if len(claims_to_verify) < 3:
                for claim_data in analysis["claims_extracted"]:
                    if len(claims_to_verify) >= 3:
                        break
                    if claim_data not in claims_to_verify:
                        claims_to_verify.append(claim_data)
            
            logger.info(f"Verifying {len(claims_to_verify)} claims total (limit: 2-3 across all models)")
            
            # Verify the selected claims
            for claim_data in claims_to_verify:
                try:
                    claim = claim_data["claim"]
                    model_name = claim_data["model"]
                    search_query = f"{claim} fact check verify"
                    
                    # Web search for verification
                    search_results = await asyncio.wait_for(
                        asyncio.to_thread(self.search_tool.invoke, search_query),
                        timeout=5.0
                    )
                    
                    verification = {
                        "claim": claim,
                        "search_query": search_query[:100],
                        "results_count": len(search_results) if isinstance(search_results, list) else 1,
                        "results_summary": self._summarize_search_results(search_results, max_chars=300)
                    }
                    
                    # Find the corresponding insight and add verification
                    for insight in analysis["insights"]:
                        if insight["model"] == model_name:
                            insight["verification_results"].append(verification)
                            insight["checks"].append({
                                "type": "web_search_verification",
                                "query": search_query[:100],
                                "results_count": verification["results_count"]
                            })
                            break
                    
                    analysis["verified_facts"].append({
                        "model": model_name,
                        "claim": claim,
                        "verification": verification["results_summary"]
                    })
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Web search timeout during claim verification: {claim[:50]}")
                except Exception as e:
                    logger.warning(f"Web search error during claim verification: {e}")
        
        # 3. Analyze evolution across rounds (compare with previous rounds)
        if len(self.debate_history) > 0 and self.current_round > 1:
            evolution_analysis = self._analyze_response_evolution(current_responses)
            analysis["evolution_notes"] = evolution_analysis
        
        # 4. Find contradictions between models
        contradictions = self._find_contradictions(current_responses)
        analysis["contradictions"] = contradictions
        
        # 5. Create synthesis points for OneSeek's response
        synthesis = self._create_synthesis_points(current_responses, analysis["verified_facts"])
        analysis["synthesis_points"] = synthesis
        
        self.oneseek_analyses.append(analysis)
        logger.info(f"Internal analysis complete: {len(analysis['insights'])} insights, "
                   f"{len(analysis['claims_extracted'])} claims, "
                   f"{len(analysis['verified_facts'])} verifications, "
                   f"{len(analysis['contradictions'])} contradictions")
        
        return analysis
    
    def _extract_claims(self, response: str) -> List[str]:
        """
        Extract key factual claims from a response.
        Simple heuristic: split by sentences and filter for statements.
        
        Args:
            response: The response text
            
        Returns:
            List of extracted claims
        """
        import re
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', response)
        claims = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            # Filter for substantial sentences (>30 chars) that contain factual indicators
            if len(sentence) > 30 and any(word in sentence.lower() for word in 
                ['är', 'visar', 'bevisar', 'indikerar', 'forskning', 'studie', 'data', 
                 'is', 'shows', 'proves', 'indicates', 'research', 'study']):
                claims.append(sentence)
                if len(claims) >= 5:  # Limit to top 5 claims per response
                    break
        
        return claims
    
    def _summarize_search_results(self, search_results: Any, max_chars: int = 500) -> str:
        """
        Summarize search results into a brief verification note.
        
        CRITICAL: Aggressively limits output size to prevent context explosion.
        
        Args:
            search_results: Results from web search
            max_chars: Maximum characters to return (default: 500)
            
        Returns:
            Summary string (guaranteed to be <= max_chars)
        """
        if isinstance(search_results, list):
            if len(search_results) > 0:
                # Build summary from multiple results, limited to max_chars total
                summary_parts = []
                remaining_chars = max_chars - 50  # Reserve space for prefix
                
                for idx, result in enumerate(search_results[:3]):  # Max 3 results
                    if remaining_chars <= 0:
                        break
                        
                    if isinstance(result, dict):
                        # Try to get title and content, but limit each
                        title = result.get('title', '')[:100]
                        content = result.get('content', '')[:200]
                        
                        if title and content:
                            part = f"{idx+1}. {title}: {content}"
                        elif title:
                            part = f"{idx+1}. {title}"
                        elif content:
                            part = f"{idx+1}. {content}"
                        else:
                            # Fallback: take first value that's a string
                            for v in result.values():
                                if isinstance(v, str) and len(v) > 10:
                                    part = f"{idx+1}. {v[:150]}"
                                    break
                            else:
                                continue
                        
                        if len(part) > remaining_chars:
                            part = part[:remaining_chars] + "..."
                        
                        summary_parts.append(part)
                        remaining_chars -= len(part) + 2  # +2 for newline
                
                if summary_parts:
                    result = "Sökresultat:\n" + "\n".join(summary_parts)
                else:
                    result = f"Hittade {len(search_results)} källor"
            else:
                result = "Inga resultat"
        else:
            # For non-list results, extract key info carefully
            # NEVER convert entire object to string - too dangerous
            if isinstance(search_results, dict):
                # Try to extract useful fields
                summary_text = ""
                for key in ['answer', 'content', 'text', 'results']:
                    if key in search_results:
                        val = search_results[key]
                        if isinstance(val, str):
                            summary_text = val[:max_chars]
                            break
                        elif isinstance(val, list) and len(val) > 0:
                            # Recursively summarize
                            return self._summarize_search_results(val, max_chars)
                
                if summary_text:
                    result = summary_text
                else:
                    result = f"Sökresultat tillgängligt ({len(search_results)} fält)"
            else:
                # Last resort: convert to string but with strict limit
                result = str(search_results)[:max_chars]
        
        # Final safety check: ensure we never exceed max_chars
        if len(result) > max_chars:
            result = result[:max_chars] + "..."
        
        return result
    
    def _analyze_response_evolution(self, current_responses: List[Dict[str, Any]]) -> List[str]:
        """
        Analyze how models' positions have evolved across rounds.
        
        Args:
            current_responses: Current round responses
            
        Returns:
            List of evolution notes
        """
        evolution_notes = []
        
        # Compare current responses with previous rounds
        if len(self.debate_history) > 0:
            prev_round = self.debate_history[-1]
            prev_responses = {r["model"]: r for r in prev_round["responses"]}
            
            for curr_resp in current_responses:
                if curr_resp["model"] in prev_responses:
                    prev_resp = prev_responses[curr_resp["model"]]
                    # Simple comparison: check if response length or content changed significantly
                    if abs(len(curr_resp["response"]) - len(prev_resp["response"])) > 200:
                        evolution_notes.append(
                            f"{curr_resp['display_name']} ändrade sin position betydligt "
                            f"(från {len(prev_resp['response'])} till {len(curr_resp['response'])} tecken)"
                        )
        
        return evolution_notes
    
    def _find_contradictions(self, responses: List[Dict[str, Any]]) -> List[str]:
        """
        Find potential contradictions between model responses.
        Simple heuristic: look for opposing keywords.
        
        Args:
            responses: List of responses
            
        Returns:
            List of contradiction notes
        """
        contradictions = []
        
        # Look for opposing statements
        opposing_pairs = [
            ('ja', 'nej'),
            ('sant', 'falskt'),
            ('korrekt', 'inkorrekt'),
            ('bra', 'dåligt'),
            ('yes', 'no'),
            ('true', 'false'),
            ('correct', 'incorrect'),
            ('good', 'bad'),
        ]
        
        for i, resp1 in enumerate(responses):
            for j, resp2 in enumerate(responses[i+1:], i+1):
                # Check for opposing keywords
                for word1, word2 in opposing_pairs:
                    if word1 in resp1["response"].lower() and word2 in resp2["response"].lower():
                        contradictions.append(
                            f"Möjlig motsättning mellan {resp1['display_name']} och {resp2['display_name']} "
                            f"om '{word1}' vs '{word2}'"
                        )
                        break
        
        return contradictions[:5]  # Limit to top 5
    
    def _create_synthesis_points(
        self, 
        responses: List[Dict[str, Any]], 
        verified_facts: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Create synthesis points from all responses and verified facts.
        
        Args:
            responses: All responses in current round
            verified_facts: Verified facts from web search
            
        Returns:
            List of synthesis points
        """
        synthesis = []
        
        # Group common themes
        synthesis.append(f"Totalt {len(responses)} perspektiv analyserade i denna runda")
        
        # Summarize verified facts
        if verified_facts:
            synthesis.append(f"{len(verified_facts)} påståenden verifierade via webbsökning")
        
        # Note consensus or disagreement
        if len(responses) > 2:
            synthesis.append(
                "Identifierade gemensamma teman och skillnader mellan modellernas perspektiv"
            )
        
        return synthesis

    async def collect_votes(
        self,
        user_query: str,
        round_3_responses: List[Dict[str, Any]]
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
        voting_context += "Du får INTE rösta på ditt eget svar. Ge endast nummret."
        
        # Log voting context size for monitoring
        token_count = self._count_tokens(voting_context)
        logger.info(f"Voting context: {token_count} tokens (adjusted for 95K model)")
        
        if token_count > 10000:
            logger.warning(f"⚠️ Voting context large: {token_count} tokens")
        
        # Ask each model to vote (including OneSeek, per user request)
        available_models = list(self.models.keys())
        
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
                
                logger.info(f"Asking {display_name} to vote")
                
                messages = [HumanMessage(content=vote_prompt)]
                # Disable callbacks to prevent streaming to UI for internal calls
                # Also truncate prompt significantly if needed, or rely on model to handle it
                # Note: For VLLM, extremely long prompts can cause OOM. We already truncated context above.
                response = await model.ainvoke(messages, config={"callbacks": []})
                vote_text = response.content if hasattr(response, "content") else str(response)
                
                # Extract vote number (enhanced regex to handle various formats like "Jag röstar på [3]", "Vote: 2", etc.)
                import re
                vote_match = re.search(r'(?:\[|\b)(\d+)(?:\]|\b)', vote_text)
                
                vote_parsed = "Unknown"
                if vote_match:
                    vote_idx = int(vote_match.group(1))
                    
                    # Prevent self-voting
                    if vote_idx == model_idx:
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
                
                vote_details.append({
                    "voter": display_name,
                    "vote": vote_parsed,
                    "raw_response": vote_text[:100]
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


# Global instance (will be created when needed)
_debate_flow_instance = None


def get_debate_flow(max_search_results: int = 3, resources: List[Any] = None) -> DebateFlow:
    """Get or create the global debate flow instance."""
    global _debate_flow_instance
    if _debate_flow_instance is None:
        _debate_flow_instance = DebateFlow(max_search_results, resources)
    return _debate_flow_instance
