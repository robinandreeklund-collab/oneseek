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

    def build_context_for_model(
        self, 
        model_key: str, 
        user_query: str, 
        locale: str = "sv-SE"
    ) -> str:
        """
        Build context for a model based on round and position.
        
        Round 1:
        - First model: user query + language rule + token limit
        - Other models: user query + chain_so_far
        
        Round 2 & 3:
        - All models: user query + full_previous_round (+ chain_so_far for non-first)
        
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
        
        # Round 1: First model gets minimal context
        if self.current_round == 1:
            if not self.chain_so_far:
                context_parts.append(f"Du deltar i en debatt med flera AI-modeller.")
                context_parts.append(f"Detta är runda 1. Du är först att svara.")
                context_parts.append(f"Svara på {language} och håll ditt svar under 500 tokens.")
                context_parts.append(f"Ge ett genomtänkt och välunderbyggt svar på frågan.")
            else:
                context_parts.append(f"\nDetta är runda 1. Tidigare svar i denna runda:\n")
                for resp in self.chain_so_far:
                    context_parts.append(f"\n{resp['display_name']}: {resp['response']}\n")
                context_parts.append(f"\nDitt svar (på {language}, max 500 tokens):")
        
        # Round 2 & 3: Include previous round
        else:
            if self.full_previous_round:
                prev_round = self.current_round - 1
                context_parts.append(f"\nKomplett Runda {prev_round}:\n")
                for resp in self.full_previous_round:
                    context_parts.append(f"\n{resp['display_name']}: {resp['response']}\n")
            
            # Add current round so far if not first
            if self.chain_so_far:
                context_parts.append(f"\nRunda {self.current_round} hittills:\n")
                for resp in self.chain_so_far:
                    context_parts.append(f"\n{resp['display_name']}: {resp['response']}\n")
            
            # Round 3 specific instructions for OneSeek
            if self.current_round == 3 and model_key == "oneseek-local":
                context_parts.append(f"\nDetta är runda 3 och din sista chans att ge ett syntetiserat svar.")
                context_parts.append(f"Du har tillgång till alla tidigare argument och dina interna analyser.")
                context_parts.append(f"Skapa ditt bästa, mest genomtänkta svar som väger alla perspektiv.")
            else:
                context_parts.append(f"\nDitt svar för runda {self.current_round} (på {language}, max 500 tokens):")
        
        return "\n".join(context_parts)

    async def query_model_in_debate(
        self,
        model_key: str,
        user_query: str,
        locale: str = "sv-SE"
    ) -> Dict[str, Any]:
        """
        Query a model with debate context.
        
        Args:
            model_key: Model identifier
            user_query: Original user question
            locale: Language locale
            
        Returns:
            Dictionary with model response
        """
        if model_key not in self.models:
            logger.warning(f"Model {model_key} not available")
            return {
                "model": model_key,
                "display_name": DEBATE_MODELS.get(model_key, {}).get("display_name", model_key),
                "response": f"Model {model_key} är inte tillgänglig.",
                "error": True
            }
        
        try:
            model = self.models[model_key]
            display_name = DEBATE_MODELS.get(model_key, {}).get("display_name", model_key)
            
            # Build context for this model
            context = self.build_context_for_model(model_key, user_query, locale)
            
            logger.info(f"Querying {display_name} in round {self.current_round}")
            
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
                "error": False
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
                "error": True
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
            
            # Simple fact-check via web search if available
            if self.search_tool and len(resp["response"]) > 100:
                try:
                    # Extract key claims (simplified - just take first 200 chars)
                    claim = resp["response"][:200]
                    search_query = f"{user_query} {claim}"
                    
                    # Quick web search
                    search_results = await asyncio.wait_for(
                        asyncio.to_thread(self.search_tool.invoke, search_query),
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
        round_3_responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Collect votes from external models on best answer from round 3.
        Models cannot vote for themselves.
        
        Args:
            user_query: Original user question
            round_3_responses: All responses from round 3
            
        Returns:
            Voting results with winner
        """
        logger.info("Collecting votes from external models")
        
        votes = {}
        vote_details = []
        
        # Build voting context
        voting_context = f"Fråga: {user_query}\n\nRunda 3 svar:\n"
        for idx, resp in enumerate(round_3_responses):
            if not resp.get("error"):
                voting_context += f"\n[{idx}] {resp['display_name']}: {resp['response']}\n"
        
        voting_context += "\n\nRösta på det bästa svaret genom att ange numret [0-" + str(len(round_3_responses)-1) + "]. "
        voting_context += "Du får INTE rösta på ditt eget svar. Ge endast nummret."
        
        # Ask each external model to vote (not OneSeek)
        external_models = [k for k in self.models.keys() if k != "oneseek-local"]
        
        for model_key in external_models:
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
                response = await model.ainvoke(messages)
                vote_text = response.content if hasattr(response, "content") else str(response)
                
                # Extract vote number (simple regex)
                import re
                vote_match = re.search(r'\[?(\d+)\]?', vote_text)
                if vote_match:
                    vote_idx = int(vote_match.group(1))
                    
                    # Prevent self-voting
                    if vote_idx == model_idx:
                        logger.warning(f"{display_name} tried to vote for itself, invalidating")
                        vote_details.append({
                            "voter": display_name,
                            "vote": "INVALID (self-vote)",
                            "raw_response": vote_text[:100]
                        })
                        continue
                    
                    # Valid vote
                    if 0 <= vote_idx < len(round_3_responses):
                        voted_for = round_3_responses[vote_idx]["display_name"]
                        votes[voted_for] = votes.get(voted_for, 0) + 1
                        
                        vote_details.append({
                            "voter": display_name,
                            "vote": voted_for,
                            "raw_response": vote_text[:100]
                        })
                        
                        logger.info(f"{display_name} voted for {voted_for}")
                    else:
                        logger.warning(f"{display_name} voted for invalid index {vote_idx}")
                else:
                    logger.warning(f"{display_name} vote could not be parsed: {vote_text[:50]}")
                    
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
            "total_voters": len(vote_details)
        }


# Global instance (will be created when needed)
_debate_flow_instance = None


def get_debate_flow(max_search_results: int = 3, resources: List[Any] = None) -> DebateFlow:
    """Get or create the global debate flow instance."""
    global _debate_flow_instance
    if _debate_flow_instance is None:
        _debate_flow_instance = DebateFlow(max_search_results, resources)
    return _debate_flow_instance
