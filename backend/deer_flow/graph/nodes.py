# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import logging
import os
from functools import partial
from typing import Annotated, Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
# MCP adapters import moved to conditional block where it's used
# from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.types import Command, interrupt

from backend.deer_flow.agents import create_agent
from backend.deer_flow.citations import extract_citations_from_messages, merge_citations
from backend.deer_flow.config.agents import AGENT_LLM_MAP
from backend.deer_flow.config.configuration import Configuration
from backend.deer_flow.llms.llm import get_llm_by_type, get_llm_token_limit_by_type, configure_llm_with_thinking
from backend.deer_flow.prompts.planner_model import Plan
from backend.deer_flow.prompts.template import apply_prompt_template
from backend.deer_flow.tools import (
    crawl_tool,
    get_retriever_tool,
    get_web_search_tool,
    python_repl_tool,
)
from backend.deer_flow.tools.ai_comparison_tools import get_ai_comparison_tools
from backend.deer_flow.tools.debate_tools import get_debate_tools
from backend.deer_flow.tools.search import LoggedTavilySearch
from backend.deer_flow.utils.context_manager import ContextManager, validate_message_content
from backend.deer_flow.utils.json_utils import repair_json_output, sanitize_tool_response

from ..config import SELECTED_SEARCH_ENGINE, SearchEngine
from .types import State
from .utils import (
    build_clarified_topic_from_history,
    get_message_content,
    is_user_message,
    reconstruct_clarification_history,
)

logger = logging.getLogger(__name__)


def is_json_like(content: str) -> bool:
    """
    Check if content looks like JSON by checking if it starts with { or [.
    
    This is a heuristic check for basic structural indicators, not actual JSON validation.
    """
    if not content:
        return False
    stripped = content.strip()
    return stripped.startswith('{') or stripped.startswith('[')


def strip_think_tags(content: str, expect_json: bool = False) -> str:
    """
    Strip <think> tags from content, intelligently handling different placements.
    
    This function handles multiple cases:
    1. Standard case: Content after </think> tag (e.g., "<think>...</think>actual content")
    2. Edge case: Content inside <think> tags (e.g., "<think>actual content</think>")
    3. Edge case: Content before <think> tag (e.g., "actual content<think>...</think>")
    4. No tags: Returns content as-is
    5. Only tags with no content: Returns empty string
    
    For JSON responses (when expect_json=True), it tries content after </think> first,
    then falls back to content inside tags if the after-content is empty or invalid JSON.
    For non-JSON responses, it tries content after, before, then inside tags.
    
    Args:
        content: The content potentially containing <think> tags
        expect_json: If True, applies JSON-specific logic for fallback
        
    Returns:
        Content with <think> tags stripped appropriately
    """
    if not content or '<think>' not in content or '</think>' not in content:
        return content
    
    think_start = content.find('<think>')
    think_end = content.find('</think>')
    
    # Validate that tags are in correct order
    if think_start >= think_end or think_start < 0 or think_end < 0:
        # Invalid tag ordering, return content as-is
        return content
    
    # Extract all potential content locations
    content_before = content[:think_start].strip()
    content_inside = content[think_start + len('<think>'):think_end].strip()
    content_after = content[think_end + len('</think>'):].strip()
    
    if expect_json:
        # For JSON: prefer after, but fall back to inside if after is not valid JSON
        if content_after and is_json_like(content_after):
            return content_after
        if content_inside and is_json_like(content_inside):
            return content_inside
        if content_before and is_json_like(content_before):
            return content_before
        # Fallback to after even if empty/invalid (will be caught by validation)
        return content_after
    else:
        # For non-JSON: prefer after, then before, then inside
        if content_after:
            return content_after
        if content_before:
            return content_before
        if content_inside:
            return content_inside
        # Fallback: return empty string to avoid showing just the tags
        return ""


@tool
def handoff_to_planner(
    research_topic: Annotated[str, "The topic of the research task to be handed off."],
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
):
    """Handoff to planner agent to do plan."""
    # This tool is not returning anything: we're just using it
    # as a way for LLM to signal that it needs to hand off to planner agent
    return


@tool
def handoff_after_clarification(
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
    research_topic: Annotated[
        str, "The clarified research topic based on all clarification rounds."
    ],
):
    """Handoff to planner after clarification rounds are complete. Pass all clarification history to planner for analysis."""
    return


@tool
def direct_response(
    message: Annotated[str, "The response message to send directly to user."],
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
):
    """Respond directly to user for greetings, small talk, or polite rejections. Do NOT use this for research questions - use handoff_to_planner instead."""
    return


@tool
def handoff_to_coder(
    code_task: Annotated[str, "The specific code-related task or question to be handled."],
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
    clarity: Annotated[str, "Whether the code task is 'clear' or 'unclear'. Use 'unclear' if the task needs human clarification."],
):
    """Handoff to coder agent for code-related questions, development, or debugging tasks. 
    Use this for questions about programming, code execution, building applications, or technical development.
    Set clarity='unclear' if the task requires human clarification before proceeding."""
    return


@tool
def handoff_to_code_planner(
    code_task: Annotated[str, "The specific code development task requiring structured planning."],
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
):
    """Handoff to code planner for structured code development with planning, implementation, and testing phases.
    Use this for complex code tasks that benefit from:
    - Structured planning before implementation
    - Research/documentation gathering
    - Multiple implementation steps
    - Testing and validation requirements
    
    For simple, quick code questions, use handoff_to_coder instead."""
    return


def is_code_related_question(question: str) -> bool:
    """
    Detect if a question is code-related using keyword matching and patterns.
    
    Args:
        question: The user's question or research topic
        
    Returns:
        True if the question appears to be code-related
    """
    if not question:
        return False
    
    question_lower = question.lower()
    
    # Code-related keywords
    code_keywords = [
        # Programming languages
        'python', 'javascript', 'java', 'typescript', 'c++', 'c#', 'ruby', 'go', 'rust',
        'php', 'swift', 'kotlin', 'scala', 'dart', 'r', 'matlab',
        # Code-related terms
        'code', 'coding', 'program', 'programming', 'script', 'function', 'method', 'class',
        'algorithm', 'debug', 'compile', 'execute', 'syntax', 'error', 'exception',
        'implement', 'development', 'software', 'application', 'api', 'library', 'framework',
        # Web development
        'react', 'vue', 'angular', 'next.js', 'node.js', 'express', 'django', 'flask',
        'html', 'css', 'frontend', 'backend', 'fullstack', 'web app',
        # Tools and technologies
        'docker', 'kubernetes', 'git', 'github', 'sql', 'database', 'mongodb',
        'linux', 'bash', 'shell', 'terminal', 'command line', 'cli',
        # Code actions
        'write code', 'create app', 'build', 'deploy', 'test', 'unit test', 'integration',
        'refactor', 'optimize', 'fix bug', 'review code',
    ]
    
    return any(keyword in question_lower for keyword in code_keywords)


def needs_clarification(state: dict) -> bool:
    """
    Check if clarification is needed based on current state.
    Centralized logic for determining when to continue clarification.
    """
    if not state.get("enable_clarification", False):
        return False

    clarification_rounds = state.get("clarification_rounds", 0)
    is_clarification_complete = state.get("is_clarification_complete", False)
    max_clarification_rounds = state.get("max_clarification_rounds", 3)

    # Need clarification if: enabled + has rounds + not complete + not exceeded max
    # Use <= because after asking the Nth question, we still need to wait for the Nth answer
    return (
        clarification_rounds > 0
        and not is_clarification_complete
        and clarification_rounds <= max_clarification_rounds
    )


def preserve_state_meta_fields(state: State) -> dict:
    """
    Extract meta/config fields that should be preserved across state transitions.
    
    These fields are critical for workflow continuity and should be explicitly
    included in all Command.update dicts to prevent them from reverting to defaults.
    
    Args:
        state: Current state object
        
    Returns:
        Dict of meta fields to preserve
    """
    return {
        "locale": state.get("locale", "en-US"),
        "research_topic": state.get("research_topic", ""),
        "clarified_research_topic": state.get("clarified_research_topic", ""),
        "clarification_history": state.get("clarification_history", []),
        "enable_clarification": state.get("enable_clarification", False),
        "max_clarification_rounds": state.get("max_clarification_rounds", 3),
        "clarification_rounds": state.get("clarification_rounds", 0),
        "resources": state.get("resources", []),
        # Debate state fields (CRITICAL: preserve across all transitions!)
        "debate_round": state.get("debate_round", 0),
        "debate_scores": state.get("debate_scores", {"proponent": 0, "opponent": 0}),
        "debate_knockout": state.get("debate_knockout", False),
        "debate_max_rounds": state.get("debate_max_rounds", 3),
        "debate_error_count": state.get("debate_error_count", 0),
        "debate_complete": state.get("debate_complete", False),
    }


def validate_and_fix_plan(plan: dict, enforce_web_search: bool = False, enable_web_search: bool = True) -> dict:
    """
    Validate and fix a plan to ensure it meets requirements.

    Args:
        plan: The plan dict to validate
        enforce_web_search: If True, ensure at least one step has need_search=true
        enable_web_search: If False, skip web search enforcement (takes precedence)

    Returns:
        The validated/fixed plan dict
    """
    if not isinstance(plan, dict):
        return plan

    steps = plan.get("steps", [])

    # ============================================================
    # SECTION 1: Repair missing step_type fields (Issue #650 fix)
    # ============================================================
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        
        # Check if step_type is missing or empty
        if "step_type" not in step or not step.get("step_type"):
            # Infer step_type based on need_search value
            # Default to "analysis" for non-search steps (Issue #677: not all processing needs code)
            inferred_type = "research" if step.get("need_search", False) else "analysis"
            step["step_type"] = inferred_type
            logger.info(
                f"Repaired missing step_type for step {idx} ({step.get('title', 'Untitled')}): "
                f"inferred as '{inferred_type}' based on need_search={step.get('need_search', False)}"
            )

    # ============================================================
    # SECTION 2: Enforce web search requirements
    # Skip enforcement if web search is disabled (enable_web_search=False takes precedence)
    # ============================================================
    if enforce_web_search and enable_web_search:
        # Check if any step has need_search=true (only check dict steps)
        has_search_step = any(
            step.get("need_search", False) 
            for step in steps 
            if isinstance(step, dict)
        )

        if not has_search_step and steps:
            # Ensure first research step has web search enabled
            for idx, step in enumerate(steps):
                if isinstance(step, dict) and step.get("step_type") == "research":
                    step["need_search"] = True
                    logger.info(f"Enforced web search on research step at index {idx}")
                    break
            else:
                # Fallback: If no research step exists, convert the first step to a research step with web search enabled.
                # This ensures that at least one step will perform a web search as required.
                if isinstance(steps[0], dict):
                    steps[0]["step_type"] = "research"
                    steps[0]["need_search"] = True
                    logger.info(
                        "Converted first step to research with web search enforcement"
                    )
        elif not has_search_step and not steps:
            # Add a default research step if no steps exist
            logger.warning("Plan has no steps. Adding default research step.")
            plan["steps"] = [
                {
                    "need_search": True,
                    "title": "Initial Research",
                    "description": "Gather information about the topic",
                    "step_type": "research",
                }
            ]

    return plan


def background_investigation_node(state: State, config: RunnableConfig):
    logger.info("background investigation node is running.")
    configurable = Configuration.from_runnable_config(config)

    # Background investigation relies on web search; skip entirely when web search is disabled
    if not configurable.enable_web_search:
        logger.info("Web search is disabled, skipping background investigation.")
        return {"background_investigation_results": json.dumps([], ensure_ascii=False)}

    query = state.get("clarified_research_topic") or state.get("research_topic")
    background_investigation_results = []
    
    if SELECTED_SEARCH_ENGINE == SearchEngine.TAVILY.value:
        searched_content = LoggedTavilySearch(
            max_results=configurable.max_search_results
        ).invoke(query)
        # check if the searched_content is a tuple, then we need to unpack it
        if isinstance(searched_content, tuple):
            searched_content = searched_content[0]
        
        # Handle string JSON response (new format from fixed Tavily tool)
        if isinstance(searched_content, str):
            try:
                parsed = json.loads(searched_content)
                if isinstance(parsed, dict) and "error" in parsed:
                    logger.error(f"Tavily search error: {parsed['error']}")
                    background_investigation_results = []
                elif isinstance(parsed, list):
                    background_investigation_results = [
                        f"## {elem.get('title', 'Untitled')}\n\n{elem.get('content', 'No content')}" 
                        for elem in parsed
                    ]
                else:
                    logger.error(f"Unexpected Tavily response format: {searched_content}")
                    background_investigation_results = []
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Tavily response as JSON: {searched_content}")
                background_investigation_results = []
        # Handle legacy list format
        elif isinstance(searched_content, list):
            background_investigation_results = [
                f"## {elem['title']}\n\n{elem['content']}" for elem in searched_content
            ]
            return {
                "background_investigation_results": "\n\n".join(
                    background_investigation_results
                )
            }
        else:
            logger.error(
                f"Tavily search returned malformed response: {searched_content}"
            )
            background_investigation_results = []
    else:
        background_investigation_results = get_web_search_tool(
            configurable.max_search_results
        ).invoke(query)
    
    return {
        "background_investigation_results": json.dumps(
            background_investigation_results, ensure_ascii=False
        )
    }


