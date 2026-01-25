# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AI Comparison Flow - Debate OS Integration for DeerFlow

Implements parallel querying of multiple AI models (GPT-3.5, Gemini 2.5 Flash, 
DeepSeek-chat, Grok-4 Fast Reasoning, OneSeek local) with analysis, fact-checking, and synthesis.
Uses the same deep research tools and techniques as DeerFlow.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from backend.deer_flow.tools import get_web_search_tool, get_retriever_tool, crawl_tool

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
        
        # OneSeek Local (vLLM)
        vllm_url = os.getenv("VLLM_URL", "http://localhost:8000/v1")
        vllm_model = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ")
        try:
            models["oneseek-local"] = ChatOpenAI(
                base_url=vllm_url,
                api_key="EMPTY",
                model=vllm_model,
                temperature=0.7,
                max_tokens=2048,
            )
            logger.info(f"OneSeek Local model initialized: {vllm_model}")
        except Exception as e:
            logger.warning(f"Failed to initialize OneSeek Local: {e}")
        
        return models

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
        try:
            logger.info(f"Querying {model_key}...")
            messages = [HumanMessage(content=query)]
            response = await model.ainvoke(messages)
            
            # Get display name if it's a standard model, otherwise use the key
            display_name = AI_MODELS.get(model_key, {}).get("display_name", model_key)
            
            return {
                "model": model_key,
                "display_name": display_name,
                "response": response.content if hasattr(response, "content") else str(response),
                "success": True,
                "error": None,
            }
        except Exception as e:
            logger.error(f"Error querying {model_key}: {e}")
            display_name = AI_MODELS.get(model_key, {}).get("display_name", model_key)
            return {
                "model": model_key,
                "display_name": display_name,
                "response": None,
                "success": False,
                "error": str(e),
            }

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
        
        # Extract key claims from responses
        successful_responses = [r for r in model_responses if r["success"]]
        if not successful_responses:
            logger.warning("No successful responses to analyze")
            return analysis
        
        # Use web search tool for fact-checking if available
        if self.search_tool:
            try:
                logger.info("Performing web search for fact-checking")
                search_results = await self.search_tool.ainvoke(query)
                analysis["sources"] = search_results if isinstance(search_results, list) else [search_results]
                logger.info(f"Found {len(analysis['sources'])} search results")
            except Exception as e:
                logger.warning(f"Web search failed during fact-checking: {e}")
        
        # Use retriever tool for RAG if available
        if self.retriever_tool:
            try:
                logger.info("Retrieving relevant documents from RAG")
                rag_results = await self.retriever_tool.ainvoke(query)
                if rag_results:
                    analysis["sources"].extend(rag_results if isinstance(rag_results, list) else [rag_results])
                logger.info(f"Retrieved {len(rag_results) if rag_results else 0} RAG documents")
            except Exception as e:
                logger.warning(f"RAG retrieval failed during fact-checking: {e}")
        
        # Identify consensus and contradictions
        response_texts = [r["response"] for r in successful_responses if r["response"]]
        
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
        Run parallel meta-agents for deeper analysis.
        Meta-agents: Counterfactual, Robustness, Consistency, Truth-Pressure
        
        Args:
            query: Original user query
            model_responses: List of responses from AI models
            analysis: Initial fact-check analysis
            
        Returns:
            Meta-agent analysis results
        """
        logger.info("Running parallel meta-agents")
        
        meta_results = {
            "counterfactual": None,
            "robustness": None,
            "consistency": None,
            "truth_pressure": None,
        }
        
        # Use OneSeek local model for meta-agent analysis if available
        if "oneseek-local" not in self.models:
            logger.warning("OneSeek local model not available for meta-agents")
            return meta_results
        
        local_model = self.models["oneseek-local"]
        
        # Define meta-agent prompts
        meta_prompts = {
            "counterfactual": f"Analyze the following responses and identify potential counterfactual scenarios or alternative explanations:\n\nQuery: {query}\n\nResponses: {model_responses}",
            "robustness": f"Evaluate the robustness and reliability of these AI responses:\n\nQuery: {query}\n\nResponses: {model_responses}",
            "consistency": f"Check for consistency and contradictions across these AI responses:\n\nQuery: {query}\n\nResponses: {model_responses}",
            "truth_pressure": f"Apply critical truth-pressure analysis to these responses, identifying claims that need verification:\n\nQuery: {query}\n\nResponses: {model_responses}",
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
        
        logger.info("Meta-agent analysis completed")
        return meta_results

    async def synthesize_optimal_answer(
        self,
        query: str,
        model_responses: List[Dict[str, Any]],
        analysis: Dict[str, Any],
        meta_results: Dict[str, Any],
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
        
        synthesis_prompt = f"""Synthesize an optimal answer to the following query based on multiple AI model responses and analysis.

Query: {query}

Model Responses:
{response_summary}

Fact-Check Sources: {len(analysis.get('sources', []))} sources found
Consensus Points: {analysis.get('consensus_points', [])}

Meta-Analysis:
- Counterfactual: {"Available" if meta_results.get('counterfactual', {}).get('success') else "Not available"}
- Robustness: {"Available" if meta_results.get('robustness', {}).get('success') else "Not available"}
- Consistency: {"Available" if meta_results.get('consistency', {}).get('success') else "Not available"}
- Truth Pressure: {"Available" if meta_results.get('truth_pressure', {}).get('success') else "Not available"}

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
            
            return {
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
