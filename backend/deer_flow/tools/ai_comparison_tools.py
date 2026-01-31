"""
AI Comparison Tools for Debate OS

These tools enable the AI comparison agent to query multiple models,
perform fact-checking, run meta-analysis, and synthesize optimal answers.
"""

import contextvars
import json
import logging
from typing import Any
from langchain_core.tools import tool

from backend.ai_comparison_flow import get_ai_comparison_flow

logger = logging.getLogger(__name__)

_ai_comparison_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "ai_comparison_context",
    default={"max_search_results": 3, "resources": []},
)


def set_ai_comparison_context(max_search_results: int = 3, resources: list[Any] | None = None):
    _ai_comparison_context.set(
        {
            "max_search_results": max_search_results,
            "resources": resources or [],
        }
    )


def _get_flow():
    context = _ai_comparison_context.get()
    return get_ai_comparison_flow(
        max_search_results=context.get("max_search_results", 3),
        resources=context.get("resources", []),
    )


def _safe_json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


@tool
async def query_gpt35(query: str) -> str:
    """
    Query GPT-3.5 Turbo model from OpenAI.
    
    Args:
        query: The question or prompt to send to GPT-3.5
        
    Returns:
        The response from GPT-3.5 Turbo
    """
    try:
        comparison_flow = _get_flow()
        response = await comparison_flow.query_single_model("gpt-3.5-turbo", query)
        
        if response["success"]:
            content = response["response"]
            payload = {
                "model": "gpt-3.5-turbo",
                "display_name": "GPT-3.5 (OpenAI)",
                "response": content,
                "success": True,
            }
            return _safe_json_dump(payload)
        else:
            return _safe_json_dump(
                {
                    "model": "gpt-3.5-turbo",
                    "display_name": "GPT-3.5 (OpenAI)",
                    "error": response.get("error"),
                    "success": False,
                }
            )
        
    except Exception as e:
        logger.error(f"Error querying GPT-3.5: {e}", exc_info=True)
        return _safe_json_dump(
            {
                "model": "gpt-3.5-turbo",
                "display_name": "GPT-3.5 (OpenAI)",
                "error": str(e),
                "success": False,
            }
        )


@tool
async def query_gemini_flash(query: str) -> str:
    """
    Query Gemini 2.5 Flash model from Google.
    
    Args:
        query: The question or prompt to send to Gemini 2.5 Flash
        
    Returns:
        The response from Gemini 2.5 Flash
    """
    try:
        comparison_flow = _get_flow()
        response = await comparison_flow.query_single_model("gemini-2.5-flash", query)
        
        if response["success"]:
            content = response["response"]
            payload = {
                "model": "gemini-2.5-flash",
                "display_name": "Gemini 2.5 Flash (Google)",
                "response": content,
                "success": True,
            }
            return _safe_json_dump(payload)
        else:
            return _safe_json_dump(
                {
                    "model": "gemini-2.5-flash",
                    "display_name": "Gemini 2.5 Flash (Google)",
                    "error": response.get("error"),
                    "success": False,
                }
            )
        
    except Exception as e:
        logger.error(f"Error querying Gemini 2.5 Flash: {e}", exc_info=True)
        return _safe_json_dump(
            {
                "model": "gemini-2.5-flash",
                "display_name": "Gemini 2.5 Flash (Google)",
                "error": str(e),
                "success": False,
            }
        )


@tool
async def query_deepseek(query: str) -> str:
    """
    Query DeepSeek Chat model.
    
    Args:
        query: The question or prompt to send to DeepSeek
        
    Returns:
        The response from DeepSeek Chat
    """
    try:
        comparison_flow = _get_flow()
        response = await comparison_flow.query_single_model("deepseek-chat", query)
        
        if response["success"]:
            content = response["response"]
            payload = {
                "model": "deepseek-chat",
                "display_name": "DeepSeek Chat",
                "response": content,
                "success": True,
            }
            return _safe_json_dump(payload)
        else:
            return _safe_json_dump(
                {
                    "model": "deepseek-chat",
                    "display_name": "DeepSeek Chat",
                    "error": response.get("error"),
                    "success": False,
                }
            )
        
    except Exception as e:
        logger.error(f"Error querying DeepSeek: {e}", exc_info=True)
        return _safe_json_dump(
            {
                "model": "deepseek-chat",
                "display_name": "DeepSeek Chat",
                "error": str(e),
                "success": False,
            }
        )


@tool
async def query_grok4(query: str) -> str:
    """
    Query Grok-4 Fast Reasoning model from xAI.
    
    Args:
        query: The question or prompt to send to Grok-4
        
    Returns:
        The response from Grok-4 Fast Reasoning
    """
    try:
        comparison_flow = _get_flow()
        response = await comparison_flow.query_single_model("grok-4-fast-reasoning", query)
        
        if response["success"]:
            content = response["response"]
            payload = {
                "model": "grok-4-fast-reasoning",
                "display_name": "Grok-4 Fast Reasoning (xAI)",
                "response": content,
                "success": True,
            }
            return _safe_json_dump(payload)
        else:
            return _safe_json_dump(
                {
                    "model": "grok-4-fast-reasoning",
                    "display_name": "Grok-4 Fast Reasoning (xAI)",
                    "error": response.get("error"),
                    "success": False,
                }
            )
        
    except Exception as e:
        logger.error(f"Error querying Grok-4: {e}", exc_info=True)
        return _safe_json_dump(
            {
                "model": "grok-4-fast-reasoning",
                "display_name": "Grok-4 Fast Reasoning (xAI)",
                "error": str(e),
                "success": False,
            }
        )