def planner_node(
    state: State, config: RunnableConfig
) -> Command[Literal["human_feedback", "reporter"]]:
    """Planner node that generate the full plan."""
    logger.info("Planner generating full plan with locale: %s", state.get("locale", "en-US"))
    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0

    # For clarification feature: use the clarified research topic (complete history)
    if state.get("enable_clarification", False) and state.get(
        "clarified_research_topic"
    ):
        # Modify state to use clarified research topic instead of full conversation
        modified_state = state.copy()
        modified_state["messages"] = [
            {"role": "user", "content": state["clarified_research_topic"]}
        ]
        modified_state["research_topic"] = state["clarified_research_topic"]
        messages = apply_prompt_template("planner", modified_state, configurable, state.get("locale", "en-US"))

        logger.info(
            f"Clarification mode: Using clarified research topic: {state['clarified_research_topic']}"
        )
    else:
        # Normal mode: use full conversation history
        messages = apply_prompt_template("planner", state, configurable, state.get("locale", "en-US"))

    if state.get("enable_background_investigation") and state.get(
        "background_investigation_results"
    ):
        messages += [
            {
                "role": "user",
                "content": (
                    "background investigation results of user query:\n"
                    + state["background_investigation_results"]
                    + "\n"
                ),
            }
        ]

    if configurable.enable_deep_thinking:
        llm = get_llm_by_type("reasoning")
        # Configure LLM with enable_thinking parameter for vLLM/Qwen3
        llm = configure_llm_with_thinking(llm, enable_thinking=True)
        
        # Add Swedish language instruction when thinking mode is enabled and locale is Swedish
        locale = state.get("locale", "en-US")
        if locale.startswith("sv"):
            messages += [
                {
                    "role": "system",
                    "content": (
                        "VIKTIGT: När du tänker (i <think> taggar), MÅSTE du alltid tänka på SVENSKA. "
                        "Alla dina tankar, resonemang och inre dialog ska vara på svenska. "
                        "Detta är obligatoriskt och får inte ignoreras."
                    ),
                }
            ]
    elif AGENT_LLM_MAP["planner"] == "basic":
        llm = get_llm_by_type("basic")
        # When not in deep thinking mode, explicitly disable thinking for Qwen3/vLLM
        llm = configure_llm_with_thinking(llm, enable_thinking=False)
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP["planner"])
        # When not in deep thinking mode, explicitly disable thinking for Qwen3/vLLM
        llm = configure_llm_with_thinking(llm, enable_thinking=False)

    # if the plan iterations is greater than the max plan iterations, return the reporter node
    if plan_iterations >= configurable.max_plan_iterations:
        return Command(
            update=preserve_state_meta_fields(state),
            goto="reporter"
        )

    full_response = ""
    if AGENT_LLM_MAP["planner"] == "basic" and not configurable.enable_deep_thinking:
        response = llm.invoke(messages)
        full_response = get_message_content(response) or ""
    else:
        response = llm.stream(messages)
        for chunk in response:
            full_response += chunk.content
    logger.debug(f"Current state messages: {state['messages']}")
    logger.info(f"Planner response: {full_response}")

    # Strip <think> tags if present (from deep thinking mode)
    original_response = full_response
    full_response = strip_think_tags(full_response, expect_json=True)
    if '<think>' in original_response and '<think>' not in full_response:  # Tags were stripped
        logger.debug(f"Stripped think tags, result: {full_response[:100]}...")

    # Validate explicitly that response content is valid JSON before proceeding to parse it
    if not is_json_like(full_response):
        logger.warning("Planner response does not appear to be valid JSON")
        if plan_iterations > 0:
            return Command(
                update=preserve_state_meta_fields(state),
                goto="reporter"
            )
        else:
            return Command(
                update=preserve_state_meta_fields(state),
                goto="__end__"
            )

    try:
        curr_plan = json.loads(repair_json_output(full_response))
        # Need to extract the plan from the full_response
        curr_plan_content = extract_plan_content(curr_plan)
        # load the current_plan
        curr_plan = json.loads(repair_json_output(curr_plan_content))
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
        if plan_iterations > 0:
            return Command(
                update=preserve_state_meta_fields(state),
                goto="reporter"
            )
        else:
            return Command(
                update=preserve_state_meta_fields(state),
                goto="__end__"
            )

    # Validate and fix plan to ensure web search requirements are met
    if isinstance(curr_plan, dict):
        curr_plan = validate_and_fix_plan(curr_plan, configurable.enforce_web_search, configurable.enable_web_search)

    if isinstance(curr_plan, dict) and curr_plan.get("has_enough_context"):
        logger.info("Planner response has enough context.")
        new_plan = Plan.model_validate(curr_plan)
        return Command(
            update={
                "messages": [AIMessage(content=full_response, name="planner")],
                "current_plan": new_plan,
                **preserve_state_meta_fields(state),
            },
            goto="reporter",
        )
    # Check if AI comparison mode is enabled
    if state.get("enable_ai_comparison", False):
        logger.info("Planner: AI comparison mode enabled, routing to ai_comparison node")
        return Command(
            update={
                "messages": [AIMessage(content=full_response, name="planner")],
                "current_plan": full_response,
                **preserve_state_meta_fields(state),
            },
            goto="ai_comparison",
        )
    
    return Command(
        update={
            "messages": [AIMessage(content=full_response, name="planner")],
            "current_plan": full_response,
            **preserve_state_meta_fields(state),
        },
        goto="human_feedback",
    )


def debate_planner_node(
    state: State, config: RunnableConfig
) -> Command[Literal["human_feedback"]]:
    """
    Debate planner node - creates a debate plan with multiple rounds where AI models
    participate as equal debaters. Follows the same workflow as normal research planning:
    debate_planner → human_feedback → research_team → researcher (with debate tools) → reporter
    
    This is essentially a simplified version of planner_node that generates a fixed debate plan structure.
    """
    logger.info("Debate planner generating debate plan with locale: %s", state.get("locale", "en-US"))
    configurable = Configuration.from_runnable_config(config)
    
    # Use the debate_planner prompt template
    messages = apply_prompt_template("debate_planner", state, configurable, state.get("locale", "en-US"))
    
    # Get LLM for debate planner
    if AGENT_LLM_MAP.get("debate_planner") == "basic":
        llm = get_llm_by_type("basic")
        llm = configure_llm_with_thinking(llm, enable_thinking=False)
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP.get("debate_planner", "basic"))
        llm = configure_llm_with_thinking(llm, enable_thinking=False)
    
    # Invoke/stream LLM to get debate plan (EXACT match to planner_node logic)
    # CRITICAL: Use the same invoke/stream logic as planner_node for frontend streaming
    full_response = ""
    if AGENT_LLM_MAP.get("debate_planner") == "basic" and not configurable.enable_deep_thinking:
        response = llm.invoke(messages)
        full_response = get_message_content(response) or ""
    else:
        response = llm.stream(messages)
        for chunk in response:
            full_response += chunk.content
    
    logger.info(f"Debate planner response: {full_response}")
    
    # Strip <think> tags if present (matching planner_node behavior)
    original_response = full_response
    full_response = strip_think_tags(full_response, expect_json=True)
    if '<think>' in original_response and '<think>' not in full_response:
        logger.debug(f"Stripped think tags from debate planner response")
    
    # Strip markdown code fences if present (LLM sometimes wraps JSON in ```json ... ```)
    full_response = full_response.strip()
    if full_response.startswith("```"):
        # Remove opening fence (e.g., ```json or just ```)
        lines = full_response.split('\n')
        if len(lines) > 0:
            lines = lines[1:]  # Remove first line with ```
        # Remove closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        full_response = '\n'.join(lines).strip()
        logger.debug(f"Stripped markdown code fences from debate planner response")
    
    # Validate explicitly that response content is valid JSON before proceeding
    if not is_json_like(full_response):
        logger.warning("Debate planner response does not appear to be valid JSON")
        return Command(
            update=preserve_state_meta_fields(state),
            goto="__end__"
        )
    
    # Parse and repair JSON (matching planner_node behavior)
    try:
        curr_plan = json.loads(repair_json_output(full_response))
        # Need to extract the plan from the full_response
        curr_plan_content = extract_plan_content(curr_plan)
        # load the current_plan
        curr_plan = json.loads(repair_json_output(curr_plan_content))
    except json.JSONDecodeError as e:
        logger.warning(f"Debate planner response is not valid JSON: {e}")
        return Command(
            update=preserve_state_meta_fields(state),
            goto="__end__"
        )
    
    # Validate and fix plan to ensure web search requirements are met (matching planner_node)
    if isinstance(curr_plan, dict):
        curr_plan = validate_and_fix_plan(curr_plan, configurable.enforce_web_search, configurable.enable_web_search)
    
    # Check if plan has enough context (matching planner_node)
    if isinstance(curr_plan, dict) and curr_plan.get("has_enough_context"):
        logger.info("Debate planner response has enough context.")
        new_plan = Plan.model_validate(curr_plan)
        return Command(
            update={
                "messages": [AIMessage(content=json.dumps(curr_plan, ensure_ascii=False, indent=2), name="planner")],
                "current_plan": new_plan,
                **preserve_state_meta_fields(state),
            },
            goto="reporter",
        )
    
    # Convert plan to JSON string for human_feedback (matching planner_node)
    full_response = json.dumps(curr_plan, ensure_ascii=False, indent=2)
    logger.debug(f"Successfully parsed and prepared debate plan for human_feedback")
    
    # Return the plan to human_feedback (same as planner_node)
    # IMPORTANT: Use name="planner" so frontend recognizes it and displays the plan card
    return Command(
        update={
            "messages": [AIMessage(content=full_response, name="planner")],
            "current_plan": full_response,  # Pass as JSON string like planner does
            **preserve_state_meta_fields(state),
        },
        goto="human_feedback",
    )


def code_planner_node(
    state: State, config: RunnableConfig
) -> Command[Literal["human_feedback"]]:
    """
    Code planner node - creates a structured plan for code development tasks.
    Follows the same workflow as debate planning:
    code_planner → human_feedback → research_team → coder/tester (with code tools) → reporter
    
    This node generates a detailed plan for code implementation, testing, and validation.
    """
    logger.info("Code planner generating code development plan with locale: %s", state.get("locale", "en-US"))
    configurable = Configuration.from_runnable_config(config)
    
    # Use the code_planner prompt template
    messages = apply_prompt_template("code_planner", state, configurable, state.get("locale", "en-US"))
    
    # Get LLM for code planner
    if AGENT_LLM_MAP.get("code_planner") == "basic":
        llm = get_llm_by_type("basic")
        llm = configure_llm_with_thinking(llm, enable_thinking=False)
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP.get("code_planner", "basic"))
        llm = configure_llm_with_thinking(llm, enable_thinking=False)
    
    # Invoke/stream LLM to get code plan (EXACT match to planner_node logic)
    full_response = ""
    if AGENT_LLM_MAP.get("code_planner") == "basic" and not configurable.enable_deep_thinking:
        response = llm.invoke(messages)
        full_response = get_message_content(response) or ""
    else:
        response = llm.stream(messages)
        for chunk in response:
            full_response += chunk.content
    
    logger.info(f"Code planner response: {full_response}")
    
    # Strip <think> tags if present (matching planner_node behavior)
    original_response = full_response
    full_response = strip_think_tags(full_response, expect_json=True)
    if '<think>' in original_response and '<think>' not in full_response:
        logger.debug(f"Stripped think tags from code planner response")
    
    # Strip markdown code fences if present (LLM sometimes wraps JSON in ```json ... ```)
    full_response = full_response.strip()
    if full_response.startswith("```"):
        # Remove opening fence (e.g., ```json or just ```)
        lines = full_response.split('\n')
        if len(lines) > 0:
            lines = lines[1:]  # Remove first line with ```
        # Remove closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        full_response = '\n'.join(lines).strip()
        logger.debug(f"Stripped markdown code fences from code planner response")
    
    # Validate explicitly that response content is valid JSON before proceeding
    if not is_json_like(full_response):
        logger.warning("Code planner response does not appear to be valid JSON")
        return Command(
            update=preserve_state_meta_fields(state),
            goto="__end__"
        )
    
    # Parse and repair JSON (matching planner_node behavior)
    try:
        curr_plan = json.loads(repair_json_output(full_response))
        # Need to extract the plan from the full_response
        curr_plan_content = extract_plan_content(curr_plan)
        # load the current_plan
        curr_plan = json.loads(repair_json_output(curr_plan_content))
    except json.JSONDecodeError as e:
        logger.warning(f"Code planner response is not valid JSON: {e}")
        return Command(
            update=preserve_state_meta_fields(state),
            goto="__end__"
        )
    
    # Validate and fix plan to ensure web search requirements are met (matching planner_node)
    if isinstance(curr_plan, dict):
        curr_plan = validate_and_fix_plan(curr_plan, configurable.enforce_web_search, configurable.enable_web_search)
    
    # Check if plan has enough context (matching planner_node)
    if isinstance(curr_plan, dict) and curr_plan.get("has_enough_context"):
        logger.info("Code planner response has enough context.")
        new_plan = Plan.model_validate(curr_plan)
        return Command(
            update={
                "messages": [AIMessage(content=json.dumps(curr_plan, ensure_ascii=False, indent=2), name="planner")],
                "current_plan": new_plan,
                **preserve_state_meta_fields(state),
            },
            goto="reporter",
        )
    
    # Convert plan to JSON string for human_feedback (matching planner_node)
    full_response = json.dumps(curr_plan, ensure_ascii=False, indent=2)
    logger.debug(f"Successfully parsed and prepared code plan for human_feedback")
    
    # Return the plan to human_feedback (same as planner_node)
    # IMPORTANT: Use name="planner" so frontend recognizes it and displays the plan card
    return Command(
        update={
            "messages": [AIMessage(content=full_response, name="planner")],
            "current_plan": full_response,  # Pass as JSON string like planner does
            **preserve_state_meta_fields(state),
        },
        goto="human_feedback",
    )


