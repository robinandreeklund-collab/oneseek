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
        
        # Always perform web search for fact-checking if available
        # This provides external validation regardless of model responses
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

**VIKTIGT:** Använd de exakta modellnamnen som visas ovan (t.ex. "GPT-3.5 (OpenAI)", "Gemini 2.5 Flash (Google)", "DeepSeek Chat", "Grok-4 Fast Reasoning (xAI)") i din analys. Säg INTE "Modell A", "Modell B", etc.

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

**VIKTIGT:** Använd de exakta modellnamnen som visas ovan (t.ex. "GPT-3.5 (OpenAI)", "Gemini 2.5 Flash (Google)", "DeepSeek Chat", "Grok-4 Fast Reasoning (xAI)") i din analys. Säg INTE "Modell A", "Modell B", etc.

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

**VIKTIGT:** Använd de exakta modellnamnen som visas ovan (t.ex. "GPT-3.5 (OpenAI)", "Gemini 2.5 Flash (Google)", "DeepSeek Chat", "Grok-4 Fast Reasoning (xAI)") i din analys. Säg INTE "Modell A", "Modell B", etc.

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

**VIKTIGT:** Använd de exakta modellnamnen som visas ovan (t.ex. "GPT-3.5 (OpenAI)", "Gemini 2.5 Flash (Google)", "DeepSeek Chat", "Grok-4 Fast Reasoning (xAI)") i din analys. Säg INTE "Modell A", "Modell B", etc.

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