@tool
async def fact_check_responses(query: str, model_responses_json: str) -> str:
    """
    Perform fact-checking on AI model responses using web search and RAG tools.
    
    Args:
        query: The original question
        model_responses_json: JSON list of model responses
        
    Returns:
        Fact-checking results with sources and verification status
    """
    try:
        comparison_flow = _get_flow()
        logger.info("Fact-checking analysis initiated")

        try:
            responses = json.loads(model_responses_json) if model_responses_json else []
        except json.JSONDecodeError:
            responses = []

        analysis = await comparison_flow.analyze_with_fact_check(query, responses)
        return _safe_json_dump(analysis)
        
    except Exception as e:
        logger.error(f"Error in fact-checking: {e}", exc_info=True)
        return f"Error in fact-checking: {str(e)}"


@tool
async def run_meta_analysis(query: str, model_responses_json: str, analysis_json: str) -> str:
    """
    Run 4 meta-analysis agents with dimensional scoring (1-10) on each AI model response.
    
    Meta-Agents:
    1. Cognitive Properties: Meta-reflection, Reasoning depth, Synthesis capacity, Bias detection
    2. Integrity & Objectivity: Objectivity, Integrity, Transparency, Epistemic humility
    3. Stability & Emotional Profile: Emotional distance, Conflict neutrality, Stability, Cognitive redundancy
    4. Adaptivity & System Role: Context elasticity, System loyalty, Adaptive precision, Structural clarity
    
    Args:
        query: The original question
        model_responses_json: JSON list of model responses
        analysis_json: JSON fact-check analysis results
        
    Returns:
        Meta-analysis results with dimensional scores from all four analytical frameworks
    """
    try:
        comparison_flow = _get_flow()
        
        logger.info("Starting 4-category meta-agent analysis with dimensional scoring")
        
        try:
            responses = json.loads(model_responses_json) if model_responses_json else []
        except json.JSONDecodeError:
            responses = []
        try:
            analysis = json.loads(analysis_json) if analysis_json else {}
        except json.JSONDecodeError:
            analysis = {}

        meta_results = await comparison_flow.run_meta_agents(query, responses, analysis)
        return _safe_json_dump(meta_results)
        
    except Exception as e:
        logger.error(f"Error in meta-analysis: {e}", exc_info=True)
        return f"Error in meta-analysis: {str(e)}"


@tool
async def synthesize_optimal_answer(
    query: str,
    model_responses_json: str,
    analysis_json: str,
    meta_json: str
) -> str:
    """
    Synthesize an optimal answer by combining insights from all models, fact-checking, and meta-analysis.
    
    Args:
        query: The original question
        model_responses_json: JSON list of model responses
        analysis_json: JSON fact-check analysis results
        meta_json: JSON meta-analysis results
        
    Returns:
        Synthesized optimal answer with sources and reasoning
    """
    try:
        comparison_flow = _get_flow()
        
        logger.info("Synthesizing optimal answer")
        
        try:
            responses = json.loads(model_responses_json) if model_responses_json else []
        except json.JSONDecodeError:
            responses = []
        try:
            analysis = json.loads(analysis_json) if analysis_json else {}
        except json.JSONDecodeError:
            analysis = {}
        try:
            meta_results = json.loads(meta_json) if meta_json else {}
        except json.JSONDecodeError:
            meta_results = {}

        synthesis = await comparison_flow.synthesize_optimal_answer(
            query, responses, analysis, meta_results
        )
        return _safe_json_dump(synthesis)
        
    except Exception as e:
        logger.error(f"Error in synthesis: {e}", exc_info=True)
        return f"Error in synthesis: {str(e)}"


def get_ai_comparison_tools():
    """Get all AI comparison tools for the agent.
    
    NOTE: OneSeek Local is NOT included as a tool because it serves as the 
    synthesizing agent that analyzes responses from other models, rather than
    being queried as one of the models to compare.
    
    The web_search tool is included directly so the frontend can display
    search results with the same rich UI as deep research mode.
    """
    # Import web_search tool from deer_flow
    from backend.deer_flow.tools import get_web_search_tool
    
    # Get web search tool with default 3 results
    web_search = get_web_search_tool(max_search_results=3)
    
    return [
        query_gpt35,
        query_gemini_flash,
        query_deepseek,
        query_grok4,
        fact_check_responses,
        web_search,  # Direct web search for fact-checking (optional)
        run_meta_analysis,
        synthesize_optimal_answer,
    ]
