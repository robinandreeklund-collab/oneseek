# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AI Comparison Flow - Debate OS Integration for DeerFlow

Implements parallel querying of multiple AI models (GPT-3.5, Gemini 2.5 Flash, 
DeepSeek-chat, Grok-4 Fast Reasoning, OneSeek local) with analysis, fact-checking, and synthesis.
Uses the same deep research tools and techniques as DeerFlow.
"""

import asyncio
import hashlib
import json
import logging
import os
import random
import time
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from backend.deer_flow.config import SELECTED_SEARCH_ENGINE
from backend.deer_flow.prompts import apply_prompt_template
from backend.deer_flow.tools import get_web_search_tool, get_retriever_tool, crawl_tool
from backend.deer_flow.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)


# Model configurations for AI comparison
AI_MODELS = {
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
        "display_name": "OneSeek Local",
    },
}


class _TTLCache:
    def __init__(self, ttl_seconds: int, max_size: int) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._store: dict[str, tuple[float, Any]] = {}

    def _is_expired(self, expires_at: float) -> bool:
        return expires_at <= time.time()

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if self._is_expired(expires_at):
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if self.ttl_seconds <= 0 or self.max_size <= 0:
            return
        if len(self._store) >= self.max_size:
            # Evict the oldest entry by expiration time (best-effort).
            oldest_key = min(self._store.items(), key=lambda item: item[1][0])[0]
            self._store.pop(oldest_key, None)
        expires_at = time.time() + self.ttl_seconds
        self._store[key] = (expires_at, value)


def _build_cache_key(prefix: str, *parts: Any) -> str:
    payload = "|".join([str(part) for part in parts if part is not None])
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _hash_resources(resources: List[Any]) -> str:
    if not resources:
        return "none"
    tokens = []
    for resource in resources:
        if isinstance(resource, dict):
            tokens.append(str(resource.get("uri") or resource.get("title") or resource))
        else:
            tokens.append(str(getattr(resource, "uri", None) or getattr(resource, "title", None) or resource))
    digest = hashlib.sha256("|".join(tokens).encode("utf-8")).hexdigest()
    return digest[:16]


def _hash_payload(payload: Any) -> str:
    try:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        serialized = str(payload)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return digest[:16]


def _hash_model_responses(model_responses: List[Dict[str, Any]]) -> str:
    normalized = []
    for resp in model_responses:
        if not isinstance(resp, dict):
            continue
        normalized.append(
            {
                "model": resp.get("model"),
                "response": resp.get("response"),
                "error": resp.get("error"),
            }
        )
    normalized.sort(key=lambda item: str(item.get("model")))
    return _hash_payload(normalized)


_MODEL_CACHE_TTL = int(os.getenv("AI_COMPARE_MODEL_CACHE_TTL_S", "900"))
_MODEL_CACHE_MAX = int(os.getenv("AI_COMPARE_MODEL_CACHE_MAX", "256"))
_SEARCH_CACHE_TTL = int(os.getenv("AI_COMPARE_SEARCH_CACHE_TTL_S", "900"))
_SEARCH_CACHE_MAX = int(os.getenv("AI_COMPARE_SEARCH_CACHE_MAX", "256"))
_RAG_CACHE_TTL = int(os.getenv("AI_COMPARE_RAG_CACHE_TTL_S", "900"))
_RAG_CACHE_MAX = int(os.getenv("AI_COMPARE_RAG_CACHE_MAX", "256"))
_META_CACHE_TTL = int(os.getenv("AI_COMPARE_META_CACHE_TTL_S", "900"))
_META_CACHE_MAX = int(os.getenv("AI_COMPARE_META_CACHE_MAX", "128"))
_SYNTH_CACHE_TTL = int(os.getenv("AI_COMPARE_SYNTH_CACHE_TTL_S", "900"))
_SYNTH_CACHE_MAX = int(os.getenv("AI_COMPARE_SYNTH_CACHE_MAX", "128"))

_MODEL_CACHE = _TTLCache(_MODEL_CACHE_TTL, _MODEL_CACHE_MAX)
_SEARCH_CACHE = _TTLCache(_SEARCH_CACHE_TTL, _SEARCH_CACHE_MAX)
_RAG_CACHE = _TTLCache(_RAG_CACHE_TTL, _RAG_CACHE_MAX)
_META_CACHE = _TTLCache(_META_CACHE_TTL, _META_CACHE_MAX)
_SYNTH_CACHE = _TTLCache(_SYNTH_CACHE_TTL, _SYNTH_CACHE_MAX)

_REQUEST_TIMEOUT_S = float(os.getenv("AI_COMPARE_REQUEST_TIMEOUT_S", "60"))
_MAX_RETRIES = int(os.getenv("AI_COMPARE_MAX_RETRIES", "2"))
_BACKOFF_BASE_S = float(os.getenv("AI_COMPARE_BACKOFF_BASE_S", "1.0"))
_ONESEEK_SELF_META_ENABLED = os.getenv("ONESEEK_SELF_META_ENABLED", "true").lower() in ("true", "1", "yes")


class AIComparisonFlow:
    """
    Handles parallel AI model comparison with analysis and synthesis.
    Integrates with DeerFlow's deep research tools for fact-checking and RAG.
    """

    def __init__(self, max_search_results: int = 3, resources: List[Any] = None):
        """Initialize AI comparison flow with configured models."""
        self.models = self._initialize_models()
        self.search_tool = None
        self.retriever_tool = None
        self.max_search_results = max_search_results
        self._resources_cache_key = _hash_resources(resources or [])
        
        # Initialize tools from deer_flow
        try:
            self.search_tool = get_web_search_tool(max_search_results=max_search_results)
            logger.info("Web search tool initialized for AI comparison")
        except Exception as e:
            logger.warning(f"Could not initialize web search tool: {e}")
        
        try:
            if resources:
                self.retriever_tool = get_retriever_tool(resources=resources)
                logger.info("Retriever tool initialized for AI comparison")
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
                logger.info("GPT-3.5 Turbo model initialized")
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
                logger.info("Gemini 2.5 Flash model initialized")
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
                logger.info("DeepSeek Chat model initialized")
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
                logger.info("Grok-4 Fast Reasoning model initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Grok-4 Fast Reasoning: {e}")
        
        # OneSeek Local (vLLM) - use configuration from conf.yaml
        try:
            # Get the local LLM from deer_flow configuration (uses conf.yaml)
            # This ensures we use the same model configuration as the rest of the system
            local_llm = get_llm_by_type("basic")
            models["oneseek-local"] = local_llm
            
            # Log the model name if available
            model_name = getattr(local_llm, 'model_name', 'unknown')
            logger.info(f"OneSeek Local model initialized from conf.yaml: {model_name}")
        except Exception as e:
            logger.warning(f"Failed to initialize OneSeek Local from conf.yaml: {e}")
            # Fallback to environment variable if conf.yaml fails
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
                logger.info(f"OneSeek Local model initialized from environment: {vllm_model}")
            except Exception as e2:
                logger.warning(f"Failed to initialize OneSeek Local from environment: {e2}")
        
        return models

    def _format_search_results(self, results: Any, max_items: int = 3) -> str:
        if not results:
            return ""
        if isinstance(results, dict):
            results = [results]
        if not isinstance(results, list):
            return str(results)
        lines: list[str] = []
        for idx, item in enumerate(results[:max_items]):
            if not isinstance(item, dict):
                lines.append(f"- {str(item)[:200]}")
                continue
            title = item.get("title") or item.get("source") or f"Source {idx + 1}"
            url = item.get("url") or item.get("link") or ""
            snippet = item.get("content") or item.get("description") or ""
            snippet = snippet[:240].strip()
            if url:
                lines.append(f"- {title} ({url}): {snippet}")
            else:
                lines.append(f"- {title}: {snippet}")
        return "\n".join(lines)

    def _infer_locale(self, query: str) -> str:
        lowered = (query or "").lower()
        if any(ch in lowered for ch in ("å", "ä", "ö")):
            return "sv-SE"
        return "en-US"

    def _render_oneseek_prompt(
        self,
        prompt_name: str,
        query: str,
        search_summary: str,
        draft: str = "",
        self_meta: str = "",
        locale: str = "en-US",
    ) -> str:
        try:
            state = {
                "messages": [],
                "research_topic": query,
                "oneseek_search_summary": search_summary,
                "oneseek_draft": draft,
                "oneseek_self_meta": self_meta,
            }
            messages = apply_prompt_template(prompt_name, state, None, locale)
            if messages and isinstance(messages[0], dict):
                return str(messages[0].get("content") or "")
        except Exception as exc:
            logger.warning(f"Failed to render {prompt_name} prompt: {exc}")
        return ""

    def _build_oneseek_system_prompt(self, query: str, search_summary: str) -> str:
        return f"""You are OneSeek Local. Answer the user question with maximum quality.