def extract_plan_content(plan_data: str | dict | Any) -> str:
    """
    Safely extract plan content from different types of plan data.
    
    Args:
        plan_data: The plan data which can be a string, AIMessage, or dict
        
    Returns:
        str: The plan content as a string (JSON string for dict inputs, or 
    extracted/original string for other types)
    """
    if isinstance(plan_data, str):
        # If it's already a string, return as is
        return plan_data
    elif hasattr(plan_data, 'content') and isinstance(plan_data.content, str):
        # If it's an AIMessage or similar object with a content attribute
        logger.debug(f"Extracting plan content from message object of type {type(plan_data).__name__}")
        return plan_data.content
    elif isinstance(plan_data, dict):
        # If it's already a dictionary, convert to JSON string
        # Need to check if it's dict with content field (AIMessage-like)
        if "content" in plan_data:
            if isinstance(plan_data["content"], str):
                logger.debug("Extracting plan content from dict with content field")
                return plan_data["content"]
            if isinstance(plan_data["content"], dict):
                logger.debug("Converting content field dict to JSON string")
                return json.dumps(plan_data["content"], ensure_ascii=False)
            else:
                logger.warning(f"Unexpected type for 'content' field in plan_data dict: {type(plan_data['content']).__name__}, converting to string")
                return str(plan_data["content"])
        else:
            logger.debug("Converting plan dictionary to JSON string")
            return json.dumps(plan_data)
    else:
        # For any other type, try to convert to string
        logger.warning(f"Unexpected plan data type {type(plan_data).__name__}, attempting to convert to string")
        return str(plan_data)


def human_feedback_node(
    state: State, config: RunnableConfig
) -> Command[Literal["planner", "research_team", "reporter", "debate_orchestrator", "__end__"]]:
    coder_flag = state.get('coder_just_completed', False)
    logger.info(f"[human_feedback_node] ENTERED - coder_just_completed={coder_flag}")
    logger.info(f"[human_feedback_node] State keys: {list(state.keys())}")
    logger.info(f"[human_feedback_node] 'coder_just_completed' in state: {'coder_just_completed' in state}")
    
    # Check if coder just completed - if so, ask about testing
    if coder_flag:
        logger.info("[human_feedback_node] Coder just completed. Asking user about testing.")
        locale = state.get("locale", "en-US")
        
        # Ask in appropriate language
        if locale.startswith("sv"):
            prompt = "Kodningen är klar! Vill du att jag testar koden?\n\nSvara '[TEST]' för att köra tester (pytest, pylint, mypy), eller '[SKIP]' för att hoppa över testning."
        else:
            prompt = "Coding is complete! Would you like me to test the code?\n\nReply '[TEST]' to run tests (pytest, pylint, mypy), or '[SKIP]' to skip testing."
        
        logger.info(f"[human_feedback_node] Calling interrupt() with prompt (locale={locale}): {prompt[:100]}...")
        feedback = interrupt(prompt)
        logger.info(f"[human_feedback_node] interrupt() returned: {feedback}")
        
        # Handle feedback
        if not feedback:
            logger.warning("[human_feedback_node] No feedback received for testing decision. Skipping testing.")
            return Command(
                update={
                    "coder_just_completed": False,  # Clear flag
                    **preserve_state_meta_fields(state),
                },
                goto="reporter"
            )
        
        feedback_normalized = str(feedback).strip().upper()
        
        if feedback_normalized.startswith("[TEST]"):
            logger.info("User requested testing. Creating TESTING step and routing to research_team.")
            # Add a TESTING step to the current plan
            current_plan = state.get("current_plan")
            if current_plan and hasattr(current_plan, 'steps'):
                from backend.deer_flow.prompts.planner_model import Step, StepType
                
                # Create testing step
                test_step = Step(
                    title="Test and Validate Code" if not locale.startswith("sv") else "Testa och Validera Kod",
                    description="Run pytest for unit tests, pylint for code quality, and mypy for type checking." if not locale.startswith("sv") else "Kör pytest för enhetstester, pylint för kodkvalitet och mypy för typkontroll.",
                    step_type=StepType.TESTING,
                    need_search=False,
                    execution_res=None
                )
                
                # Add testing step to plan
                current_plan.steps.append(test_step)
                logger.info(f"Added TESTING step to plan. Total steps: {len(current_plan.steps)}")
                
                return Command(
                    update={
                        "current_plan": current_plan,
                        "coder_just_completed": False,  # Clear flag
                        **preserve_state_meta_fields(state),
                    },
                    goto="research_team"
                )
        
        # If [SKIP] or any other response, skip testing and go to reporter
        logger.info("User declined testing or provided invalid response. Skipping testing, going to reporter.")
        return Command(
            update={
                "coder_just_completed": False,  # Clear flag
                **preserve_state_meta_fields(state),
            },
            goto="reporter"
        )
    
    # Original human_feedback_node logic for plan approval
    current_plan = state.get("current_plan", "")
    # check if the plan is auto accepted
    auto_accepted_plan = state.get("auto_accepted_plan", False)
    if not auto_accepted_plan:
        feedback = interrupt("Please Review the Plan.")

        # Handle None or empty feedback
        if not feedback:
            logger.warning(f"Received empty or None feedback: {feedback}. Returning to planner for new plan.")
            return Command(
                update=preserve_state_meta_fields(state),
                goto="planner"
            )

        # Normalize feedback string
        feedback_normalized = str(feedback).strip().upper()

        # if the feedback is not accepted, return the planner node
        if feedback_normalized.startswith("[EDIT_PLAN]"):
            logger.info(f"Plan edit requested by user: {feedback}")
            return Command(
                update={
                    "messages": [
                        HumanMessage(content=feedback, name="feedback"),
                    ],
                    **preserve_state_meta_fields(state),
                },
                goto="planner",
            )
        elif feedback_normalized.startswith("[ACCEPTED]"):
            logger.info("Plan is accepted by user.")
        else:
            logger.warning(f"Unsupported feedback format: {feedback}. Please use '[ACCEPTED]' to accept or '[EDIT_PLAN]' to edit.")
            return Command(
                update=preserve_state_meta_fields(state),
                goto="planner"
            )

    # if the plan is accepted, run the following node
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    
    # Determine routing based on mode
    if state.get("debate_complete", False):
        # Debate is complete - route to END (debate has separate chain, never use research_team)
        goto = END
        logger.info("[human_feedback_node] Debate complete, routing to END (debate is separate chain)")
    elif state.get("enable_debate_mode", False):
        # Debate mode - route to debate_orchestrator after plan approval
        goto = "debate_orchestrator"
        logger.info("[human_feedback_node] Plan approved in debate mode, routing to debate_orchestrator")
    else:
        # Normal mode - route to research_team
        goto = "research_team"
        logger.info("[human_feedback_node] Plan approved, routing to research_team")
    
    try:
        # Safely extract plan content from different types (string, AIMessage, dict)
        original_plan = current_plan
        
        # Repair the JSON output
        current_plan = repair_json_output(current_plan)
        # parse the plan to dict
        current_plan = json.loads(current_plan)
        current_plan_content = extract_plan_content(current_plan)
        
        # increment the plan iterations
        plan_iterations += 1
        # parse the plan
        new_plan = json.loads(repair_json_output(current_plan_content))
        # Validate and fix plan to ensure web search requirements are met
        configurable = Configuration.from_runnable_config(config)
        new_plan = validate_and_fix_plan(new_plan, configurable.enforce_web_search, configurable.enable_web_search)
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"Failed to parse plan: {str(e)}. Plan data type: {type(current_plan).__name__}")
        if isinstance(current_plan, dict) and "content" in original_plan:
            logger.warning(f"Plan appears to be an AIMessage object with content field")
        if plan_iterations > 1:  # the plan_iterations is increased before this check
            return Command(
                update=preserve_state_meta_fields(state),
                goto="reporter"
            )
        else:
            return Command(
                update=preserve_state_meta_fields(state),
                goto="__end__"
            )

    # Build update dict with safe locale handling
    update_dict = {
        "current_plan": Plan.model_validate(new_plan),
        "plan_iterations": plan_iterations,
        **preserve_state_meta_fields(state),
    }
    
    # Only override locale if new_plan provides a valid value, otherwise use preserved locale
    if new_plan.get("locale"):
        update_dict["locale"] = new_plan["locale"]
    
    # Initialize debate state if routing to debate_orchestrator
    if goto == "debate_orchestrator":
        update_dict.update({
            "debate_round": 0,
            "debate_max_rounds": 3,
            "debate_scores": {"external_ai": 0, "consensus": 0},
            "debate_knockout": False,
        })
    
    return Command(
        update=update_dict,
        goto=goto,
    )


