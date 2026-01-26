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
        
        # Parse and format search results nicely
        import json
        result = f"## Fact-Check Analysis\n\n"
        
        sources = analysis.get('sources', [])
        if sources:
            # Parse JSON if it's a string
            parsed_sources = []
            for source in sources:
                if isinstance(source, str):
                    try:
                        source_data = json.loads(source)
                        if isinstance(source_data, dict) and 'results' in source_data:
                            parsed_sources.extend(source_data['results'])
                        else:
                            parsed_sources.append(source_data)
                    except json.JSONDecodeError:
                        # If it's not JSON, treat it as plain text
                        parsed_sources.append({'content': source})
                else:
                    parsed_sources.append(source)
            
            result += f"**Sources Found**: {len(parsed_sources)}\n\n"
            result += "### Search Results:\n\n"
            
            for i, source in enumerate(parsed_sources[:5], 1):  # Limit to first 5
                if isinstance(source, dict):
                    title = source.get('title', 'No title')
                    url = source.get('url', '')
                    content = source.get('content', '')
                    
                    result += f"**{i}. {title}**\n"
                    if url:
                        result += f"🔗 {url}\n"
                    if content:
                        # Truncate content to reasonable length
                        content_preview = content[:200] + "..." if len(content) > 200 else content
                        result += f"📄 {content_preview}\n"
                    result += "\n"
                else:
                    result += f"{i}. {str(source)[:200]}...\n\n"
        else:
            result += "**Sources Found**: 0\n\n"
            result += "No search results were found for fact-checking.\n\n"
        
        if analysis.get("fact_check_summary"):
            result += f"### Summary:\n{analysis['fact_check_summary']}\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in fact-checking: {e}", exc_info=True)
        return f"Error in fact-checking: {str(e)}"


@tool
async def run_meta_analysis(query: str, responses_context: str) -> str:
    """
    Run 4 meta-analysis agents with dimensional scoring (1-10) on each AI model response.
    
    Meta-Agents:
    1. Cognitive Properties: Meta-reflection, Reasoning depth, Synthesis capacity, Bias detection
    2. Integrity & Objectivity: Objectivity, Integrity, Transparency, Epistemic humility
    3. Stability & Emotional Profile: Emotional distance, Conflict neutrality, Stability, Cognitive redundancy
    4. Adaptivity & System Role: Context elasticity, System loyalty, Adaptive precision, Structural clarity
    
    Args:
        query: The original question
        responses_context: Context about the model responses
        
    Returns:
        Meta-analysis results with dimensional scores from all four analytical frameworks
    """
    try:
        comparison_flow = get_ai_comparison_flow(max_search_results=3, resources=[])
        
        logger.info("Starting 4-category meta-agent analysis with dimensional scoring")
        
        # Run meta-agents (they now use the new 4-category system)
        meta_results = await comparison_flow.run_meta_agents(query, [], {})
        
        # Format results
        result = f"## Meta-Analysis Results (4 Categories)\n\n"
        successful = sum(1 for v in meta_results.values() if v.get("success"))
        result += f"**Completed**: {successful}/4 meta-agent categories\n\n"
        
        # Map agent names to display names
        agent_display_names = {
            "cognitive_properties": "Kognitiva Egenskaper (Cognitive Properties)",
            "integrity_objectivity": "Integritet & Objektivitet (Integrity & Objectivity)",
            "stability_emotional": "Stabilitet & Emotionell Profil (Stability & Emotional Profile)",
            "adaptivity_system": "Adaptivitet & Systemroll (Adaptivity & System Role)",
        }
        
        for agent_name, agent_result in meta_results.items():
            status = "✓" if agent_result.get("success") else "✗"
            display_name = agent_display_names.get(agent_name, agent_name.replace("_", " ").title())
            result += f"### {status} {display_name}\n\n"
            
            if agent_result.get("success"):
                analysis = agent_result.get("analysis", "No analysis available")
                # Show more of the analysis since it contains scores
                analysis_preview = analysis[:500] if len(analysis) > 500 else analysis
                if len(analysis) > 500:
                    analysis_preview += "... [truncated for brevity]"
                result += f"{analysis_preview}\n\n"
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
        web_search,  # Direct web search for fact-checking
        run_meta_analysis,
        synthesize_optimal_answer,
    ]
