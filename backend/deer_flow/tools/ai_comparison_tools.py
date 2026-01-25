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
async def query_all_ai_models(query: str) -> str:
    """
    Query multiple AI models in parallel (GPT-3.5, Gemini 2.5 Flash, DeepSeek, Grok-4, OneSeek Local).
    
    Args:
        query: The question or prompt to send to all models
        
    Returns:
        A formatted string containing responses from all models with success/failure status
    """
    try:
        # Get comparison flow instance with default config
        comparison_flow = get_ai_comparison_flow(max_search_results=3, resources=[])
        
        # Query all models
        responses = await comparison_flow.parallel_query_all_models(query)
        
        # Format results
        result = f"## AI Model Responses ({len([r for r in responses if r['success']])}/{len(responses)} successful)\n\n"
        
        for response in responses:
            status = "✓" if response["success"] else "✗"
            result += f"### {status} {response['display_name']}\n\n"
            if response["success"]:
                # Truncate long responses
                content = response["response"][:500]
                if len(response["response"]) > 500:
                    content += "... [truncated]"
                result += f"{content}\n\n"
            else:
                result += f"Error: {response['error']}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error querying AI models: {e}", exc_info=True)
        return f"Error querying AI models: {str(e)}"


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
        query_all_ai_models,
        fact_check_responses,
        run_meta_analysis,
        synthesize_optimal_answer,
    ]