def coordinator_node(
    state: State, config: RunnableConfig
) -> Command[Literal["planner", "background_investigator", "ai_comparison", "debate_planner", "code_planner", "coordinator", "coder", "human_feedback", "__end__"]]:
    """Coordinator node that communicate with customers and handle clarification."""
    logger.info("Coordinator talking.")
    configurable = Configuration.from_runnable_config(config)

    # Check if clarification is enabled
    enable_clarification = state.get("enable_clarification", False)
    initial_topic = state.get("research_topic", "")
    clarified_topic = initial_topic
    direct_response_message = None  # Store direct response message to preserve it
    # ============================================================
    # BRANCH 1: Clarification DISABLED (Legacy Mode)
    # ============================================================
    if not enable_clarification:
        # Use normal prompt with explicit instruction to skip clarification
        messages = apply_prompt_template("coordinator", state, locale=state.get("locale", "en-US"))
        messages.append(
            {
                "role": "system",
                "content": "Clarification is DISABLED. For research questions, use handoff_to_planner. For greetings or small talk, use direct_response. Do NOT ask clarifying questions.",
            }
        )

        # Bind handoff_to_planner, direct_response, handoff_to_coder, and handoff_to_code_planner tools
        tools = [handoff_to_planner, direct_response, handoff_to_coder, handoff_to_code_planner]
        response = (
            get_llm_by_type(AGENT_LLM_MAP["coordinator"])
            .bind_tools(tools)
            .invoke(messages)
        )

        goto = "__end__"
        locale = state.get("locale", "en-US")
        logger.info(f"Coordinator locale: {locale}")
        research_topic = state.get("research_topic", "")

        # Process tool calls for legacy mode
        if response.tool_calls:
            try:
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("args", {})

                    if tool_name == "handoff_to_planner":
                        logger.info("Handing off to planner")
                        
                        # Check debate mode first - route directly to debate_planner
                        if state.get("enable_debate_mode", False):
                            logger.info("Debate mode enabled, routing to debate_planner")
                            goto = "debate_planner"
                        # Check AI comparison mode - route to planner (which routes to ai_comparison)
                        elif state.get("enable_ai_comparison", False):
                            logger.info("AI comparison mode enabled, planner will route to ai_comparison")
                            goto = "planner"
                        # Normal research mode
                        else:
                            goto = "planner"

                        # Extract research_topic if provided
                        if tool_args.get("research_topic"):
                            research_topic = tool_args.get("research_topic")
                        break
                    elif tool_name == "handoff_to_coder":
                        logger.info("Handing off to coder for code-related task")
                        
                        # Extract code task and clarity
                        code_task = tool_args.get("code_task", research_topic)
                        clarity = tool_args.get("clarity", "clear")
                        
                        # Route based on clarity - NEW: Route directly to coder, not through planner
                        if clarity == "unclear":
                            logger.info("Code task is unclear, routing to human_feedback first")
                            goto = "human_feedback"
                        else:
                            logger.info("Code task is clear, routing directly to coder")
                            goto = "coder"
                        
                        # Mark research topic with [CODE] prefix to help coder detect direct call
                        research_topic = f"[CODE] {code_task}"
                        break
                    elif tool_name == "handoff_to_code_planner":
                        logger.info("Handing off to code_planner for structured code development")
                        
                        # Extract code task
                        code_task = tool_args.get("code_task", research_topic)
                        
                        # Check if code planner mode is enabled (similar to debate mode check)
                        # If not explicitly enabled, default to using it when the tool is called
                        logger.info("Code planner mode activated, routing to code_planner")
                        goto = "code_planner"
                        
                        # Set research topic for code planner
                        research_topic = code_task
                        break
                    elif tool_name == "direct_response":
                        logger.info("Direct response to user (greeting/small talk)")
                        goto = "__end__"
                        # Store direct message to add it later after messages are rebuilt
                        if tool_args.get("message"):
                            direct_response_message = AIMessage(content=tool_args.get("message"), name="coordinator")
                        break

            except Exception as e:
                logger.error(f"Error processing tool calls: {e}")
                goto = "planner"

        # Do not return early - let code flow to unified return logic below
        # Set clarification variables for legacy mode
        clarification_rounds = 0
        clarification_history = []
        clarified_topic = research_topic

    # ============================================================
    # BRANCH 2: Clarification ENABLED (New Feature)
    # ============================================================
    else:
        # Load clarification state
        clarification_rounds = state.get("clarification_rounds", 0)
        clarification_history = list(state.get("clarification_history", []) or [])
        clarification_history = [item for item in clarification_history if item]
        max_clarification_rounds = state.get("max_clarification_rounds", 3)

        # Prepare the messages for the coordinator
        state_messages = list(state.get("messages", []))
        messages = apply_prompt_template("coordinator", state, locale=state.get("locale", "en-US"))

        clarification_history = reconstruct_clarification_history(
            state_messages, clarification_history, initial_topic
        )
        clarified_topic, clarification_history = build_clarified_topic_from_history(
            clarification_history
        )
        logger.debug("Clarification history rebuilt: %s", clarification_history)

        if clarification_history:
            initial_topic = clarification_history[0]
            latest_user_content = clarification_history[-1]
        else:
            latest_user_content = ""

        # Add clarification status for first round
        if clarification_rounds == 0:
            messages.append(
                {
                    "role": "system",
                    "content": "Clarification mode is ENABLED. Follow the 'Clarification Process' guidelines in your instructions.",
                }
            )

        current_response = latest_user_content or "No response"
        logger.info(
            "Clarification round %s/%s | topic: %s | current user response: %s",
            clarification_rounds,
            max_clarification_rounds,
            clarified_topic or initial_topic,
            current_response,
        )

        clarification_context = f"""Continuing clarification (round {clarification_rounds}/{max_clarification_rounds}):
            User's latest response: {current_response}
            Ask for remaining missing dimensions. Do NOT repeat questions or start new topics."""

        messages.append({"role": "system", "content": clarification_context})

        # Bind all clarification and routing tools - let LLM choose the appropriate one
        tools = [handoff_to_planner, handoff_after_clarification, handoff_to_coder, handoff_to_code_planner]

        # Check if we've already reached max rounds
        if clarification_rounds >= max_clarification_rounds:
            # Max rounds reached - force handoff by adding system instruction
            logger.warning(
                f"Max clarification rounds ({max_clarification_rounds}) reached. Forcing handoff to planner. Using prepared clarified topic: {clarified_topic}"
            )
            # Add system instruction to force handoff - let LLM choose the right tool
            messages.append(
                {
                    "role": "system",
                    "content": f"MAX ROUNDS REACHED. You MUST call handoff_after_clarification (not handoff_to_planner) with the appropriate locale based on the user's language and research_topic='{clarified_topic}'. Do not ask any more questions.",
                }
            )

        response = (
            get_llm_by_type(AGENT_LLM_MAP["coordinator"])
            .bind_tools(tools)
            .invoke(messages)
        )
        logger.debug(f"Current state messages: {state['messages']}")

        # Initialize response processing variables
        goto = "__end__"
        locale = state.get("locale", "en-US")
        research_topic = (
            clarification_history[0]
            if clarification_history
            else state.get("research_topic", "")
        )
        if not clarified_topic:
            clarified_topic = research_topic

        # --- Process LLM response ---
        # No tool calls - LLM is asking a clarifying question
        if not response.tool_calls and response.content:
            # Strip think tags from coordinator response
            coordinator_content = strip_think_tags(response.content)
            
            # Check if we've reached max rounds - if so, force handoff to planner
            if clarification_rounds >= max_clarification_rounds:
                logger.warning(
                    f"Max clarification rounds ({max_clarification_rounds}) reached. "
                    "LLM didn't call handoff tool, forcing handoff to planner."
                )
                goto = "planner"
                # Continue to final section instead of early return
            else:
                # Continue clarification process
                clarification_rounds += 1
                # Do NOT add LLM response to clarification_history - only user responses
                logger.info(
                    f"Clarification response: {clarification_rounds}/{max_clarification_rounds}: {coordinator_content}"
                )

                # Append coordinator's question to messages
                updated_messages = list(state_messages)
                if coordinator_content:
                    updated_messages.append(
                        HumanMessage(content=coordinator_content, name="coordinator")
                    )

                return Command(
                    update={
                        "messages": updated_messages,
                        "locale": locale,
                        "research_topic": research_topic,
                        "resources": configurable.resources,
                        "clarification_rounds": clarification_rounds,
                        "clarification_history": clarification_history,
                        "clarified_research_topic": clarified_topic,
                        "is_clarification_complete": False,
                        "goto": goto,
                        "citations": state.get("citations", []),
                        "__interrupt__": [("coordinator", coordinator_content)],
                    },
                    goto=goto,
                )
        else:
            # LLM called a tool (handoff) or has no content - clarification complete
            if response.tool_calls:
                logger.info(
                    f"Clarification completed after {clarification_rounds} rounds. LLM called handoff tool."
                )
            else:
                logger.warning("LLM response has no content and no tool calls.")
            # goto will be set in the final section based on tool calls

    # ============================================================
    # Final: Build and return Command
    # ============================================================
    messages = list(state.get("messages", []) or [])
    if response.content:
        # Strip think tags from coordinator response before adding to messages
        coordinator_content = strip_think_tags(response.content)
        messages.append(HumanMessage(content=coordinator_content, name="coordinator"))
    
    # Add direct response message if it was set (for greetings/small talk)
    if direct_response_message:
        messages.append(direct_response_message)

    # Process tool calls for BOTH branches (legacy and clarification)
    if response.tool_calls:
        try:
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})

                if tool_name in ["handoff_to_planner", "handoff_after_clarification"]:
                    logger.info("Handing off to planner")
                    
                    # Check debate mode first - route directly to debate_planner
                    if state.get("enable_debate_mode", False):
                        logger.info("Debate mode enabled, routing to debate_planner")
                        goto = "debate_planner"
                    # Check AI comparison mode - route to planner (which routes to ai_comparison)
                    elif state.get("enable_ai_comparison", False):
                        logger.info("AI comparison mode enabled, planner will route to ai_comparison")
                        goto = "planner"
                    # Normal research mode
                    else:
                        goto = "planner"

                    if not enable_clarification and tool_args.get("research_topic"):
                        research_topic = tool_args["research_topic"]

                    if enable_clarification:
                        logger.info(
                            "Using prepared clarified topic: %s",
                            clarified_topic or research_topic,
                        )
                    else:
                        logger.info(
                            "Using research topic for handoff: %s", research_topic
                        )
                    break
                elif tool_name == "handoff_to_coder":
                    logger.info("Handing off to coder for code-related task")
                    
                    # Extract code task and clarity
                    code_task = tool_args.get("code_task", clarified_topic or research_topic)
                    clarity = tool_args.get("clarity", "clear")
                    
                    # Route based on clarity - NEW: Route directly to coder, not through planner
                    if clarity == "unclear":
                        logger.info("Code task is unclear, routing to human_feedback first")
                        goto = "human_feedback"
                    else:
                        logger.info("Code task is clear, routing directly to coder")
                        goto = "coder"
                    
                    # Mark research topic with [CODE] prefix to help coder detect direct call
                    research_topic = f"[CODE] {code_task}"
                    if enable_clarification:
                        clarified_topic = f"[CODE] {code_task}"
                    break
                elif tool_name == "handoff_to_code_planner":
                    logger.info("Handing off to code_planner for structured code development")
                    
                    # Extract code task
                    code_task = tool_args.get("code_task", clarified_topic or research_topic)
                    
                    # Route to code planner
                    logger.info("Code planner mode activated, routing to code_planner")
                    goto = "code_planner"
                    
                    # Set research topic for code planner
                    research_topic = code_task
                    if enable_clarification:
                        clarified_topic = code_task
                    break

        except Exception as e:
            logger.error(f"Error processing tool calls: {e}")
            goto = "planner"
    else:
        # No tool calls detected
        if enable_clarification:
            # BRANCH 2: Fallback to planner to ensure research proceeds
            logger.warning(
                "LLM didn't call any tools. This may indicate tool calling issues with the model. "
                "Falling back to planner to ensure research proceeds."
            )
            logger.debug(f"Coordinator response content: {response.content}")
            logger.debug(f"Coordinator response object: {response}")
            goto = "planner"
        else:
            # BRANCH 1: No tool calls means end workflow gracefully (e.g., greeting handled)
            logger.info("No tool calls in legacy mode - ending workflow gracefully")

    # Apply background_investigation routing if enabled (unified logic)
    # But skip if AI comparison or debate mode is enabled (they don't need background investigation)
    # Also skip if already routing to debate_planner
    if goto == "planner" and state.get("enable_background_investigation") and not state.get("enable_ai_comparison") and not state.get("enable_debate_mode"):
        goto = "background_investigator"

    # Set default values for state variables (in case they're not defined in legacy mode)
    if not enable_clarification:
        clarification_rounds = 0
        clarification_history = []

    clarified_research_topic_value = clarified_topic or research_topic

    # clarified_research_topic: Complete clarified topic with all clarification rounds
    return Command(
        update={
            "messages": messages,
            "locale": locale,
            "research_topic": research_topic,
            "clarified_research_topic": clarified_research_topic_value,
            "resources": configurable.resources,
            "clarification_rounds": clarification_rounds,
            "clarification_history": clarification_history,
            "is_clarification_complete": goto != "coordinator",
            "goto": goto,
            "citations": state.get("citations", []),
        },
        goto=goto,
    )


def reporter_node(state: State, config: RunnableConfig):
    """Reporter node that write a final report."""
    logger.info("Reporter write final report")
    configurable = Configuration.from_runnable_config(config)
    
    # Check if this is Debate mode (NEW)
    debate_results = state.get("debate_results")
    if debate_results:
        logger.info("Handling debate results in reporter node")
        final_report = debate_results.get("final_report", "Debate completed but no report generated.")
        
        # If the report seems short or missing, we might want to wrap it
        if len(final_report) < 100:
            final_report = f"# Debate Results\n\n{final_report}"
            
        return {
            "final_report": final_report,
            "citations": state.get("citations", []),
        }
    
    # Check if this is AI comparison mode
    comparison_results = state.get("comparison_results")
    if comparison_results:
        logger.info("Generating report for AI comparison results")
        
        # Format the comparison results as a report
        report_parts = ["# AI Model Comparison Results\n\n"]
        
        if comparison_results.get("status") == "failed":
            report_parts.append(f"**Error**: {comparison_results.get('error', 'Unknown error')}\n\n")
        else:
            # Add query
            report_parts.append(f"## Query\n{comparison_results.get('query', 'N/A')}\n\n")
            
            # Add model responses
            report_parts.append("## Model Responses\n\n")
            model_responses = comparison_results.get("model_responses", [])
            for response in model_responses:
                display_name = response.get("display_name", "Unknown Model")
                if response.get("success"):
                    report_parts.append(f"### {display_name}\n")
                    report_parts.append(f"{response.get('response', 'No response')}\n\n")
                else:
                    report_parts.append(f"### {display_name}\n")
                    report_parts.append(f"**Error**: {response.get('error', 'Unknown error')}\n\n")
            
            # Add synthesis
            synthesis = comparison_results.get("synthesis", {})
            if synthesis:
                report_parts.append("## Synthesized Optimal Answer\n\n")
                report_parts.append(f"{synthesis.get('synthesized_answer', 'N/A')}\n\n")
                
                # Add models used
                models_used = synthesis.get("models_used", [])
                if models_used:
                    report_parts.append(f"**Models Used**: {', '.join(models_used)}\n\n")
                
                # Add tools used
                tools_used = [t for t in synthesis.get("tools_used", []) if t]
                if tools_used:
                    report_parts.append(f"**Tools Used**: {', '.join(tools_used)}\n\n")
            
            # Add analysis
            analysis = comparison_results.get("analysis", {})
            if analysis:
                sources = analysis.get("sources", [])
                if sources:
                    report_parts.append(f"## Fact-Checking Sources\n\n")
                    report_parts.append(f"Found {len(sources)} sources for fact-checking.\n\n")
        
        final_report = "".join(report_parts)
        return {
            "final_report": final_report,
            "citations": state.get("citations", []),
        }
    
    # Normal reporting mode
    current_plan = state.get("current_plan")
    
    # Handle case where current_plan is None (e.g., if agent execution failed)
    if current_plan is None:
        logger.error("No current_plan found in state - cannot generate report")
        # Check if there are any observations to use
        observations = state.get("observations", [])
        if observations:
            error_report = "# Research Report\n\nAn error occurred during research execution, but some observations were collected:\n\n"
            for obs in observations:
                error_report += f"- {obs}\n\n"
            return {
                "final_report": error_report,
                "citations": state.get("citations", []),
            }
        else:
            return {
                "final_report": "# Research Report\n\nAn error occurred during research execution and no results were collected.",
                "citations": [],
            }
    
    # Handle case where current_plan is a string (raw JSON from planner)
    # This happens when planner routes to AI comparison or human_feedback
    if isinstance(current_plan, str):
        logger.info("current_plan is a string, parsing it as Plan object")
        try:
            # Try to parse the JSON string to extract plan information
            plan_dict = json.loads(repair_json_output(current_plan))
            plan_content = extract_plan_content(plan_dict)
            plan_dict = json.loads(repair_json_output(plan_content))
            current_plan = Plan.model_validate(plan_dict)
        except Exception as e:
            logger.error(f"Failed to parse current_plan string to Plan object: {e}")
            # Fall back to a generic task description
            plan_title = "AI Model Comparison Research"
            plan_thought = "Compare and analyze responses from multiple AI models"
            input_ = {
                "messages": [
                    HumanMessage(
                        f"# Research Requirements\n\n## Task\n\n{plan_title}\n\n## Description\n\n{plan_thought}"
                    )
                ],
                "locale": state.get("locale", "en-US"),
            }
            invoke_messages = apply_prompt_template("reporter", input_, configurable, input_.get("locale", "en-US"))
            observations = state.get("observations", [])
            
            # Get collected citations for the report
            citations = state.get("citations", [])
            
            # Continue with reporter execution using fallback values
            # (rest of the reporter logic will be executed below)
    
    if not isinstance(current_plan, str):  # Only set input_ if we have a proper Plan object
        input_ = {
            "messages": [
                HumanMessage(
                    f"# Research Requirements\n\n## Task\n\n{current_plan.title}\n\n## Description\n\n{current_plan.thought}"
                )
            ],
            "locale": state.get("locale", "en-US"),
        }
    invoke_messages = apply_prompt_template("reporter", input_, configurable, input_.get("locale", "en-US"))
    observations = state.get("observations", [])
    
    # Get collected citations for the report
    citations = state.get("citations", [])

    # If we have collected citations, provide them to the reporter
    if citations:
        citation_list = "\n\n## Available Source References (use these in References section):\n\n"
        for i, citation in enumerate(citations, 1):
            title = citation.get("title", "Untitled")
            url = citation.get("url", "")
            domain = citation.get("domain", "")
            description = citation.get("description", "")
            desc_truncated = description[:150] if description else ""
            citation_list += f"{i}. **{title}**\n   - URL: {url}\n   - Domain: {domain}\n"
            if desc_truncated:
                citation_list += f"   - Summary: {desc_truncated}...\n"
            citation_list += "\n"
        
        logger.info(f"Providing {len(citations)} collected citations to reporter")

        invoke_messages.append(
            HumanMessage(
                content=citation_list,
                name="system",
            )
        )

    observation_messages = []
    for observation in observations:
        observation_messages.append(
            HumanMessage(
                content=f"Below are some observations for the research task:\n\n{observation}",
                name="observation",
            )
        )

    # Context compression
    llm_token_limit = get_llm_token_limit_by_type(AGENT_LLM_MAP["reporter"])
    compressed_state = ContextManager(llm_token_limit).compress_messages(
        {"messages": observation_messages}
    )
    invoke_messages += compressed_state.get("messages", [])

    logger.debug(f"Current invoke messages: {invoke_messages}")
    response = get_llm_by_type(AGENT_LLM_MAP["reporter"]).invoke(invoke_messages)
    response_content = strip_think_tags(response.content)
    logger.info(f"reporter response: {response_content}")

    return {
        "final_report": response_content,
        "citations": citations,  # Pass citations through to final state
    }


