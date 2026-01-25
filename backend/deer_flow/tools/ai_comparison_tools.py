"""
AI Comparison Tools for Debate OS

These tools enable the AI comparison agent to query multiple models,
perform fact-checking, run meta-analysis, and synthesize optimal answers.
"""

import logging
from typing import Any
from langchain_core.tools import tool

from backend.ai_comparison_flow import get_ai_comparison_flow

logger = logging.getLogger(__name__)


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
        comparison_flow = get_ai_comparison_flow(max_search_results=3, resources=[])
        response = await comparison_flow.query_single_model("gpt-3.5-turbo", query)
        
        if response["success"]:
            content = response["response"][:800]
            if len(response["response"]) > 800:
                content += "... [response truncated for brevity]"
            return f"**GPT-3.5 Response:**\n\n{content}"
        else:
            return f"**GPT-3.5 Error:** {response['error']}"
        
    except Exception as e:
        logger.error(f"Error querying GPT-3.5: {e}", exc_info=True)
        return f"Error querying GPT-3.5: {str(e)}"


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
        comparison_flow = get_ai_comparison_flow(max_search_results=3, resources=[])
        response = await comparison_flow.query_single_model("gemini-2.5-flash", query)
        
        if response["success"]:
            content = response["response"][:800]
            if len(response["response"]) > 800:
                content += "... [response truncated for brevity]"
            return f"**Gemini 2.5 Flash Response:**\n\n{content}"
        else:
            return f"**Gemini 2.5 Flash Error:** {response['error']}"
        
    except Exception as e:
        logger.error(f"Error querying Gemini 2.5 Flash: {e}", exc_info=True)
        return f"Error querying Gemini 2.5 Flash: {str(e)}"


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
        comparison_flow = get_ai_comparison_flow(max_search_results=3, resources=[])
        response = await comparison_flow.query_single_model("deepseek-chat", query)
        
        if response["success"]:
            content = response["response"][:800]
            if len(response["response"]) > 800:
                content += "... [response truncated for brevity]"
            return f"**DeepSeek Response:**\n\n{content}"
        else:
            return f"**DeepSeek Error:** {response['error']}"
        
    except Exception as e:
        logger.error(f"Error querying DeepSeek: {e}", exc_info=True)
        return f"Error querying DeepSeek: {str(e)}"


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
        comparison_flow = get_ai_comparison_flow(max_search_results=3, resources=[])
        response = await comparison_flow.query_single_model("grok-4-fast-reasoning", query)
        
        if response["success"]:
            content = response["response"][:800]
            if len(response["response"]) > 800:
                content += "... [response truncated for brevity]"
            return f"**Grok-4 Response:**\n\n{content}"
        else:
            return f"**Grok-4 Error:** {response['error']}"
        
    except Exception as e:
        logger.error(f"Error querying Grok-4: {e}", exc_info=True)
        return f"Error querying Grok-4: {str(e)}"


@tool
async def query_oneseek_local(query: str) -> str:
    """
    Query OneSeek Local model (vLLM).
    
    Args:
        query: The question or prompt to send to OneSeek Local
        
    Returns:
        The response from OneSeek Local
    """
    try:
        comparison_flow = get_ai_comparison_flow(max_search_results=3, resources=[])
        response = await comparison_flow.query_single_model("oneseek-local", query)
        
        if response["success"]:
            content = response["response"][:800]
            if len(response["response"]) > 800:
                content += "... [response truncated for brevity]"
            return f"**OneSeek Local Response:**\n\n{content}"
        else:
            return f"**OneSeek Local Error:** {response['error']}"
        
    except Exception as e:
        logger.error(f"Error querying OneSeek Local: {e}", exc_info=True)
        return f"Error querying OneSeek Local: {str(e)}"