Goal: maximize scores on the 16 meta‑analysis dimensions:
1) Meta‑reflection level
2) Reasoning depth
3) Synthesis capacity
4) Bias detection
5) Objectivity degree
6) Integrity index
7) Transparency degree
8) Epistemic humility
9) Emotional distance
10) Conflict neutrality
11) Stability coefficient
12) Cognitive redundancy (avoid over‑complexity)
13) Context elasticity
14) System loyalty
15) Adaptive precision
16) Structural clarity

Mandatory behaviors:
- Be explicit about uncertainties and competing interpretations.
- Show clear reasoning steps and balanced trade‑offs.
- Provide a concise, structured answer with headings.
- Include a short "Sources" section if any web search data is available.

Web search findings (use these, do not invent sources):
{search_summary or "- (No web search results available)"}

User question:
{query}
"""

    async def query_model(
        self, model_key: str, model: Any, query: str
    ) -> Dict[str, Any]:
        """
        Query a single AI model and return its response.
        
        Args:
            model_key: Model identifier (e.g., "gpt-3.5-turbo" or "meta-counterfactual")
            model: LangChain model instance
            query: User query to send to the model
            
        Returns:
            Dictionary with model response and metadata
        """
        display_name = AI_MODELS.get(model_key, {}).get("display_name", model_key)
        cache_key = _build_cache_key("model", model_key, query)
        cached = _MODEL_CACHE.get(cache_key)
        if isinstance(cached, dict):
            cached_payload = dict(cached)
            cached_payload["cached"] = True
            return cached_payload

        attempt = 0
        while True:
            try:
                logger.info(f"Querying {model_key} (attempt {attempt + 1})...")
                messages = [HumanMessage(content=query)]
                if model_key == "oneseek-local":
                    search_summary = ""
                    locale = self._infer_locale(query)
                    if self.search_tool:
                        search_cache_key = _build_cache_key(
                            "search",
                            query,
                            self.max_search_results,
                            SELECTED_SEARCH_ENGINE,
                        )
                        cached_search = _SEARCH_CACHE.get(search_cache_key)
                        if cached_search is not None:
                            logger.info("Using cached web search results for OneSeek")
                            search_summary = self._format_search_results(cached_search)
                        else:
                            try:
                                logger.info("OneSeek performing web search before answering")
                                search_results = await asyncio.wait_for(
                                    self.search_tool.ainvoke(query),
                                    timeout=_REQUEST_TIMEOUT_S if _REQUEST_TIMEOUT_S > 0 else None,
                                )
                                _SEARCH_CACHE.set(search_cache_key, search_results)
                                search_summary = self._format_search_results(search_results)
                            except Exception as search_exc:
                                logger.warning(f"OneSeek web search failed: {search_exc}")
                    system_prompt = self._render_oneseek_prompt(
                        "ai_compare_oneseek_system",
                        query,
                        search_summary,
                        locale=locale,
                    )
                    if not system_prompt:
                        system_prompt = self._build_oneseek_system_prompt(query, search_summary)
                    messages = [SystemMessage(content=system_prompt), HumanMessage(content=query)]
                response = await asyncio.wait_for(
                    model.ainvoke(messages),
                    timeout=_REQUEST_TIMEOUT_S if _REQUEST_TIMEOUT_S > 0 else None,
                )
                response_text = response.content if hasattr(response, "content") else str(response)
                if model_key == "oneseek-local" and _ONESEEK_SELF_META_ENABLED:
                    self_meta_prompt = self._render_oneseek_prompt(
                        "ai_compare_oneseek_self_meta",
                        query,
                        search_summary,
                        draft=response_text,
                        locale=locale,
                    )
                    self_meta_text = ""
                    if self_meta_prompt:
                        try:
                            meta_response = await asyncio.wait_for(
                                model.ainvoke(
                                    [
                                        SystemMessage(content=self_meta_prompt),
                                        HumanMessage(content=response_text),
                                    ]
                                ),
                                timeout=_REQUEST_TIMEOUT_S if _REQUEST_TIMEOUT_S > 0 else None,
                            )
                            self_meta_text = (
                                meta_response.content
                                if hasattr(meta_response, "content")
                                else str(meta_response)
                            )
                        except Exception as meta_exc:
                            logger.warning(f"OneSeek self-meta failed: {meta_exc}")
                    revision_prompt = self._render_oneseek_prompt(
                        "ai_compare_oneseek_revision",
                        query,
                        search_summary,
                        draft=response_text,
                        self_meta=self_meta_text,
                        locale=locale,
                    )
                    if revision_prompt:
                        try:
                            revised = await asyncio.wait_for(
                                model.ainvoke(
                                    [
                                        SystemMessage(content=revision_prompt),
                                        HumanMessage(content=response_text),
                                    ]
                                ),
                                timeout=_REQUEST_TIMEOUT_S if _REQUEST_TIMEOUT_S > 0 else None,
                            )
                            response_text = (
                                revised.content if hasattr(revised, "content") else str(revised)
                            )
                        except Exception as revise_exc:
                            logger.warning(f"OneSeek revision failed: {revise_exc}")

                payload = {
                    "model": model_key,
                    "display_name": display_name,
                    "response": response_text,
                    "success": True,
                    "error": None,
                    "cached": False,
                }
                _MODEL_CACHE.set(cache_key, payload)
                return payload
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error querying {model_key}: {e}")
                if attempt >= _MAX_RETRIES:
                    return {
                        "model": model_key,
                        "display_name": display_name,
                        "response": None,
                        "success": False,
                        "error": str(e),
                        "cached": False,
                    }
                backoff = _BACKOFF_BASE_S * (2**attempt) + random.uniform(0, _BACKOFF_BASE_S)
                await asyncio.sleep(backoff)
                attempt += 1

    async def query_single_model(self, model_key: str, query: str) -> Dict[str, Any]:
        """
        Query a single AI model by its key (for individual tool calls).
        
        Args:
            model_key: Model identifier (e.g., "gpt-3.5-turbo", "gemini-2.5-flash")
            query: User query to send to the model
            
        Returns:
            Dictionary with model response and metadata
        """
        if model_key not in self.models:
            return {
                "model": model_key,
                "display_name": AI_MODELS.get(model_key, {}).get("display_name", model_key),
                "response": None,
                "success": False,
                "error": f"Model {model_key} not available (check API key)",
            }
        
        return await self.query_model(model_key, self.models[model_key], query)

    async def parallel_query_all_models(self, query: str) -> List[Dict[str, Any]]:
        """
        Query all available AI models in parallel using asyncio.gather.
        
        Args:
            query: User query to send to all models
            
        Returns:
            List of response dictionaries from all models
        """
        if not self.models:
            logger.warning("No AI models available for comparison")
            return []
        
        logger.info(f"Starting parallel queries to {len(self.models)} models")
        
        # Create tasks for all models
        tasks = [
            self.query_model(model_key, model, query)
            for model_key, model in self.models.items()
        ]
        
        # Execute all queries in parallel with asyncio.gather
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                model_key = list(self.models.keys())[i]
                processed_results.append({
                    "model": model_key,
                    "display_name": AI_MODELS[model_key]["display_name"],
                    "response": None,
                    "success": False,
                    "error": str(result),
                })
            else:
                processed_results.append(result)
        
        logger.info(f"Completed parallel queries: {len(processed_results)} responses")
        return processed_results

    async def analyze_with_fact_check(
        self, query: str, model_responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze model responses with fact-checking using DeerFlow tools.
        
        Args:
            query: Original user query
            model_responses: List of responses from AI models
            
        Returns:
            Analysis results with fact-checking and sources
        """
        logger.info("Starting fact-check analysis with DeerFlow tools")
        
        analysis = {
            "fact_checks": [],
            "sources": [],
            "contradictions": [],
            "consensus_points": [],
        }
        
        tasks: dict[str, asyncio.Task] = {}
        search_results = None
        rag_results = None

        # Always perform web search for fact-checking if available
        if self.search_tool:
            search_cache_key = _build_cache_key(
                "search",
                query,
                self.max_search_results,
                SELECTED_SEARCH_ENGINE,
            )
            cached_search = _SEARCH_CACHE.get(search_cache_key)
            if cached_search is not None:
                search_results = cached_search
                logger.info("Using cached web search results for fact-checking")
            else:
                logger.info("Performing web search for fact-checking")
                tasks["search"] = asyncio.create_task(self.search_tool.ainvoke(query))

        # Use retriever tool for RAG if available
        if self.retriever_tool:
            rag_cache_key = _build_cache_key("rag", query, self._resources_cache_key)
            cached_rag = _RAG_CACHE.get(rag_cache_key)
            if cached_rag is not None:
                rag_results = cached_rag
                logger.info("Using cached RAG results for fact-checking")
            else:
                logger.info("Retrieving relevant documents from RAG")
                tasks["rag"] = asyncio.create_task(self.retriever_tool.ainvoke(query))

        if tasks:
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for (name, result) in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.warning(f"{name} retrieval failed during fact-checking: {result}")
                    continue
                if name == "search":
                    search_results = result
                    search_cache_key = _build_cache_key(
                        "search",
                        query,
                        self.max_search_results,
                        SELECTED_SEARCH_ENGINE,
                    )
                    _SEARCH_CACHE.set(search_cache_key, search_results)
                elif name == "rag":
                    rag_results = result
                    rag_cache_key = _build_cache_key("rag", query, self._resources_cache_key)
                    _RAG_CACHE.set(rag_cache_key, rag_results)

        if search_results is not None:
            analysis["sources"] = (
                search_results if isinstance(search_results, list) else [search_results]
            )
            logger.info(f"Found {len(analysis['sources'])} search results")

        if rag_results:
            analysis["sources"].extend(
                rag_results if isinstance(rag_results, list) else [rag_results]
            )
            logger.info(f"Retrieved {len(rag_results) if rag_results else 0} RAG documents")
        
        # Extract key claims from responses if provided
        successful_responses = [r for r in model_responses if r.get("success")]
        if not successful_responses:
            logger.info("No model responses provided or all failed, but fact-checking via web search was still performed")
        else:
            # Identify consensus and contradictions from model responses
            response_texts = [r["response"] for r in successful_responses if r.get("response")]
            
            # Simple consensus detection (can be enhanced with semantic similarity)
            if len(response_texts) >= 2:
                # Look for common themes (simplified version)
                analysis["consensus_points"] = [
                    "Multiple models provided responses (detailed analysis requires semantic comparison)"
                ]
        
        logger.info("Fact-check analysis completed")
        return analysis

    async def run_meta_agents(
        self, query: str, model_responses: List[Dict[str, Any]], analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run parallel meta-agents for deeper analysis with scoring.
        
        4 Meta-Agent Categories with 4 dimensions each (scored 1-10):
        1. Cognitive Properties: Meta-reflection, Reasoning depth, Synthesis capacity, Bias detection
        2. Integrity & Objectivity: Objectivity degree, Integrity index, Transparency degree, Epistemic humility
        3. Stability & Emotional Profile: Emotional distance, Conflict neutrality, Stability coefficient, Cognitive redundancy
        4. Adaptivity & System Role: Context elasticity, System loyalty, Adaptive precision, Structural clarity
        
        Args:
            query: Original user query
            model_responses: List of responses from AI models
            analysis: Initial fact-check analysis
            
        Returns:
            Meta-agent analysis results with scores for each dimension
        """
        cache_key = _build_cache_key("meta", query, _hash_model_responses(model_responses))
        cached = _META_CACHE.get(cache_key)
        if isinstance(cached, dict):
            logger.info("Using cached meta-agent analysis")
            return cached

        logger.info("Running 4 parallel meta-agents with dimensional scoring")
        
        meta_results = {
            "cognitive_properties": None,
            "integrity_objectivity": None,
            "stability_emotional": None,
            "adaptivity_system": None,
        }
        
        # Use OneSeek local model for meta-agent analysis if available
        if "oneseek-local" not in self.models:
            logger.warning("OneSeek local model not available for meta-agents")
            return meta_results
        
        local_model = self.models["oneseek-local"]
        
        # Prepare responses summary for analysis with display names
        responses_text = "\n\n".join([
            f"**{resp.get('display_name', resp.get('model', 'Unknown'))}**:\n{resp.get('response', '')[:500]}..."
            for resp in model_responses if resp.get('success')
        ])
        
        # Define meta-agent prompts with scoring instructions
        meta_prompts = {
            "cognitive_properties": f"""Analysera AI-modellernas kognitiva egenskaper för denna fråga:

Fråga: {query}

Svar från modellerna:
{responses_text}

Betygsätt varje modell på dessa 4 dimensioner (1-10).

**VIKTIGT:** Använd de exakta modellnamnen som visas ovan (t.ex. "GPT-3.5 (OpenAI)", "Gemini 2.5 Flash (Google)", "DeepSeek Chat", "Grok-4 Fast Reasoning (xAI)", "OneSeek Local") i din analys. Säg INTE "Modell A", "Modell B", etc.

Dimensioner:
1. **Meta-reflektionsnivå** - Förmåga att analysera hur resonemang uppstår
   (1 = ingen meta-reflektion, 10 = avancerad meta-analys)

2. **Resonemangsdjup** - Hur många lager av logik och konsekvens modellen arbetar med
   (1 = ytligt, 10 = multilager-tänkande)

3. **Synteskapacitet** - Förmåga att förena perspektiv till en helhet
   (1 = fragmenterat, 10 = sömlös syntes)

4. **Bias-detektion** - Förmåga att upptäcka dolda antaganden och vinklingar
   (1 = blind, 10 = hög precision)

Ge konkreta poäng (exakt siffra 1-10) och korta motiveringar för varje dimension och modell.""",

            "integrity_objectivity": f"""Analysera AI-modellernas integritet och objektivitet för denna fråga:

Fråga: {query}

Svar från modellerna:
{responses_text}

Betygsätt varje modell på dessa 4 dimensioner (1-10).

**VIKTIGT:** Använd de exakta modellnamnen som visas ovan (t.ex. "GPT-3.5 (OpenAI)", "Gemini 2.5 Flash (Google)", "DeepSeek Chat", "Grok-4 Fast Reasoning (xAI)", "OneSeek Local") i din analys. Säg INTE "Modell A", "Modell B", etc.

Dimensioner:
1. **Objektivitetsgrad** - Grad av neutralitet och frånvaro av partiskhet
   (1 = stark bias, 10 = konsekvent objektiv)

2. **Integritetsindex** - Hur strikt modellen följer metod och logik
   (1 = opportunistisk, 10 = principfast)

3. **Transparensgrad** - Hur tydligt resonemang och metod redovisas
   (1 = svart låda, 10 = full transparens)

4. **Epistemisk ödmjukhet** - Förmåga att erkänna osäkerhet och alternativa tolkningar
   (1 = dogmatisk, 10 = ödmjuk)

Ge konkreta poäng (exakt siffra 1-10) och korta motiveringar för varje dimension och modell.""",

            "stability_emotional": f"""Analysera AI-modellernas stabilitet och emotionella profil för denna fråga:

Fråga: {query}

Svar från modellerna:
{responses_text}

Betygsätt varje modell på dessa 4 dimensioner (1-10).

**VIKTIGT:** Använd de exakta modellnamnen som visas ovan (t.ex. "GPT-3.5 (OpenAI)", "Gemini 2.5 Flash (Google)", "DeepSeek Chat", "Grok-4 Fast Reasoning (xAI)", "OneSeek Local") i din analys. Säg INTE "Modell A", "Modell B", etc.

Dimensioner:
1. **Emotionell distans** - Förmåga att förstå känslor utan att påverkas
   (1 = reaktiv, 10 = stabil)

2. **Konfliktneutralitet** - Förmåga att inte ta parti i polariserade frågor
   (1 = partisk, 10 = helt neutral)

3. **Stabilitetskoefficient** - Motståndskraft mot provokationer och retoriska fällor
   (1 = lättstörd, 10 = orubblig)

4. **Kognitiv redundans** - Förmåga att undvika överarbete och onödig komplexitet
   (1 = överarbetar, 10 = extremt effektiv)

Ge konkreta poäng (exakt siffra 1-10) och korta motiveringar för varje dimension och modell.""",

            "adaptivity_system": f"""Analysera AI-modellernas adaptivitet och systemroll för denna fråga:

Fråga: {query}

Svar från modellerna:
{responses_text}

Betygsätt varje modell på dessa 4 dimensioner (1-10).

**VIKTIGT:** Använd de exakta modellnamnen som visas ovan (t.ex. "GPT-3.5 (OpenAI)", "Gemini 2.5 Flash (Google)", "DeepSeek Chat", "Grok-4 Fast Reasoning (xAI)", "OneSeek Local") i din analys. Säg INTE "Modell A", "Modell B", etc.

Dimensioner:
1. **Kontextelasticitet** - Förmåga att anpassa sig till olika format och situationer
   (1 = rigid, 10 = flexibel)

2. **Systemlojalitet** - Hur väl modellen följer arkitekturens principer
   (1 = avvikande, 10 = harmonisk)

3. **Adaptiv precision** - Förmåga att justera ton och stil utan att tappa identitet
   (1 = oförutsägbar, 10 = exakt)

4. **Strukturell klarhet** - Hur tydligt modellen organiserar och presenterar information
   (1 = rörig, 10 = kristallklar)

Ge konkreta poäng (exakt siffra 1-10) och korta motiveringar för varje dimension och modell.""",
        }
        
        # Run meta-agents in parallel
        tasks = [
            self.query_model(f"meta-{agent_name}", local_model, prompt)
            for agent_name, prompt in meta_prompts.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process meta-agent results
        for agent_name, result in zip(meta_prompts.keys(), results):
            if isinstance(result, Exception):
                logger.warning(f"Meta-agent {agent_name} failed: {result}")
                meta_results[agent_name] = {"error": str(result)}
            elif result and result["success"]:
                meta_results[agent_name] = {
                    "analysis": result["response"],
                    "success": True,
                }
            else:
                meta_results[agent_name] = {"error": "Failed to generate analysis"}
        
        logger.info("Meta-agent analysis completed with dimensional scoring")
        _META_CACHE.set(cache_key, meta_results)
        return meta_results

    async def synthesize_optimal_answer(
        self,
        query: str,
        model_responses: List[Dict[str, Any]],
        analysis: Dict[str, Any],
        meta_results: Dict[str, Any],
        locale: str = "en-US",
    ) -> Dict[str, Any]:
        """
        Synthesize an optimal answer from all model responses and analysis.
        
        Args:
            query: Original user query
            model_responses: List of responses from AI models
            analysis: Fact-check analysis results
            meta_results: Meta-agent analysis results
            
        Returns:
            Synthesized optimal answer with sources and tools used
        """
        cache_key = _build_cache_key(
            "synth",
            query,
            _hash_model_responses(model_responses),
            _hash_payload(analysis),
            _hash_payload(meta_results),
            locale,
        )
        cached = _SYNTH_CACHE.get(cache_key)
        if isinstance(cached, dict):
            logger.info("Using cached synthesized answer")
            return cached

        logger.info("Synthesizing optimal answer")
        
        # Use OneSeek local model for synthesis if available
        if "oneseek-local" not in self.models:
            logger.warning("OneSeek local model not available for synthesis")
            return {
                "synthesized_answer": "Synthesis not available (local model not configured)",
                "sources": analysis.get("sources", []),
                "tools_used": ["parallel_query", "fact_check"],
            }
        
        local_model = self.models["oneseek-local"]
        
        # Prepare synthesis prompt
        successful_responses = [r for r in model_responses if r["success"]]
        response_summary = "\n\n".join([
            f"**{r['display_name']}**: {r['response'][:500]}..." if len(r['response']) > 500 else f"**{r['display_name']}**: {r['response']}"
            for r in successful_responses
        ])
        
        if locale.startswith("sv"):
            synthesis_prompt = f"""Syntetisera ett optimalt svar på följande fråga baserat på flera AI‑modell‑svar och analys.

Fråga: {query}

Modellsvar:
{response_summary}

Faktakoll: {len(analysis.get('sources', []))} källor
Konsensuspunkter: {analysis.get('consensus_points', [])}

Meta‑analys: Använd insikter från de fyra kategorierna (kognitiva egenskaper, integritet & objektivitet, stabilitet & emotionell profil, adaptivitet & systemroll).

Svara på svenska och:
1. Kombinera de bästa insikterna från alla modeller
2. Ta hänsyn till faktakoll
3. Redovisa konsensus och oenighet
4. Håll det sakligt och balanserat
"""
        else:
            synthesis_prompt = f"""Synthesize an optimal answer to the following query based on multiple AI model responses and analysis.

Query: {query}

Model Responses:
{response_summary}

Fact-Check Sources: {len(analysis.get('sources', []))} sources found
Consensus Points: {analysis.get('consensus_points', [])}

Meta-Analysis: Use the four-category meta analysis (cognitive properties, integrity & objectivity, stability & emotional profile, adaptivity & system role).

Please provide a comprehensive, well-reasoned answer that:
1. Combines the best insights from all model responses
2. Considers the fact-checking results
3. Acknowledges areas of consensus and disagreement
4. Provides a balanced, accurate response
"""
        
        try:
            synthesis_result = await self.query_model(
                "synthesis", local_model, synthesis_prompt
            )
            
            payload = {
                "synthesized_answer": synthesis_result["response"] if synthesis_result["success"] else "Failed to synthesize answer",
                "sources": analysis.get("sources", []),
                "tools_used": [
                    "parallel_query",
                    "fact_check",
                    "web_search" if self.search_tool else None,
                    "rag_retrieval" if self.retriever_tool else None,
                    "meta_agents",
                    "synthesis",
                ],
                "models_used": [r["display_name"] for r in successful_responses],
            }
            _SYNTH_CACHE.set(cache_key, payload)
            return payload
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return {
                "synthesized_answer": f"Synthesis error: {str(e)}",
                "sources": analysis.get("sources", []),
                "tools_used": ["parallel_query", "fact_check"],
            }

    async def run_comparison(self, query: str) -> Dict[str, Any]:
        """
        Run the complete AI comparison flow.
        
        Args:
            query: User query to compare across AI models
            
        Returns:
            Complete comparison results with model responses, analysis, and synthesis
        """
        logger.info(f"Starting AI comparison for query: {query[:100]}...")
        
        # Step 1: Query all models in parallel
        model_responses = await self.parallel_query_all_models(query)
        
        # Step 2: Analyze with fact-checking
        analysis = await self.analyze_with_fact_check(query, model_responses)
        
        # Step 3: Run meta-agents in parallel
        meta_results = await self.run_meta_agents(query, model_responses, analysis)
        
        # Step 4: Synthesize optimal answer
        synthesis = await self.synthesize_optimal_answer(
            query, model_responses, analysis, meta_results
        )
        
        logger.info("AI comparison completed successfully")
        
        return {
            "query": query,
            "model_responses": model_responses,
            "analysis": analysis,
            "meta_results": meta_results,
            "synthesis": synthesis,
            "status": "completed",
        }


# Global instance
_ai_comparison_flow: Optional[AIComparisonFlow] = None


def get_ai_comparison_flow(max_search_results: int = 3, resources: List[Any] = None) -> AIComparisonFlow:
    """Get or create the global AI comparison flow instance."""
    global _ai_comparison_flow
    # Always create a new instance with the provided parameters
    _ai_comparison_flow = AIComparisonFlow(max_search_results=max_search_results, resources=resources or [])
    return _ai_comparison_flow