def research_team_node(state: State):
    """Research team node that collaborates on tasks."""
    logger.info("Research team is collaborating on tasks.")
    logger.debug("Entering research_team_node - coordinating research and coder agents")
    pass


def validate_web_search_usage(messages: list, agent_name: str = "agent") -> bool:
    """
    Validate if the agent has used the web search tool during execution.
    
    Args:
        messages: List of messages from the agent execution
        agent_name: Name of the agent (for logging purposes)
        
    Returns:
        bool: True if web search tool was used, False otherwise
    """
    web_search_used = False
    
    for message in messages:
        # Check for ToolMessage instances indicating web search was used
        if isinstance(message, ToolMessage) and message.name == "web_search":
            web_search_used = True
            logger.info(f"[VALIDATION] {agent_name} received ToolMessage from web_search tool")
            break
            
        # Check for AIMessage content that mentions tool calls
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.get('name') == "web_search":
                    web_search_used = True
                    logger.info(f"[VALIDATION] {agent_name} called web_search tool")
                    break
            # break outer loop if web search was used
            if web_search_used:
                break
                    
        # Check for message name attribute
        if hasattr(message, 'name') and message.name == "web_search":
            web_search_used = True
            logger.info(f"[VALIDATION] {agent_name} used web_search tool")
            break
    
    if not web_search_used:
        logger.warning(f"[VALIDATION] {agent_name} did not use web_search tool")
        
    return web_search_used


async def _execute_agent_step(
    state: State, agent, agent_name: str, config: RunnableConfig = None
) -> Command[Literal["research_team"]]:
    """Helper function to execute a step using the specified agent."""
    logger.debug(f"[_execute_agent_step] Starting execution for agent: {agent_name}")
    
    current_plan = state.get("current_plan")
    
    # Handle case where current_plan is a string (from planner in AI comparison mode)
    if isinstance(current_plan, str):
        logger.info(f"[_execute_agent_step] current_plan is string, parsing to Plan object")
        try:
            from backend.deer_flow.utils.json_utils import repair_json_output
            from backend.deer_flow.prompts.planner_model import Plan
            
            plan_dict = json.loads(repair_json_output(current_plan))
            plan_content = extract_plan_content(plan_dict)
            plan_dict = json.loads(repair_json_output(plan_content))
            current_plan = Plan.model_validate(plan_dict)
            logger.info(f"[_execute_agent_step] Successfully parsed string to Plan object")
        except Exception as e:
            logger.error(f"[_execute_agent_step] Failed to parse current_plan string: {e}")
            # Return to research_team if parsing fails
            return Command(
                update=preserve_state_meta_fields(state),
                goto="research_team"
            )
    
    # Handle case where current_plan is None (direct call from coordinator for code questions)
    if current_plan is None:
        logger.info(f"[_execute_agent_step] current_plan is None, creating synthetic plan for direct {agent_name} call")
        from backend.deer_flow.prompts.planner_model import Plan, Step, StepType
        
        # Get research topic from state (should have [CODE] prefix for direct code calls)
        research_topic = state.get("research_topic", "Code Task")
        
        # Remove [CODE] prefix if present
        if research_topic.startswith("[CODE]"):
            research_topic = research_topic[6:].strip()
        
        # Create a simple synthetic plan with one step
        step_type = StepType.PROCESSING if agent_name == "coder" else StepType.RESEARCH
        current_plan = Plan(
            locale=state.get("locale", "en-US"),
            has_enough_context=False,
            thought=f"Direct {agent_name} execution for: {research_topic}",
            title=research_topic,
            steps=[
                Step(
                    need_search=False,
                    step_type=step_type,
                    title=research_topic,
                    description=f"Execute {agent_name} task: {research_topic}",
                    execution_res=None
                )
            ]
        )
        logger.info(f"[_execute_agent_step] Created synthetic plan for direct call: {current_plan.title}")
    
    plan_title = current_plan.title
    observations = state.get("observations", [])
    logger.debug(f"[_execute_agent_step] Plan title: {plan_title}, observations count: {len(observations)}")

    # Find the first unexecuted step
    current_step = None
    completed_steps = []
    for idx, step in enumerate(current_plan.steps):
        if not step.execution_res:
            current_step = step
            logger.debug(f"[_execute_agent_step] Found unexecuted step at index {idx}: {step.title}")
            break
        else:
            completed_steps.append(step)

    if not current_step:
        logger.warning(f"[_execute_agent_step] No unexecuted step found in {len(current_plan.steps)} total steps")
        return Command(
            update=preserve_state_meta_fields(state),
            goto="research_team"
        )

    logger.info(f"[_execute_agent_step] Executing step: {current_step.title}, agent: {agent_name}")
    logger.debug(f"[_execute_agent_step] Completed steps so far: {len(completed_steps)}")

    # Format completed steps information
    completed_steps_info = ""
    if completed_steps:
        completed_steps_info = "# Completed Research Steps\n\n"
        for i, step in enumerate(completed_steps):
            completed_steps_info += f"## Completed Step {i + 1}: {step.title}\n\n"
            completed_steps_info += f"<finding>\n{step.execution_res}\n</finding>\n\n"

    # Prepare the input for the agent with completed steps info
    agent_input = {
        "messages": [
            HumanMessage(
                content=f"# Research Topic\n\n{plan_title}\n\n{completed_steps_info}# Current Step\n\n## Title\n\n{current_step.title}\n\n## Description\n\n{current_step.description}\n\n## Locale\n\n{state.get('locale', 'en-US')}"
            )
        ]
    }

    # Add citation reminder for researcher agent
    if agent_name == "researcher":
        if state.get("resources"):
            resources_info = "**The user mentioned the following resource files:**\n\n"
            for resource in state.get("resources"):
                resources_info += f"- {resource.title} ({resource.description})\n"

            agent_input["messages"].append(
                HumanMessage(
                    content=resources_info
                    + "\n\n"
                    + "You MUST use the **local_search_tool** to retrieve the information from the resource files.",
                )
            )

        agent_input["messages"].append(
            HumanMessage(
                content="IMPORTANT: DO NOT include inline citations in the text. Instead, track all sources and include a References section at the end using link reference format. Include an empty line between each citation for better readability. Use this format for each reference:\n- [Source Title](URL)\n\n- [Another Source](URL)",
                name="system",
            )
        )

    # Invoke the agent
    default_recursion_limit = 100
    try:
        env_value_str = os.getenv("AGENT_RECURSION_LIMIT", str(default_recursion_limit))
        parsed_limit = int(env_value_str)

        if parsed_limit > 0:
            recursion_limit = parsed_limit
            logger.info(f"Recursion limit set to: {recursion_limit}")
        else:
            logger.warning(
                f"AGENT_RECURSION_LIMIT value '{env_value_str}' (parsed as {parsed_limit}) is not positive. "
                f"Using default value {default_recursion_limit}."
            )
            recursion_limit = default_recursion_limit
    except ValueError:
        raw_env_value = os.getenv("AGENT_RECURSION_LIMIT")
        logger.warning(
            f"Invalid AGENT_RECURSION_LIMIT value: '{raw_env_value}'. "
            f"Using default value {default_recursion_limit}."
        )
        recursion_limit = default_recursion_limit

    logger.info(f"Agent input: {agent_input}")
    
    # Validate message content before invoking agent
    try:
        validated_messages = validate_message_content(agent_input["messages"])
        agent_input["messages"] = validated_messages
    except Exception as validation_error:
        logger.error(f"Error validating agent input messages: {validation_error}")
    
    # Apply context compression to prevent token overflow (Issue #721)
    llm_token_limit = get_llm_token_limit_by_type(AGENT_LLM_MAP[agent_name])
    if llm_token_limit:
        token_count_before = sum(
            len(str(msg.content).split()) for msg in agent_input.get("messages", []) if hasattr(msg, "content")
        )
        compressed_state = ContextManager(llm_token_limit, preserve_prefix_message_count=3).compress_messages(
            {"messages": agent_input["messages"]}
        )
        agent_input["messages"] = compressed_state.get("messages", [])
        token_count_after = sum(
            len(str(msg.content).split()) for msg in agent_input.get("messages", []) if hasattr(msg, "content")
        )
        logger.info(
            f"Context compression for {agent_name}: {len(compressed_state.get('messages', []))} messages, "
            f"estimated tokens before: ~{token_count_before}, after: ~{token_count_after}"
        )
    
    try:
        result = await agent.ainvoke(
            input=agent_input, config={"recursion_limit": recursion_limit}
        )
    except Exception as e:
        import traceback

        error_traceback = traceback.format_exc()
        error_message = f"Error executing {agent_name} agent for step '{current_step.title}': {str(e)}"
        logger.exception(error_message)
        logger.error(f"Full traceback:\n{error_traceback}")
        
        # Enhanced error diagnostics for content-related errors
        if "Field required" in str(e) and "content" in str(e):
            logger.error(f"Message content validation error detected")
            for i, msg in enumerate(agent_input.get('messages', [])):
                logger.error(f"Message {i}: type={type(msg).__name__}, "
                            f"has_content={hasattr(msg, 'content')}, "
                            f"content_type={type(msg.content).__name__ if hasattr(msg, 'content') else 'N/A'}, "
                            f"content_len={len(str(msg.content)) if hasattr(msg, 'content') and msg.content else 0}")

        detailed_error = f"[ERROR] {agent_name.capitalize()} Agent Error\n\nStep: {current_step.title}\n\nError Details:\n{str(e)}\n\nPlease check the logs for more information."
        current_step.execution_res = detailed_error

        return Command(
            update={
                "messages": [
                    HumanMessage(
                        content=detailed_error,
                        name=agent_name,
                    )
                ],
                "observations": observations + [detailed_error],
                **preserve_state_meta_fields(state),
            },
            goto="research_team",
        )

    # Process the result
    response_content = result["messages"][-1].content
    
    # Strip think tags if present
    response_content = strip_think_tags(response_content)
    
    # Sanitize response to remove extra tokens and truncate if needed
    response_content = sanitize_tool_response(str(response_content))
    
    logger.debug(f"{agent_name.capitalize()} full response: {response_content}")

    # Validate web search usage for researcher agent if enforcement is enabled
    web_search_validated = True
    should_validate = agent_name == "researcher"
    validation_info = ""

    if should_validate:
        # Check if enforcement is enabled in configuration
        configurable = Configuration.from_runnable_config(config) if config else Configuration()
        # Skip validation if web search is disabled (user intentionally disabled it)
        if configurable.enforce_researcher_search and configurable.enable_web_search:
            web_search_validated = validate_web_search_usage(result["messages"], agent_name)
            
            # If web search was not used, add a warning to the response
            if not web_search_validated:
                logger.warning(f"[VALIDATION] Researcher did not use web_search tool. Adding reminder to response.")
                # Add validation information to observations
                validation_info = (
                    "\n\n[WARNING] This research was completed without using the web_search tool. "
                    "Please verify that the information provided is accurate and up-to-date."
                    "\n\n[VALIDATION WARNING] Researcher did not use the web_search tool as recommended."
                )

    # Update the step with the execution result
    current_step.execution_res = response_content
    logger.info(f"Step '{current_step.title}' execution completed by {agent_name}")

    # Include all messages from agent result to preserve intermediate tool calls/results
    # This ensures multiple web_search calls all appear in the stream, not just the final result
    agent_messages = result.get("messages", [])
    logger.debug(
        f"{agent_name.capitalize()} returned {len(agent_messages)} messages. "
        f"Message types: {[type(msg).__name__ for msg in agent_messages]}"
    )
    
    # Count tool messages for logging
    tool_message_count = sum(1 for msg in agent_messages if isinstance(msg, ToolMessage))
    if tool_message_count > 0:
        logger.info(
            f"{agent_name.capitalize()} agent made {tool_message_count} tool calls. "
            f"All tool results will be preserved and streamed to frontend."
        )
    
    # For direct agent calls (especially coder), ensure there's a meaningful final message
    # If the last AIMessage has empty/minimal content, create a summary message
    logger.info(f"[{agent_name}] Checking if message enhancement needed: agent_messages={len(agent_messages) if agent_messages else 0}, current_plan={'exists' if current_plan else 'None'}, steps={len(current_plan.steps) if current_plan else 'N/A'}")
    if agent_messages and current_plan and len(current_plan.steps) == 1 and tool_message_count > 0:  # Synthetic plan (direct call) with tools
        last_msg = agent_messages[-1]
        logger.info(f"[{agent_name}] Last message type: {type(last_msg).__name__}, isinstance(AIMessage)={isinstance(last_msg, AIMessage)}")
        
        if isinstance(last_msg, AIMessage):
            content_to_check = str(last_msg.content).strip()
            logger.info(f"[{agent_name}] Last message content length: {len(content_to_check)}, tool_message_count: {tool_message_count}")
            
            # For direct coder calls with tools, ALWAYS enhance the message to ensure visibility
            # This fixes the issue where frontend receives messages but doesn't render them
            logger.info(f"[{agent_name}] Direct call with tools detected - enhancing message for frontend visibility")
            
            # Build summary from tool messages
            tool_summaries = []
            for msg in agent_messages:
                if isinstance(msg, ToolMessage):
                    tool_name = getattr(msg, 'name', 'unknown_tool')
                    tool_content = str(msg.content)[:200]  # First 200 chars
                    tool_summaries.append(f"**{tool_name}**: {tool_content}")
            
            # Always include tool results, even if there was some content
            if tool_summaries:
                if content_to_check and len(content_to_check) > 10:
                    # There's already meaningful content, just append tool results
                    summary_content = f"{content_to_check}\n\n## Tool Results\n\n" + "\n\n".join(tool_summaries)
                else:
                    # Little/no content, use response_content (task description) + tool results
                    summary_content = f"{response_content}\n\n## Tool Results\n\n" + "\n\n".join(tool_summaries)
                
                logger.info(f"[{agent_name}] Created enhanced content with {len(tool_summaries)} tool results, total length: {len(summary_content)}")
                
                # Create a new AIMessage with the summary
                enhanced_message = AIMessage(
                    content=summary_content,
                    name=agent_name,
                    id=last_msg.id
                )
                
                # Replace the last message with the enhanced one
                agent_messages[-1] = enhanced_message
                logger.info(f"[{agent_name}] Enhanced final message with tool results summary")
                logger.info(f"[{agent_name}] FINAL ENHANCED MESSAGE CONTENT: {summary_content[:500]}...")  # Log first 500 chars
            else:
                logger.warning(f"[{agent_name}] No tool summaries found despite tool_message_count > 0")

    # Extract citations from tool call results (web_search, crawl)
    existing_citations = state.get("citations", [])
    new_citations = extract_citations_from_messages(agent_messages)
    merged_citations = merge_citations(existing_citations, new_citations)
    
    if new_citations:
        logger.info(
            f"Extracted {len(new_citations)} new citations from {agent_name} agent. "
            f"Total citations: {len(merged_citations)}"
        )

    return Command(
        update={
            **preserve_state_meta_fields(state),
            "messages": agent_messages,
            "observations": observations + [response_content + validation_info],
            "citations": merged_citations,  # Store merged citations based on existing state and new tool results
        },
        goto="research_team",
    )