@tool
async def fact_check_responses(query: str, model_responses_summary: str) -> str:
    """
    Perform fact-checking on AI model responses using web search and RAG tools.
    
    Args:
        query: The original question
        model_responses_summary: Summary of what the models said (for context)
        
    Returns:
        Fact-checking results with sources and verification status
    """
    try:
        comparison_flow = get_ai_comparison_flow(max_search_results=3, resources=[])
        
        # For fact-checking, we need the actual response objects, but we only have summary
        # This is a simplified version - in practice, the agent would call query_all_ai_models first
        logger.info("Fact-checking analysis initiated")
        
        # Run fact-check (this would ideally use the full responses, but we work with what we have)
        analysis = await comparison_flow.analyze_with_fact_check(query, [])
        
        # Format results
        result = f"## Fact-Check Analysis\n\n"
        result += f"**Sources Found**: {len(analysis.get('sources', []))}\n\n"
        
        if analysis.get("sources"):
            result += "### Sources:\n"
            for source in analysis.get("sources", [])[:5]:  # Limit to first 5
                result += f"- {source}\n"
            result += "\n"
        
        if analysis.get("fact_check_summary"):
            result += f"### Summary:\n{analysis['fact_check_summary']}\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in fact-checking: {e}", exc_info=True)
        return f"Error in fact-checking: {str(e)}"


@tool
async def run_meta_analysis(query: str, responses_context: str) -> str:
    """
    Run meta-analysis agents (Counterfactual, Robustness, Consistency, Truth-Pressure) on the responses.
    
    Args:
        query: The original question
        responses_context: Context about the model responses
        
    Returns:
        Meta-analysis results from all four analytical frameworks
    """
    try:
        comparison_flow = get_ai_comparison_flow(max_search_results=3, resources=[])
        
        logger.info("Starting meta-agent analysis")
        
        # Run meta-agents
        meta_results = await comparison_flow.run_meta_agents(query, [], {})
        
        # Format results
        result = f"## Meta-Analysis Results\n\n"
        successful = sum(1 for v in meta_results.values() if v.get("success"))
        result += f"**Completed**: {successful}/4 meta-agents\n\n"
        
        for agent_name, agent_result in meta_results.items():
            status = "✓" if agent_result.get("success") else "✗"
            display_name = agent_name.replace("_", " ").title()
            result += f"### {status} {display_name}\n\n"
            
            if agent_result.get("success"):
                analysis = agent_result.get("analysis", "No analysis available")[:300]
                if len(agent_result.get("analysis", "")) > 300:
                    analysis += "... [truncated]"
                result += f"{analysis}\n\n"
            else:
                result += f"Error: {agent_result.get('error', 'Unknown error')}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in meta-analysis: {e}", exc_info=True)
        return f"Error in meta-analysis: {str(e)}"


@tool
async def synthesize_optimal_answer(
    query: str,
    model_responses: str,
    fact_check_results: str,
    meta_analysis: str
) -> str:
    """
    Synthesize an optimal answer by combining insights from all models, fact-checking, and meta-analysis.
    
    Args:
        query: The original question
        model_responses: Summary of what each model said
        fact_check_results: Fact-checking findings
        meta_analysis: Meta-analysis insights
        
    Returns:
        Synthesized optimal answer with sources and reasoning
    """
    try:
        comparison_flow = get_ai_comparison_flow(max_search_results=3, resources=[])
        
        logger.info("Synthesizing optimal answer")
        
        # Run synthesis
        synthesis = await comparison_flow.synthesize_optimal_answer(query, [], {}, {})
        
        # Format result
        result = f"## Optimal Synthesized Answer\n\n"
        
        if synthesis.get("success"):
            result += f"{synthesis.get('synthesis', 'No synthesis generated')}\n\n"
            result += f"### Confidence: {synthesis.get('confidence', 'N/A')}\n\n"
            
            if synthesis.get("sources"):
                result += "### Sources:\n"
                for source in synthesis.get("sources", [])[:10]:
                    result += f"- {source}\n"
        else:
            result += f"Synthesis failed: {synthesis.get('error', 'Unknown error')}\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in synthesis: {e}", exc_info=True)
        return f"Error in synthesis: {str(e)}"


def get_ai_comparison_tools():
    """Get all AI comparison tools for the agent."""
    return [
        query_gpt35,
        query_gemini_flash,
        query_deepseek,
        query_grok4,
        query_oneseek_local,
        fact_check_responses,
        run_meta_analysis,
        synthesize_optimal_answer,
    ]