async def _setup_and_execute_agent_step(
    state: State,
    config: RunnableConfig,
    agent_type: str,
    default_tools: list,
) -> Command[Literal["research_team"]]:
    """Helper function to set up an agent with appropriate tools and execute a step.

    This function handles the common logic for both researcher_node and coder_node:
    1. Configures MCP servers and tools based on agent type
    2. Creates an agent with the appropriate tools or uses the default agent
    3. Executes the agent on the current step

    Args:
        state: The current state
        config: The runnable config
        agent_type: The type of agent ("researcher" or "coder")
        default_tools: The default tools to add to the agent

    Returns:
        Command to update state and go to research_team
    """
    configurable = Configuration.from_runnable_config(config)
    mcp_servers = {}
    enabled_tools = {}
    loaded_tools = default_tools[:]
    
    # Get locale from workflow state to pass to agent creation
    # This fixes issue #743 where locale was not correctly retrieved in agent prompt
    locale = state.get("locale", "en-US")

    # Extract MCP server configuration for this agent type
    if configurable.mcp_settings:
        for server_name, server_config in configurable.mcp_settings["servers"].items():
            if (
                server_config["enabled_tools"]
                and agent_type in server_config["add_to_agents"]
            ):
                mcp_servers[server_name] = {
                    k: v
                    for k, v in server_config.items()
                    if k in ("transport", "command", "args", "url", "env", "headers")
                }
                for tool_name in server_config["enabled_tools"]:
                    enabled_tools[tool_name] = server_name

    # Create and execute agent with MCP tools if available
    if mcp_servers:
        # Add MCP tools to loaded tools if MCP servers are configured
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
            client = MultiServerMCPClient(mcp_servers)
            all_tools = await client.get_tools()
            for tool in all_tools:
                if tool.name in enabled_tools:
                    tool.description = (
                        f"Powered by '{enabled_tools[tool.name]}'.\n{tool.description}"
                    )
                    loaded_tools.append(tool)
        except ImportError:
            logger.warning("MCP servers configured but langchain_mcp_adapters not installed. Install with: pip install langchain-mcp-adapters")

    llm_token_limit = get_llm_token_limit_by_type(AGENT_LLM_MAP[agent_type])
    pre_model_hook = partial(ContextManager(llm_token_limit, 3).compress_messages)
    agent = create_agent(
        agent_type,
        agent_type,
        loaded_tools,
        agent_type,
        pre_model_hook,
        interrupt_before_tools=configurable.interrupt_before_tools,
        locale=locale,
    )
    return await _execute_agent_step(state, agent, agent_type, config)


async def researcher_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Researcher node that do research or execute debate"""
    logger.info("Researcher node is researching.")
    logger.debug(f"[researcher_node] Starting researcher agent")
    
    configurable = Configuration.from_runnable_config(config)
    logger.debug(f"[researcher_node] Max search results: {configurable.max_search_results}")
    
    # Check if we're in debate mode
    enable_debate_mode = state.get("enable_debate_mode", False)
    
    # Build tools list based on configuration
    tools = []
    
    if enable_debate_mode:
        # In debate mode, use debate tools instead of research tools
        logger.info("[researcher_node] Debate mode enabled - adding debate tools")
        debate_tools = get_debate_tools()
        tools.extend(debate_tools)
        logger.info(f"[researcher_node] Debate tools count: {len(tools)}")
        logger.debug(f"[researcher_node] Debate tools: {[tool.name if hasattr(tool, 'name') else str(tool) for tool in tools]}")
    else:
        # Normal research mode
        # Add web search and crawl tools only if web search is enabled
        if configurable.enable_web_search:
            tools.extend([get_web_search_tool(configurable.max_search_results), crawl_tool])
        else:
            logger.info("[researcher_node] Web search is disabled, using only local RAG")
        
        # Add retriever tool if resources are available (always add, higher priority)
        retriever_tool = get_retriever_tool(state.get("resources", []))
        if retriever_tool:
            logger.debug(f"[researcher_node] Adding retriever tool to tools list")
            tools.insert(0, retriever_tool)
        
        # Warn if no tools are available
        if not tools:
            logger.warning("[researcher_node] No tools available (web search disabled, no resources). "
                           "Researcher will operate in pure reasoning mode.")
        
        logger.info(f"[researcher_node] Researcher tools count: {len(tools)}")
        logger.debug(f"[researcher_node] Researcher tools: {[tool.name if hasattr(tool, 'name') else str(tool) for tool in tools]}")
        logger.info(f"[researcher_node] enforce_researcher_search={configurable.enforce_researcher_search}, "
                    f"enable_web_search={configurable.enable_web_search}")
    
    return await _setup_and_execute_agent_step(
        state,
        config,
        "researcher",
        tools,
    )


async def coder_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team", "human_feedback", "__end__"]]:
    """Coder node that handles code analysis and execution with extended tools.
    
    Can be called in three ways:
    1. Directly from coordinator for simple code questions -> responds directly (goto __end__)
    2. From research_team as part of a plan -> routes to human_feedback to ask about testing
    3. Legacy: Can still return to research_team if needed
    """
    logger.info("Coder node is coding.")
    logger.debug(f"[coder_node] Starting coder agent with extended code tools")
    
    # Import code tools
    from backend.deer_flow.tools.code_tools import get_code_tools
    
    # Build tool list: always include python_repl_tool, plus any enabled code tools
    tools = [python_repl_tool]
    code_tools = get_code_tools()
    tools.extend(code_tools)
    
    logger.info(f"Coder node using {len(tools)} tools: {[t.name for t in tools]}")
    
    # Check if this is a direct call from coordinator (code-specific question)
    # vs being called as part of research_team workflow
    current_plan = state.get("current_plan")
    research_topic = state.get("research_topic", "")
    
    logger.info(f"[coder_node] Routing decision: current_plan={'exists' if current_plan else 'None'}, research_topic='{research_topic}'")
    
    called_directly = current_plan is None or (
        isinstance(research_topic, str) and 
        research_topic.startswith("[CODE]")
    )
    
    logger.info(f"[coder_node] called_directly={called_directly}, will route to {'__end__' if called_directly else 'human_feedback'}")
    
    result = await _setup_and_execute_agent_step(
        state,
        config,
        "coder",
        tools,
    )
    
    # If called directly from coordinator, respond directly to user
    if called_directly:
        logger.info("Coder was called directly from coordinator, responding to user (__end__)")
        # Log the messages being sent to verify content
        messages_to_send = result.update.get("messages", [])
        if messages_to_send:
            last_msg_content = messages_to_send[-1].content if hasattr(messages_to_send[-1], 'content') else "NO CONTENT ATTR"
            logger.info(f"[coder_node] Sending {len(messages_to_send)} messages to frontend, last message content length: {len(last_msg_content) if isinstance(last_msg_content, str) else 0}")
            logger.info(f"[coder_node] Last message content preview: {str(last_msg_content)[:200]}...")
        return Command(
            update=result.update,
            goto="__end__"
        )
    
    # When called from research_team, route to human_feedback to ask about testing
    logger.info("Coder completed, routing to human_feedback to ask about testing")
    # Set flag to indicate coder just completed (for human_feedback_node to know what to ask)
    # Create new update dict to ensure the flag is properly set
    updated_state = {
        **result.update,
        "coder_just_completed": True
    }
    logger.info(f"[coder_node] Setting coder_just_completed=True in update dict")
    return Command(
        update=updated_state,
        goto="human_feedback"
    )


async def tester_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Tester node that handles automated testing, linting, and code quality validation.
    
    This node executes test suites, runs linters, performs type checking, and validates
    code quality standards. It uses specialized test tools for Python and JavaScript/TypeScript.
    """
    logger.info("Tester node is testing code.")
    logger.debug(f"[tester_node] Starting tester agent with test tools")
    
    # Import test tools
    from backend.deer_flow.tools.test_tools import get_test_tools
    
    # Build tool list: test tools + file system tool for reading test files + python_repl for debugging
    tools = [python_repl_tool]
    test_tools = get_test_tools()
    tools.extend(test_tools)
    
    # Add file_system_tool if available for reading test files (optional)
    from backend.deer_flow.tools.code_tools import file_system_tool
    try:
        # File system tool is optional for tester but helpful for reading test files
        tools.append(file_system_tool)
        logger.debug("Added file_system_tool to tester tools")
    except Exception as e:
        logger.debug(f"File system tool not available (optional): {e}")
    
    logger.info(f"Tester node using {len(tools)} tools: {[t.name for t in tools]}")
    
    # Execute tester agent
    return await _setup_and_execute_agent_step(
        state,
        config,
        "tester",
        tools,
    )


async def analyst_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Analyst node that performs reasoning and analysis without code execution.
    
    This node handles tasks like:
    - Cross-validating information from multiple sources
    - Synthesizing research findings
    - Comparative analysis
    - Pattern recognition and trend analysis
    - General reasoning tasks that don't require code
    """
    logger.info("Analyst node is analyzing.")
    logger.debug(f"[analyst_node] Starting analyst agent for reasoning/analysis tasks")
    
    # Analyst uses no tools - pure LLM reasoning
    return await _setup_and_execute_agent_step(
        state,
        config,
        "analyst",
        [],  # No tools - pure reasoning
    )


async def ai_comparison_node(
    state: State, config: RunnableConfig
) -> Command[Literal["reporter"]]:
    """
    AI Comparison node that runs sequential queries across multiple AI models.
    Implements Debate OS functionality for DeerFlow with real-time streaming.
    
    Executes AI comparison agent with tools, then goes directly to reporter.
    Does NOT use research_team routing to avoid loops.
    """
    # CRITICAL: Do NOT run ai_comparison when debate_mode is enabled
    # Debate uses completely separate chain with debate_tools
    if state.get("enable_debate_mode", False):
        logger.warning("AI Comparison node called with debate_mode=True - this should NOT happen! Skipping ai_comparison.")
        return Command(
            update=preserve_state_meta_fields(state),
            goto="reporter"
        )
    
    logger.info("AI Comparison node starting - Debate OS mode")
    
    configurable = Configuration.from_runnable_config(config)
    
    # Get AI comparison tools
    tools = get_ai_comparison_tools()
    logger.info(f"AI comparison tools count: {len(tools)}")
    
    # Get locale and research topic from state
    locale = state.get("locale", "en-US")
    research_topic = state.get("research_topic", "Unknown topic")
    logger.info(f"Research topic: {research_topic}")
    
    # Create a simple plan with one step for AI comparison
    # This allows us to use _setup_and_execute_agent_step() which we KNOW works for streaming
    from backend.deer_flow.prompts.planner_model import Plan, Step, StepType
    
    comparison_step = Step(
        need_search=False,  # AI comparison doesn't need web search, it queries AI models
        step_type=StepType.RESEARCH,
        title="AI Model Comparison",
        description=f"""Query and compare responses from multiple AI models for: {research_topic}

Follow these steps:
1. Query each AI model individually (call tools one at a time for streaming):
   - query_gpt35
   - query_gemini_flash
   - query_deepseek  
   - query_grok4
   - query_oneseek_local

2. Fact-check responses using fact_check_responses tool

3. Run meta-analysis using run_meta_analysis tool

4. Synthesize optimal answer using synthesize_optimal_answer tool

Provide a comprehensive comparison report with citations.""",
        execution_res=None
    )
    
    comparison_plan = Plan(
        locale=state.get("locale", "en-US"),  # Get locale from state, default to en-US
        has_enough_context=False,  # We need to execute this comparison step
        thought="Running AI comparison across multiple models to provide comprehensive analysis.",
        title=research_topic,
        steps=[comparison_step]
    )
    
    # Update state directly with the comparison plan
    # State is a dict-like object, so we can mutate it
    state["current_plan"] = comparison_plan
    state["locale"] = locale
    state["research_topic"] = research_topic
    
    logger.info("Created comparison plan with 1 step, using standard execution path")
    
    # Set a higher recursion limit for AI comparison since it needs to call 8+ tools sequentially
    # Each tool call counts as ~2-3 recursion steps, so 8 tools = ~24 steps minimum
    # We set to 50 to give plenty of buffer
    import os
    original_recursion_limit = os.getenv("AGENT_RECURSION_LIMIT")
    os.environ["AGENT_RECURSION_LIMIT"] = "50"
    
    try:
        # Planner node already created the planner message before routing to ai_comparison
        # So we don't need to create it again here - it already exists in state["messages"]
        logger.info("Planner already created planner message, executing AI comparison step")
        
        # Use the EXACT SAME execution path as researcher/coder
        # This is what makes streaming work correctly!
        result = await _setup_and_execute_agent_step(
            state,
            config,
            "ai_comparison",
            tools,
        )
        
        # Mark the comparison step as complete to prevent research_team from routing to researcher
        comparison_step.execution_res = "AI comparison completed successfully"
        
        # Go directly to reporter instead of research_team to avoid researcher loops
        # The ai_comparison agent has already executed all tools (query models, fact_check, meta_analysis, synthesize)
        logger.info("AI comparison complete, routing directly to reporter")
        
        # Return updated state with completed step and goto reporter
        return Command(
            update={
                **result.update,
                "current_plan": comparison_plan,  # Update with completed step
            },
            goto="reporter",
        )
    finally:
        # Restore original recursion limit
        if original_recursion_limit is not None:
            os.environ["AGENT_RECURSION_LIMIT"] = original_recursion_limit
        elif "AGENT_RECURSION_LIMIT" in os.environ:
            del os.environ["AGENT_RECURSION_LIMIT"]


async def debate_node(
    state: State, config: RunnableConfig
) -> Command[Literal["reporter"]]:
    """
    Multi-Round Debate node that orchestrates a 3-round debate between AI models.
    
    All models (including OneSeek) participate as equal debaters with:
    - Randomized order each round
    - Sequential chain-of-thought flow
    - Strict context control between rounds
    - OneSeek synthesis in round 3
    - External model voting after round 3
    
    Routes directly to reporter to avoid research_team loops.
    """
    logger.info("Debate node starting - Multi-Round Debate Engine")
    
    configurable = Configuration.from_runnable_config(config)
    
    # Get debate tools
    from backend.deer_flow.tools import get_debate_tools
    tools = get_debate_tools()
    logger.info(f"Debate tools count: {len(tools)}")
    
    # Get locale and research topic from state
    locale = state.get("locale", "en-US")
    research_topic = state.get("research_topic", "Unknown topic")
    logger.info(f"Research topic: {research_topic}")
    logger.info(f"Locale: {locale}")
    
    # Create a simple plan with one step for the debate
    # This allows us to use _setup_and_execute_agent_step() which works for streaming
    from backend.deer_flow.prompts.planner_model import Plan, Step, StepType
    
    debate_step = Step(
        need_search=False,  # Debate uses internal web search via tools
        step_type=StepType.RESEARCH,
        title="Multi-Round Debate",
        description=f"""Orchestrate a 3-round debate for: {research_topic}

Follow the debate protocol:

**Round 1:**
1. start_debate_round(1, "{research_topic}", "{locale}")
2. Query each model ONE AT A TIME in randomized order using query_model_in_round
3. Use debater_web_search if needed to verify facts

**Round 2:**
1. start_debate_round(2, "{research_topic}", "{locale}")
2. Query each model ONE AT A TIME in randomized order using query_model_in_round
3. Use debater_web_search if needed

**Round 3:**
1. start_debate_round(3, "{research_topic}", "{locale}")
2. Query each model ONE AT A TIME in randomized order using query_model_in_round
3. OneSeek creates synthesis when it's OneSeek's turn
4. Use debater_web_search if needed

**Voting:**
1. collect_debate_votes("{research_topic}")

**Summary:**
1. get_debate_summary()

Provide a comprehensive debate report with all rounds, voting results, and conclusions.""",
        execution_res=None
    )
    
    debate_plan = Plan(
        locale=state.get("locale", "en-US"),
        has_enough_context=False,  # We need to execute this debate step
        thought="Running multi-round debate with all AI models to provide comprehensive, debated analysis.",
        title=research_topic,
        steps=[debate_step]
    )
    
    # Update state with debate plan
    # Ensure debate_results is cleared from previous runs
    state["current_plan"] = debate_plan
    state["locale"] = locale
    state["research_topic"] = research_topic
    if "debate_results" in state:
        del state["debate_results"]
    
    logger.info("Created debate plan with 1 step, using standard execution path")
    
    # Set a higher recursion limit for debate since it needs many sequential tool calls
    # 3 rounds × ~5 models × 2 tools per model = ~30 calls minimum
    # Plus voting and summary = ~35 calls
    # We set to 100 to give plenty of buffer
    import os
    original_recursion_limit = os.getenv("AGENT_RECURSION_LIMIT")
    os.environ["AGENT_RECURSION_LIMIT"] = "100"
    
    try:
        logger.info("Executing debate step via standard agent execution path")
        
        # Use the EXACT SAME execution path as ai_comparison and researcher
        result = await _setup_and_execute_agent_step(
            state,
            config,
            "debate",
            tools,
        )
        
        # Mark the debate step as complete
        debate_step.execution_res = "Multi-round debate completed successfully"
        
        # Go directly to reporter to avoid research_team loops
        logger.info("Debate complete, routing directly to reporter")
        
        # Extract the final debate report from the messages
        # The debate agent's last message should be the final report/summary
        debate_report = None
        if result.update.get("messages"):
            last_message = result.update["messages"][-1]
            if isinstance(last_message, AIMessage) and last_message.content:
                debate_report = last_message.content
                logger.info("Extracted debate report from final message")
        
        # If no report found in messages, try to get it from observations (tool outputs)
        if not debate_report:
            observations = result.update.get("observations", [])
            if observations:
                # The last observation might be the get_debate_summary output
                debate_report = observations[-1]
                logger.info("Using last observation as debate report")
        
        # Return updated state with completed step and goto reporter
        # We pass debate_results to trigger special handling in reporter_node
        return Command(
            update={
                **result.update,
                "current_plan": debate_plan,
                "debate_results": {
                    "final_report": debate_report,
                    "status": "completed"
                }
            },
            goto="reporter",
        )
    finally:
        # Restore original recursion limit
        if original_recursion_limit is not None:
            os.environ["AGENT_RECURSION_LIMIT"] = original_recursion_limit
        elif "AGENT_RECURSION_LIMIT" in os.environ:
            del os.environ["AGENT_RECURSION_LIMIT"]

# ============================================================
# NEW SEPARATE DEBATE CHAIN NODES
# ============================================================

async def debate_orchestrator_node(
    state: State, config: RunnableConfig
) -> Command[Literal["external_ai_caller", "reporter"]]:
    """
    Debate orchestrator node - manages rounds, scores, and exit criteria.
    
    This is the conductor that:
    1. Tracks current round number
    2. Routes to external_ai_caller to get real AI model responses
    3. Collects scores from moderator after each round
    4. Determines when to exit (rounds complete, knockout, significant score lead)
    5. Routes to reporter when debate is complete
    
    NEW FLOW: orchestrator → external_ai_caller → fact_checker → synthesizer → moderator → orchestrator
    """
    logger.info("Debate orchestrator starting")
    configurable = Configuration.from_runnable_config(config)
    
    # Get debate state
    current_round = state.get("debate_round", 0)
    max_rounds = state.get("debate_max_rounds", 3)
    scores = state.get("debate_scores", {"external_ai": 0, "consensus": 0})  # Simplified scoring
    knockout = state.get("debate_knockout", False)
    logger.info(f"Orchestrator: Read debate_round={current_round} from state (before increment)")
    
    # 🚨 CIRCUIT BREAKER: Track consecutive errors to prevent GPU burn
    error_count = state.get("debate_error_count", 0)
    MAX_CONSECUTIVE_ERRORS = 3
    
    # Check recent messages (not just last one!) for error indicators
    messages = state.get("messages", [])
    if messages and len(messages) > 0:
        # Check last 10 messages for errors from any debate node
        recent_messages = messages[-10:] if len(messages) >= 10 else messages
        # More precise error indicators - avoid false positives
        error_indicators = ["Error querying", "ERROR:", "error:", "AttributeError", "Exception:", "Traceback"]
        
        # Check if there are errors in recent messages
        error_in_recent = False
        error_node = None
        for msg in reversed(recent_messages):
            if hasattr(msg, 'name') and msg.name in ["external_ai_caller", "moderator", "fact_checker", "synthesizer"]:
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                # Only detect actual errors, not JSON fields like '"error": false'
                if any(indicator in content for indicator in error_indicators):
                    error_in_recent = True
                    error_node = msg.name
                    break
        
        if error_in_recent:
            error_count += 1
            logger.error(f"🚨 CIRCUIT BREAKER: Error detected in {error_node} (count: {error_count}/{MAX_CONSECUTIVE_ERRORS})")
            
            if error_count >= MAX_CONSECUTIVE_ERRORS:
                logger.error(f"🚨 CIRCUIT BREAKER TRIGGERED: {error_count} consecutive errors - ABORTING DEBATE TO PREVENT GPU BURN")
                error_msg = AIMessage(
                    content=json.dumps({
                        "error": "Circuit breaker triggered",
                        "reason": f"Debatten avbröts automatiskt efter {error_count} sammanhängande fel",
                        "final_round": current_round,
                        "exit_reason": "🚨 SÄKERHETSBRYTARE AKTIVERAD - För många fel, avbryter för att förhindra GPU-bränning",
                        "node_with_error": error_node
                    }, ensure_ascii=False, indent=2),
                    name="debate_orchestrator"
                )
                return Command(
                    update={
                        **preserve_state_meta_fields(state),
                        "messages": [error_msg],
                        "debate_complete": True,
                        "debate_error_count": error_count,
                    },
                    goto="reporter"
                )
        else:
            # No errors in recent messages - reset counter
            if error_count > 0:
                logger.info(f"✅ Circuit breaker reset - no errors in recent messages (was at {error_count})")
                error_count = 0
    
    # Increment round
    current_round += 1
    logger.info(f"Orchestrator: Incremented to debate_round={current_round}")
    logger.info(f"Starting debate round {current_round}/{max_rounds}")
    
    # Check exit criteria before starting new round
    if current_round > max_rounds:
        logger.info(f"Max rounds reached: {max_rounds}")
        exit_reason = f"{max_rounds} rundor uppnått"
        summary_msg = AIMessage(
            content=json.dumps({
                "final_round": current_round - 1,
                "final_scores": scores,
                "exit_reason": exit_reason,
                "external_ai_models": ["Grok", "Gemini", "ChatGPT", "DeepSeek"]
            }, ensure_ascii=False, indent=2),
            name="debate_orchestrator"
        )
        
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "messages": [summary_msg],
                "debate_complete": True,
                "debate_error_count": 0,  # Reset on successful completion
            },
            goto="reporter"
        )
    elif knockout:
        logger.info("Knockout detected in previous round")
        exit_reason = "Knockout-argument identifierat"
        summary_msg = AIMessage(
            content=json.dumps({
                "final_round": current_round - 1,
                "final_scores": scores,
                "exit_reason": exit_reason,
                "external_ai_models": ["Grok", "Gemini", "ChatGPT", "DeepSeek"]
            }, ensure_ascii=False, indent=2),
            name="debate_orchestrator"
        )
        
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "messages": [summary_msg],
                "debate_complete": True,
                "debate_error_count": 0,  # Reset on successful completion
            },
            goto="reporter"
        )
    
    # Create debate_flow instance if this is round 1 (and it doesn't exist)
    if current_round == 1 and "debate_flow" not in state:
        from backend.debate_flow import get_debate_flow
        debate_flow = get_debate_flow(
            max_search_results=configurable.max_search_results,
            resources=state.get("resources", [])
        )
        logger.info("Created debate_flow instance for round 1")
    else:
        debate_flow = state.get("debate_flow")
    
    # Start new round - route to external_ai_caller to get real AI responses
    logger.info(f"Round {current_round}: Routing to external_ai_caller for real AI model responses")
    
    # Build state update explicitly to debug
    preserved_fields = preserve_state_meta_fields(state)
    logger.info(f"Orchestrator: preserved_fields has debate_round={preserved_fields.get('debate_round')}")
    logger.info(f"Orchestrator: Setting debate_round={current_round} in state update (should override preserved value)")
    
    state_update = {
        **preserved_fields,
        "debate_round": current_round,
        "debate_flow": debate_flow,  # ADD debate_flow to state!
        "debate_error_count": error_count,  # Track errors for circuit breaker
    }
    logger.info(f"Orchestrator: Final state_update has debate_round={state_update.get('debate_round')}")
    
    return Command(
        update=state_update,
        goto="external_ai_caller"  # Calls Grok, Gemini, ChatGPT, DeepSeek
    )


async def debate_team_node(state: State, config: RunnableConfig):
    """
    Debate team sub-graph that runs the specialized debate nodes in sequence:
    proponent → opponent → fact_checker → synthesizer → moderator
    
    Each node has its own dedicated prompt and role in the debate.
    """
    logger.info("Debate team starting for round %s", state.get("debate_round", 1))
    
    # This is a placeholder that will be replaced by the sub-graph
    # The actual execution happens through the sub-graph edges
    pass


async def external_ai_caller_node(
    state: State, config: RunnableConfig
) -> Command[Literal["fact_checker"]]:
    """
    External AI Caller node - orchestrates sequential debate rounds DETERMINISTICALLY.
    
    NO LONGER uses an LLM agent (which was unreliable and caused infinite loops).
    Instead, directly calls debate_flow methods in a predictable order:
    1. Start the debate round
    2. Query each model exactly once
    3. Return
    
    This ensures each model is called EXACTLY once per round, no more, no less.
    """
    logger.info("External AI Caller - orchestrating debate round (DETERMINISTIC)")
    configurable = Configuration.from_runnable_config(config)
    
    # Always recreate debate_flow instance (don't rely on state persistence)
    # LangGraph doesn't properly pass complex Python objects through state
    from backend.debate_flow import get_debate_flow
    debate_flow = get_debate_flow(
        max_search_results=configurable.max_search_results,
        resources=state.get("resources", [])
    )
    logger.info("Created debate_flow instance in external_ai_caller")
    
    # Get current round number from state (1-based: 1, 2, 3)
    round_num = state.get("debate_round", 1)
    logger.info(f"Starting deterministic execution for Round {round_num}")
    
    # DETERMINISTIC EXECUTION - no LLM making decisions!
    try:
        # Create tool calls list to show progress in frontend
        tool_calls = []
        import uuid
        
        # Step 1: Start the debate round
        # Emit tool call for starting round
        start_round_id = f"call_{uuid.uuid4().hex[:24]}"
        tool_calls.append({
            "id": start_round_id,
            "name": "start_debate_round",
            "args": {"round_number": round_num}
        })
        
        logger.info(f"Step 1: Starting debate round {round_num}")
        debate_flow.start_new_round(round_num)
        logger.info(f"Round {round_num} started")
        
        # Step 2: Query each model EXACTLY once
        all_models = list(debate_flow.models.keys())
        logger.info(f"Step 2: Querying {len(all_models)} models sequentially")
        
        responses = []
        for i, model_key in enumerate(all_models, 1):
            # Emit tool call for querying model
            query_model_id = f"call_{uuid.uuid4().hex[:24]}"
            tool_calls.append({
                "id": query_model_id,
                "name": "query_model_in_debate",
                "args": {
                    "model_key": model_key,
                    "round_number": round_num,
                    "model_index": f"{i}/{len(all_models)}"
                }
            })
            
            logger.info(f"  Querying model {i}/{len(all_models)}: {model_key}")
            # Build context and query model
            user_query = state.get("user_query", "")
            # Get locale from state (NOT round number!)
            locale = state.get("locale", "sv-SE")
            # Query model with correct locale parameter
            response = await debate_flow.query_model_in_debate(model_key, user_query, locale)
            
            # Extract only the actual response text, not the full metadata
            if isinstance(response, dict):
                response_text = response.get('response', str(response))
            else:
                response_text = str(response)
            
            responses.append(f"Model {model_key}: {response_text}")
            logger.info(f"  ✓ Model {model_key} responded ({len(response_text)} chars)")
        
        # Step 3: Done! Combine all responses
        combined_response = "\n\n".join(responses)
        logger.info(f"Step 3: Round {round_num} complete - all {len(all_models)} models queried")
        
        # Create AIMessage with tool_calls to show progress in frontend
        response_message = AIMessage(
            content=combined_response,
            name="external_ai_caller",
            tool_calls=tool_calls,  # Show tool calls in frontend
            additional_kwargs={
                "round": round_num,
                "models_queried": len(all_models),
                "agent": "external_ai_caller"
            }
        )
        
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "messages": [response_message],
                "external_ai_responses": combined_response,
            },
            goto="fact_checker"
        )
        
    except Exception as e:
        logger.error(f"Error in deterministic external_ai_caller: {e}", exc_info=True)
        error_message = AIMessage(
            content=f"Error in debate round: {str(e)}",
            name="external_ai_caller"
        )
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "messages": [error_message],
                "external_ai_responses": "",
            },
            goto="fact_checker"
        )


async def fact_checker_node(
    state: State, config: RunnableConfig
) -> Command[Literal["synthesizer"]]:
    """Fact checker node - verifies claims from external AI models."""
    logger.info("Fact checker verifying external AI claims")
    configurable = Configuration.from_runnable_config(config)
    locale = state.get("locale", "en-US")
    
    # Get web search and other tools for verification
    tools = [get_web_search_tool(configurable.max_search_results), crawl_tool]
    
    # Build prompt for fact_checker
    messages = apply_prompt_template("fact_checker", state, configurable, locale)
    
    # Create agent for fact_checker
    llm_token_limit = get_llm_token_limit_by_type(AGENT_LLM_MAP["fact_checker"])
    pre_model_hook = partial(ContextManager(llm_token_limit, 3).compress_messages)
    agent = create_agent(
        "fact_checker",
        "fact_checker",
        tools,
        "fact_checker",
        pre_model_hook,
        interrupt_before_tools=configurable.interrupt_before_tools,
        locale=locale,
    )
    
    # Execute agent
    result = await agent.ainvoke(state, config)
    
    # Extract response - agent returns dict with "messages" key
    response_content = ""
    if result and "messages" in result and len(result["messages"]) > 0:
        last_msg = result["messages"][-1]
        if hasattr(last_msg, 'content'):
            response_content = last_msg.content
    
    logger.info(f"Fact checker response length: {len(response_content)}")
    
    return Command(
        update={
            **preserve_state_meta_fields(state),
            "messages": result.get("messages", []),
            "fact_checker_response": response_content,
        },
        goto="synthesizer"  # Route to synthesizer to integrate external AI perspectives
    )


async def synthesizer_node(
    state: State, config: RunnableConfig
) -> Command[Literal["moderator"]]:
    """Synthesizer node - creates superior synthesis from both sides."""
    logger.info("Synthesizer creating integrated position")
    configurable = Configuration.from_runnable_config(config)
    locale = state.get("locale", "en-US")
    
    # Get web search and other tools for additional context
    tools = [get_web_search_tool(configurable.max_search_results), crawl_tool]
    
    # Build prompt for synthesizer
    messages = apply_prompt_template("synthesizer", state, configurable, locale)
    
    # Create agent for synthesizer
    llm_token_limit = get_llm_token_limit_by_type(AGENT_LLM_MAP["synthesizer"])
    pre_model_hook = partial(ContextManager(llm_token_limit, 3).compress_messages)
    agent = create_agent(
        "synthesizer",
        "synthesizer",
        tools,
        "synthesizer",
        pre_model_hook,
        interrupt_before_tools=configurable.interrupt_before_tools,
        locale=locale,
    )
    
    # Execute agent
    result = await agent.ainvoke(state, config)
    
    # Extract response - agent returns dict with "messages" key
    response_content = ""
    if result and "messages" in result and len(result["messages"]) > 0:
        last_msg = result["messages"][-1]
        if hasattr(last_msg, 'content'):
            response_content = last_msg.content
    
    logger.info(f"Synthesizer response length: {len(response_content)}")
    
    return Command(
        update={
            **preserve_state_meta_fields(state),
            "messages": result.get("messages", []),
            "synthesizer_response": response_content,
        },
        goto="moderator"
    )


async def moderator_node(
    state: State, config: RunnableConfig
) -> Command[Literal["debate_orchestrator"]]:
    """
    Moderator node - summarizes round, gives scores, determines winner.
    
    This node:
    1. Summarizes the round
    2. Gives scores (0-3) to proponent and opponent
    3. Determines round winner
    4. Checks for knockout arguments
    5. Updates debate scores in state
    6. Routes back to debate_orchestrator
    """
    logger.info("Moderator evaluating round")
    configurable = Configuration.from_runnable_config(config)
    locale = state.get("locale", "en-US")
    
    # Get debate state
    current_round = state.get("debate_round", 1)
    scores = state.get("debate_scores", {"proponent": 0, "opponent": 0})
    logger.info(f"Moderator: Read debate_round={current_round} from state")
    
    # Build prompt for moderator
    messages = apply_prompt_template("moderator", state, configurable, locale)
    
    # Add context about current scores AND EXPLICIT JSON REQUEST
    messages.append({
        "role": "system",
        "content": f"""Detta är runda {current_round}. Nuvarande poängställning: Proponent {scores['proponent']} - Opponent {scores['opponent']}

**KRITISKT VIKTIGT**: Du MÅSTE svara ENDAST med giltig JSON i detta exakta format (inga extra ord eller text):

{{
  "proponent_score": 0-3,
  "opponent_score": 0-3,
  "winner": "proponent/opponent/tie",
  "summary": "kort sammanfattning av rundan",
  "knockout": false
}}

Svara INTE med vanlig text eller markdown. Endast ren JSON!"""
    })
    
    # Get LLM
    llm = get_llm_by_type(AGENT_LLM_MAP["moderator"])
    llm = configure_llm_with_thinking(llm, enable_thinking=False)
    
    # Invoke LLM
    response = await llm.ainvoke(messages)
    response_content = get_message_content(response) or ""
    
    # Parse moderator response (expecting JSON)
    try:
        # Strip think tags and markdown fences
        cleaned_response = strip_think_tags(response_content, expect_json=True)
        if cleaned_response.startswith("```"):
            lines = cleaned_response.split('\n')
            if len(lines) > 0:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned_response = '\n'.join(lines).strip()
        
        moderator_result = json.loads(cleaned_response)
        
        # Update scores
        round_proponent_score = moderator_result.get("proponent_score", 0)
        round_opponent_score = moderator_result.get("opponent_score", 0)
        
        scores["proponent"] += round_proponent_score
        scores["opponent"] += round_opponent_score
        
        knockout = moderator_result.get("knockout", False)
        
        logger.info(f"Round {current_round} scores: Proponent +{round_proponent_score}, Opponent +{round_opponent_score}")
        logger.info(f"Total scores: Proponent {scores['proponent']}, Opponent {scores['opponent']}")
        logger.info(f"Knockout: {knockout}")
        logger.info(f"Moderator: Setting debate_round={current_round} in state update")
        
        # Create summary message
        summary_msg = AIMessage(
            content=json.dumps(moderator_result, ensure_ascii=False, indent=2),
            name="moderator"
        )
        
        # Build state update - explicitly set all debate fields
        state_update = {
            "messages": [summary_msg],
            "debate_scores": scores,
            "debate_knockout": knockout,
            "debate_round": current_round,  # CRITICAL: Preserve round number!
        }
        # Add meta fields but let debate fields from above take precedence
        for key, value in preserve_state_meta_fields(state).items():
            if key not in state_update:
                state_update[key] = value
        
        logger.info(f"Moderator: State update keys: {list(state_update.keys())}, debate_round in update: {state_update.get('debate_round')}")
        
        return Command(
            update=state_update,
            goto="debate_orchestrator"  # Route back for next round
        )
        
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse moderator response: {e}")
        logger.error(f"Response content: {response_content[:500]}")
        
        # Fallback: simple scores
        summary_msg = AIMessage(
            content=f"Runda {current_round}: Kunde inte bedöma ordentligt.",
            name="moderator"
        )
        
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "messages": [summary_msg],
                "debate_scores": scores,
                "debate_knockout": False,
                "debate_round": current_round,  # CRITICAL: Preserve round number even on error!
            },
            goto="debate_orchestrator"  # Route back for next round
        )
