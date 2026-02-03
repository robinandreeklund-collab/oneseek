# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import json
import logging
import os
import re
from uuid import uuid4
from functools import partial
from typing import Annotated, Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
# MCP adapters import moved to conditional block where it's used
# from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import END
from langgraph.types import Command, interrupt

from backend.deer_flow.agents import create_agent
from backend.deer_flow.citations import extract_citations_from_messages, merge_citations
from backend.deer_flow.config.agents import AGENT_LLM_MAP
from backend.deer_flow.config.loader import get_bool_env
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
from backend.deer_flow.tools.ai_comparison_tools import (
    fact_check_responses,
    query_all_models,
    query_deepseek,
    query_gemini_flash,
    query_gpt35,
    query_grok4,
    query_oneseek_local,
    run_meta_analysis,
    set_ai_comparison_context,
    synthesize_optimal_answer,
)
from backend.deer_flow.tools.debate_tools import get_debate_tools
from backend.deer_flow.tools.search import LoggedTavilySearch
from backend.deer_flow.utils.context_manager import ContextManager, validate_message_content
from backend.deer_flow.utils.json_utils import repair_json_output, sanitize_tool_response
from backend.deer_flow.utils.llm_output_parser import parse_llm_output

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


def strip_markdown_code_fences(content: str) -> str:
    """
    Strip markdown code fences and return the fenced content if present.
    """
    if not content:
        return content
    match = re.search(r"```(?:json)?\s*(.*?)```", content, re.S | re.I)
    if match:
        return match.group(1).strip()
    stripped = content.strip()
    if not stripped.startswith("```"):
        return content
    lines = stripped.split("\n")
    if lines:
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_json_substring(content: str) -> str | None:
    """
    Extract JSON substring starting from the first '{' or '['.
    """
    if not content:
        return None
    start_positions = [pos for pos in (content.find("{"), content.find("[")) if pos != -1]
    if not start_positions:
        return None
    start = min(start_positions)
    return content[start:].strip()


def strip_think_tags(content: str, expect_json: bool = False) -> str:
    """
    Strip <think> tags or [thinking] markers from content, handling different placements.
    
    This function handles multiple cases:
    1. Standard case: Content after </think> tag (e.g., "<think>...</think>actual content")
    2. Edge case: Content inside <think> tags (e.g., "<think>actual content</think>")
    3. Edge case: Content before <think> tag (e.g., "actual content<think>...</think>")
    4. No tags: Returns content as-is
    5. Only tags with no content: Returns empty string
    6. [thinking] markers: prefer content after the last marker
    
    For JSON responses (when expect_json=True), it tries content after </think> first,
    then falls back to content inside tags if the after-content is empty or invalid JSON.
    For non-JSON responses, it tries content after, before, then inside tags.
    
    Args:
        content: The content potentially containing <think> tags
        expect_json: If True, applies JSON-specific logic for fallback
        
    Returns:
        Content with <think> tags stripped appropriately
    """
    if not content:
        return content

    if re.search(r"\[(think|thinking)\]", content, re.I):
        segments = [segment.strip() for segment in re.split(r"\[(think|thinking)\]", content, flags=re.I)]
        segments = [segment for segment in segments if segment and segment.lower() not in ("think", "thinking")]
        segments = [segment for segment in segments if segment]
        if not segments:
            return ""
        if expect_json:
            for segment in reversed(segments):
                candidate = strip_markdown_code_fences(segment)
                if is_json_like(candidate):
                    return candidate
            return segments[-1]
        return segments[-1]

    if '<think>' not in content or '</think>' not in content:
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
        for segment in (content_after, content_inside, content_before):
            candidate = strip_markdown_code_fences(segment)
            if candidate and is_json_like(candidate):
                return candidate
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


def _parse_json_content(content: str) -> dict[str, Any]:
    """Parse JSON content from a message string."""
    if not content:
        return {}
    content = content.strip()
    if content.startswith("```"):
        match = re.search(r"```json\s*(.*?)```", content, re.S | re.I)
        if match:
            content = match.group(1).strip()
        else:
            # Fallback to any fenced block
            match = re.search(r"```(.*?)```", content, re.S)
            if match:
                content = match.group(1).strip()
    try:
        return json.loads(repair_json_output(content))
    except Exception:
        return {}


def normalize_json_response(content: str) -> str:
    """
    Normalize a model response that should contain JSON.
    """
    if not content:
        return content
    cleaned = strip_think_tags(content, expect_json=True)
    if not cleaned:
        cleaned = content
    cleaned = strip_markdown_code_fences(cleaned)
    if is_json_like(cleaned):
        return cleaned
    extracted = _extract_json_substring(cleaned)
    if extracted and is_json_like(extracted):
        return extracted
    extracted = _extract_json_substring(content)
    if extracted and is_json_like(extracted):
        return extracted
    return cleaned


def apply_llm_output_parsing(response: AIMessage) -> AIMessage:
    if not response or not hasattr(response, "content"):
        return response
    content = response.content if isinstance(response.content, str) else str(response.content)
    parsed = parse_llm_output(content)
    if parsed.reasoning_content and not response.additional_kwargs.get("reasoning_content"):
        response.additional_kwargs["reasoning_content"] = parsed.reasoning_content
    if parsed.tool_calls and not response.tool_calls:
        response.tool_calls = parsed.tool_calls
    if parsed.content != content:
        response.content = parsed.content
    return response


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
    
    Debate state fields ARE included to ensure they persist across node transitions.
    Orchestrator can explicitly override these values when needed.
    
    Args:
        state: Current state object
        
    Returns:
        Dict of meta fields to preserve
    """
    return {
        "locale": state.get("locale", "en-US"),
        "research_topic": state.get("research_topic", ""),
        "clarified_research_topic": state.get("clarified_research_topic", ""),
        "plan_source": state.get("plan_source", "planner"),
        "enable_code_mode": state.get("enable_code_mode", False),
        "code_report_complete": state.get("code_report_complete", False),
        "enable_ai_comparison": state.get("enable_ai_comparison", False),
        "ai_compare_responses": state.get("ai_compare_responses", []),
        "ai_compare_responses_json": state.get("ai_compare_responses_json"),
        "ai_compare_fact_check": state.get("ai_compare_fact_check"),
        "ai_compare_fact_check_json": state.get("ai_compare_fact_check_json"),
        "ai_compare_meta": state.get("ai_compare_meta"),
        "ai_compare_meta_json": state.get("ai_compare_meta_json"),
        "ai_compare_synthesis": state.get("ai_compare_synthesis"),
        "ai_compare_synthesis_json": state.get("ai_compare_synthesis_json"),
        "ai_compare_report_complete": state.get("ai_compare_report_complete", False),
        "ai_compare_pending_tool": state.get("ai_compare_pending_tool"),
        "clarification_history": state.get("clarification_history", []),
        "enable_clarification": state.get("enable_clarification", False),
        "max_clarification_rounds": state.get("max_clarification_rounds", 3),
        "clarification_rounds": state.get("clarification_rounds", 0),
        "resources": state.get("resources", []),
        # Debate state fields - preserve across transitions so orchestrator can read them
        "debate_round": state.get("debate_round", 0),
        "debate_scores": state.get("debate_scores", {"proponent": 0, "opponent": 0}),
        "debate_knockout": state.get("debate_knockout", False),
        "debate_max_rounds": state.get("debate_max_rounds", 3),
        "debate_error_count": state.get("debate_error_count", 0),
        "debate_complete": state.get("debate_complete", False),
        "debate_model_index": state.get("debate_model_index", 0),
        "debate_model_order": state.get("debate_model_order", []),
        "debate_round_started": state.get("debate_round_started", False),
        "external_ai_responses": state.get("external_ai_responses", ""),
        "debate_pending_model": state.get("debate_pending_model"),
        "debate_model_ids": state.get("debate_model_ids", []),
    }


def get_team_route(state: State) -> str:
    """Return the appropriate team router for the current plan."""
    plan_source = state.get("plan_source")
    if plan_source == "code_planner":
        return "code_team"
    if plan_source == "ai_comparison":
        return "ai_compare_team"
    return "research_team"


def get_thread_id_from_config(config: RunnableConfig | None) -> str:
    """Extract thread_id from runnable config."""
    if not config:
        return "default"
    if isinstance(config, dict) and config.get("thread_id"):
        return str(config["thread_id"])
    configurable = config.get("configurable") if isinstance(config, dict) else None
    if isinstance(configurable, dict) and configurable.get("thread_id"):
        return str(configurable["thread_id"])
    return "default"


def parse_debate_model_selection(feedback: str) -> list[str]:
    """Extract selected debate model IDs from interrupt feedback."""
    if not feedback:
        return []
    try:
        match = re.search(r"models=([^\]]+)", feedback, re.IGNORECASE)
        if not match:
            return []
        raw = match.group(1)
        return [model.strip() for model in raw.split(",") if model.strip()]
    except Exception:
        return []


def build_rounds_preview(rounds: list[dict], max_chars: int = 400) -> list[dict]:
    """Trim debate round data for UI display."""
    preview: list[dict] = []
    for round_data in rounds:
        responses_preview = []
        for resp in round_data.get("responses", []):
            if resp.get("error"):
                continue
            response_text = resp.get("response", "")
            if isinstance(response_text, str) and len(response_text) > max_chars:
                response_text = response_text[:max_chars] + "... [trunkerat]"
            responses_preview.append({
                "model": resp.get("model"),
                "display_name": resp.get("display_name"),
                "response": response_text,
            })
        preview.append({
            "round": round_data.get("round"),
            "responses": responses_preview,
        })
    return preview


def extract_claim_sentences(text: str, max_claims: int = 8) -> list[str]:
    """Extract claim-like sentences for controlled fact checking."""
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    claims = []
    for sentence in sentences:
        cleaned = sentence.strip()
        if len(cleaned) < 20:
            continue
        if any(token in cleaned.lower() for token in ["%", "år", "year", "miljoner", "million", "billion", "studie", "rapport", "enligt", "according", "fakta", "data"]) or re.search(r"\d", cleaned):
            claims.append(cleaned)
        if len(claims) >= max_claims:
            break
    return claims


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

    # Normalize response to JSON-only content (handles think tags/markers and code fences)
    original_response = full_response
    full_response = normalize_json_response(full_response)
    if full_response != original_response:
        logger.debug(f"Normalized planner response to JSON: {full_response[:100]}...")

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
                "plan_source": "planner",
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
                "plan_source": "planner",
                **preserve_state_meta_fields(state),
            },
            goto="ai_comparison",
        )
    
    return Command(
        update={
            "messages": [AIMessage(content=full_response, name="planner")],
            "current_plan": full_response,
            "plan_source": "planner",
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
    
    # Normalize response to JSON-only content (handles think tags/markers and code fences)
    original_response = full_response
    full_response = normalize_json_response(full_response)
    if full_response != original_response:
        logger.debug("Normalized debate planner response to JSON")
    
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
        # Enforce code planner rule: never use research steps
        steps = curr_plan.get("steps", [])
        for step in steps:
            if not isinstance(step, dict):
                continue
            if step.get("step_type") == "research" or step.get("need_search"):
                step["step_type"] = "processing"
                step["need_search"] = False
                step["description"] = (
                    "Include any necessary documentation lookup as part of implementation. "
                    + (step.get("description") or "")
                ).strip()
        curr_plan["steps"] = steps
    
    # Check if plan has enough context (matching planner_node)
    if isinstance(curr_plan, dict) and curr_plan.get("has_enough_context"):
        logger.info("Debate planner response has enough context.")
        new_plan = Plan.model_validate(curr_plan)
        return Command(
            update={
                "messages": [AIMessage(content=json.dumps(curr_plan, ensure_ascii=False, indent=2), name="planner")],
                "current_plan": new_plan,
                "plan_source": "code_planner",
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
            "plan_source": "code_planner",
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
    
    # Normalize response to JSON-only content (handles think tags/markers and code fences)
    original_response = full_response
    full_response = normalize_json_response(full_response)
    if full_response != original_response:
        logger.debug("Normalized code planner response to JSON")
    
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
                "plan_source": "debate_planner",
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
            "plan_source": "debate_planner",
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
) -> Command[
    Literal[
        "planner",
        "research_team",
        "code_team",
        "ai_compare_team",
        "reporter",
        "debate_orchestrator",
        "__end__",
    ]
]:
    if state.get("final_report") and state.get("plan_source") == "code_planner":
        logger.info("[human_feedback_node] Code plan complete, routing to END")
        return Command(
            update=preserve_state_meta_fields(state),
            goto=END,
        )
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
            prompt = "[CODE_TEST_PROMPT|sv-SE]\nKodningen är klar! Vill du att jag testar koden?\n\nSvara '[TEST]' för att köra tester (pytest, pylint, mypy), eller '[SKIP]' för att hoppa över testning."
        else:
            prompt = "[CODE_TEST_PROMPT|en-US]\nCoding is complete! Would you like me to test the code?\n\nReply '[TEST]' to run tests (pytest, pylint, mypy), or '[SKIP]' to skip testing."
        
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
            logger.info("User requested testing. Creating TESTING step and routing to team.")
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
                    goto=get_team_route(state),
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
    selected_models: list[str] = state.get("debate_model_ids", [])
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
        feedback_raw = str(feedback).strip()
        feedback_normalized = feedback_raw.upper()
        selected_models = parse_debate_model_selection(feedback_raw)

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
        elif feedback_normalized.startswith("[ACCEPTED") or feedback_normalized.startswith("ACCEPTED"):
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
        # Normal mode - route to appropriate team
        goto = get_team_route(state)
        logger.info(f"[human_feedback_node] Plan approved, routing to {goto}")
    
    try:
        # Safely extract plan content from different types (string, AIMessage, dict, Plan)
        original_plan = current_plan

        if isinstance(current_plan, Plan):
            new_plan = current_plan.model_dump()
        else:
            # Repair the JSON output
            current_plan = repair_json_output(current_plan)
            # parse the plan to dict
            current_plan = json.loads(current_plan)
            current_plan_content = extract_plan_content(current_plan)
            # parse the plan
            new_plan = json.loads(repair_json_output(current_plan_content))
        
        # increment the plan iterations
        plan_iterations += 1
        # Validate and fix plan to ensure web search requirements are met
        configurable = Configuration.from_runnable_config(config)
        enforce_web_search = configurable.enforce_web_search
        if state.get("plan_source") in ("code_planner", "ai_comparison"):
            enforce_web_search = False
        new_plan = validate_and_fix_plan(new_plan, enforce_web_search, configurable.enable_web_search)
        if state.get("plan_source") == "code_planner":
            steps = new_plan.get("steps", [])
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if step.get("step_type") == "research" or step.get("need_search"):
                    step["step_type"] = "processing"
                    step["need_search"] = False
                    step["description"] = (
                        "Include any necessary documentation lookup as part of implementation. "
                        + (step.get("description") or "")
                    ).strip()
            new_plan["steps"] = steps
        
        if selected_models:
            from backend.debate_flow import DEBATE_MODELS
            model_names = [
                DEBATE_MODELS.get(model_id, {}).get("display_name", model_id)
                for model_id in selected_models
            ]
            locale = state.get("locale", "en-US")
            if locale.startswith("sv"):
                selection_note = f"Valda modeller: {', '.join(model_names)}"
            else:
                selection_note = f"Selected models: {', '.join(model_names)}"
            new_plan["thought"] = f"{new_plan.get('thought', '')} ({selection_note})"
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
            "debate_scores": {"proponent": 0, "opponent": 0},
            "debate_knockout": False,
            "debate_model_ids": selected_models or state.get("debate_model_ids", []),
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

    if state.get("enable_code_mode"):
        logger.info("[coordinator_node] Code mode enabled, routing to code_planner")
        return Command(
            update={
                "research_topic": state.get("research_topic", ""),
                **preserve_state_meta_fields(state),
            },
            goto="code_planner",
        )

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
        response = apply_llm_output_parsing(response)

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
                            logger.info("AI comparison mode enabled, routing to ai_comparison planner")
                            goto = "ai_comparison"
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
        response = apply_llm_output_parsing(response)
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
    if response.content and not response.tool_calls:
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
                        logger.info("AI comparison mode enabled, routing to ai_comparison planner")
                        goto = "ai_comparison"
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


def _format_debate_results_for_report(debate_results: dict) -> str:
    """Create a compact debate context for the reporter model."""
    def truncate(text: str, max_chars: int = 900) -> str:
        if not text:
            return ""
        text = text.strip()
        if len(text) > max_chars:
            return text[:max_chars] + "... [trunkerat]"
        return text

    user_query = debate_results.get("user_query", "")
    rounds = debate_results.get("rounds", [])
    vote_results = debate_results.get("vote_results")
    internal_fact_checks = debate_results.get("internal_fact_checks", [])
    internal_summaries = debate_results.get("internal_summaries", [])

    parts = [
        "Denna debattprocess är intern för OneSeek och ska inte delas externt.",
        f"Fråga: {user_query}",
    ]

    for round_data in rounds:
        round_number = round_data.get("round")
        parts.append(f"\n## Runda {round_number}")
        for resp in round_data.get("responses", []):
            display = resp.get("display_name") or resp.get("model", "Modell")
            response_text = truncate(resp.get("response", ""))
            parts.append(f"- **{display}**: {response_text}")

    if internal_fact_checks:
        parts.append("\n## Interna faktakontroller (kumulativa)")
        for entry in internal_fact_checks:
            round_number = entry.get("round")
            parts.append(f"- Runda {round_number}: {truncate(entry.get('content', ''), 700)}")

    if internal_summaries:
        parts.append("\n## Interna synteser (kumulativa)")
        for entry in internal_summaries:
            round_number = entry.get("round")
            parts.append(f"- Runda {round_number}: {truncate(entry.get('content', ''), 700)}")

    if vote_results:
        parts.append("\n## Röstningsresultat (alla modeller, självröstning ej tillåten)")
        parts.append(f"Vinnare: {vote_results.get('winner')}")
        parts.append(f"Röster: {vote_results.get('votes')}")
        details = vote_results.get("vote_details", [])
        if details:
            parts.append("Detaljer:")
            for detail in details:
                voter = detail.get("voter", "okänd")
                vote = detail.get("vote", "okänd")
                parts.append(f"- {voter} → {vote}")
                reasons = detail.get("reasons") or []
                for reason in reasons[:3]:
                    parts.append(f"  - {reason}")

    return "\n".join(parts)


def reporter_node(state: State, config: RunnableConfig):
    """Reporter node that write a final report."""
    logger.info("Reporter write final report")
    configurable = Configuration.from_runnable_config(config)
    
    # Check if this is Debate mode (NEW)
    debate_results = state.get("debate_results")
    if debate_results:
        logger.info("Handling debate results in reporter node")
        final_report = debate_results.get("final_report")
        if not final_report or len(final_report) < 100:
            locale = state.get("locale", "sv-SE")
            debate_context = _format_debate_results_for_report(debate_results)
            input_ = {
                "messages": [HumanMessage(content=debate_context)],
                "locale": locale,
            }
            invoke_messages = apply_prompt_template("debate_reporter", input_, configurable, locale)
            response = get_llm_by_type(AGENT_LLM_MAP["reporter"]).invoke(invoke_messages)
            final_report = strip_think_tags(response.content)
        
        # Ensure a title is present
        if len(final_report) < 100:
            final_report = f"# Debattresultat\n\n{final_report}"
        
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


def code_team_node(state: State):
    """Code team node that orchestrates code-only tasks."""
    logger.info("Code team is collaborating on code tasks.")
    logger.debug("Entering code_team_node - coordinating code-only agents")
    pass


def ai_compare_team_node(state: State):
    """AI comparison team node that orchestrates comparison tasks."""
    logger.info("AI comparison team is collaborating on comparison tasks.")
    logger.debug("Entering ai_compare_team_node - coordinating ai comparison agents")
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
) -> Command[Literal["research_team", "code_team", "ai_compare_team"]]:
    """Helper function to execute a step using the specified agent."""
    logger.debug(f"[_execute_agent_step] Starting execution for agent: {agent_name}")
    team_goto = get_team_route(state)
    
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
                goto=team_goto
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
            goto=team_goto
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
            goto=team_goto,
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
        goto=team_goto,
    )


async def _setup_and_execute_agent_step(
    state: State,
    config: RunnableConfig,
    agent_type: str,
    default_tools: list,
) -> Command[Literal["research_team", "code_team", "ai_compare_team"]]:
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
        Command to update state and go to the appropriate team router
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


async def code_researcher_node(
    state: State, config: RunnableConfig
) -> Command[Literal["code_team"]]:
    """Code researcher node that gathers code/documentation references."""
    logger.info("Code researcher node is researching code references.")
    logger.debug("[code_researcher_node] Starting code researcher agent")

    configurable = Configuration.from_runnable_config(config)

    tools = []
    if configurable.enable_web_search:
        tools.extend([get_web_search_tool(configurable.max_search_results), crawl_tool])
    else:
        logger.info("[code_researcher_node] Web search disabled, using local resources only")

    retriever_tool = get_retriever_tool(state.get("resources", []))
    if retriever_tool:
        tools.insert(0, retriever_tool)

    return await _setup_and_execute_agent_step(
        state,
        config,
        "code_researcher",
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


async def code_reviewer_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Code reviewer node that inspects changes and flags risks."""
    logger.info("Code reviewer is analyzing code changes.")
    logger.debug("[code_reviewer_node] Starting code reviewer agent")

    tools = []
    try:
        from backend.deer_flow.tools.code_tools import file_system_tool
        tools.append(file_system_tool)
    except Exception as e:
        logger.debug(f"[code_reviewer_node] file_system_tool unavailable: {e}")

    return await _setup_and_execute_agent_step(
        state,
        config,
        "code_reviewer",
        tools,
    )


async def code_architect_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Code architect node that evaluates design and architecture."""
    logger.info("Code architect is reviewing architecture.")
    logger.debug("[code_architect_node] Starting code architect agent")

    tools = []
    try:
        from backend.deer_flow.tools.code_tools import file_system_tool
        tools.append(file_system_tool)
    except Exception as e:
        logger.debug(f"[code_architect_node] file_system_tool unavailable: {e}")

    return await _setup_and_execute_agent_step(
        state,
        config,
        "code_architect",
        tools,
    )


async def code_refiner_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Code refiner node that cleans up and formats code changes."""
    logger.info("Code refiner is refining code changes.")
    logger.debug("[code_refiner_node] Starting code refiner agent")

    from backend.deer_flow.tools.code_tools import get_code_tools

    tools = [python_repl_tool]
    tools.extend(get_code_tools())

    return await _setup_and_execute_agent_step(
        state,
        config,
        "code_refiner",
        tools,
    )


async def code_tester_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Code tester node that runs test tools only."""
    logger.info("Code tester is running tests.")
    logger.debug("[code_tester_node] Starting code tester agent")

    from backend.deer_flow.tools.test_tools import get_test_tools

    tools = get_test_tools()

    return await _setup_and_execute_agent_step(
        state,
        config,
        "code_tester",
        tools,
    )


async def code_reporter_node(
    state: State, config: RunnableConfig
) -> Command[Literal["__end__"]]:
    """Code reporter node that outputs a code-focused summary."""
    logger.info("Code reporter generating code-focused summary.")
    configurable = Configuration.from_runnable_config(config)
    locale = state.get("locale", "en-US")

    messages = apply_prompt_template("code_reporter", state, configurable, locale)
    llm = get_llm_by_type(AGENT_LLM_MAP.get("code_reporter", "basic"))
    response = llm.invoke(messages)
    content = strip_think_tags(get_message_content(response) or "")

    return Command(
        update={
            "messages": [AIMessage(content=content, name="code_reporter")],
            "code_report_complete": True,
            **preserve_state_meta_fields(state),
        },
        goto="__end__",
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
) -> Command[Literal["human_feedback"]]:
    """AI comparison planner node that creates a comparison plan."""
    if state.get("enable_debate_mode", False):
        logger.warning("AI Comparison node called with debate_mode=True - skipping.")
        return Command(update=preserve_state_meta_fields(state), goto="reporter")

    configurable = Configuration.from_runnable_config(config)
    locale = state.get("locale", "en-US")
    research_topic = state.get("research_topic", "Unknown topic")

    set_ai_comparison_context(
        max_search_results=configurable.max_search_results,
        resources=state.get("resources", []),
    )

    from backend.deer_flow.prompts.planner_model import Plan, Step, StepType

    if locale.startswith("sv"):
        thought = "Kör AI‑jämförelse med modellfrågor, faktakoll, meta‑analys och syntes."
        steps = [
            Step(
                need_search=False,
                step_type=StepType.AI_QUERY,
                title="GPT‑3.5",
                description="Model: gpt-3.5-turbo",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_QUERY,
                title="Gemini 2.5 Flash",
                description="Model: gemini-2.5-flash",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_QUERY,
                title="DeepSeek Chat",
                description="Model: deepseek-chat",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_QUERY,
                title="Grok‑4 Fast Reasoning",
                description="Model: grok-4-fast-reasoning",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_QUERY,
                title="OneSeek Local",
                description="Model: oneseek-local",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_FACT_CHECK,
                title="Faktakoll",
                description="Verifiera centrala påståenden med externa källor.",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_META,
                title="Meta‑analys",
                description="Poängsätt modellerna över meta‑analytiska dimensioner.",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_SYNTH,
                title="Syntetisera svar",
                description="Skapa en optimal syntes baserad på all input.",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_REPORT,
                title="Skapa jämförelserapport",
                description="Skriv slutrapporten med tabeller och källor.",
                execution_res=None,
            ),
        ]
    else:
        thought = "Run AI comparison with model queries, fact-checking, meta-analysis, and synthesis."
        steps = [
            Step(
                need_search=False,
                step_type=StepType.AI_QUERY,
                title="GPT-3.5",
                description="Model: gpt-3.5-turbo",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_QUERY,
                title="Gemini 2.5 Flash",
                description="Model: gemini-2.5-flash",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_QUERY,
                title="DeepSeek Chat",
                description="Model: deepseek-chat",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_QUERY,
                title="Grok-4 Fast Reasoning",
                description="Model: grok-4-fast-reasoning",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_QUERY,
                title="OneSeek Local",
                description="Model: oneseek-local",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_FACT_CHECK,
                title="Fact Check",
                description="Verify key claims with external sources.",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_META,
                title="Meta Analysis",
                description="Score models across meta-analysis dimensions.",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_SYNTH,
                title="Synthesize Answer",
                description="Produce optimal synthesized answer from all inputs.",
                execution_res=None,
            ),
            Step(
                need_search=False,
                step_type=StepType.AI_REPORT,
                title="Generate Comparison Report",
                description="Write the final comparison report with tables.",
                execution_res=None,
            ),
        ]

    comparison_plan = Plan(
        locale=locale,
        has_enough_context=False,
        thought=thought,
        title=research_topic,
        steps=steps,
    )

    return Command(
        update={
            **preserve_state_meta_fields(state),
            "messages": [
                AIMessage(
                    content=json.dumps(comparison_plan.model_dump(), ensure_ascii=False, indent=2),
                    name="planner",
                )
            ],
            "current_plan": comparison_plan,
            "plan_source": "ai_comparison",
            "ai_compare_responses": [],
            "ai_compare_responses_json": None,
            "ai_compare_fact_check": None,
            "ai_compare_fact_check_json": None,
            "ai_compare_meta": None,
            "ai_compare_meta_json": None,
            "ai_compare_synthesis": None,
            "ai_compare_synthesis_json": None,
            "ai_compare_report_complete": False,
            "ai_compare_pending_tool": None,
        },
        goto="human_feedback",
    )


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


async def ai_compare_query_node(
    state: State, config: RunnableConfig
) -> Command[Literal["ai_compare_team"]]:
    """Query AI models and store responses."""
    configurable = Configuration.from_runnable_config(config)
    from backend.deer_flow.prompts.planner_model import Plan, StepType
    set_ai_comparison_context(
        max_search_results=configurable.max_search_results,
        resources=state.get("resources", []),
    )
    current_plan = state.get("current_plan")
    current_step = None
    if isinstance(current_plan, Plan):
        for step in current_plan.steps:
            if not step.execution_res and step.step_type == StepType.AI_QUERY:
                current_step = step
                break

    def _format_ai_compare_responses(responses: list[dict[str, Any]]) -> str:
        sections: list[str] = []
        seen: set[str] = set()
        for idx, resp in enumerate(responses):
            if not isinstance(resp, dict):
                continue
            model_key = str(resp.get("model") or "").strip()
            display_name = str(
                resp.get("display_name") or model_key or f"Model {idx + 1}"
            ).strip()
            dedupe_key = model_key or display_name.lower()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            label = display_name
            if resp.get("cached"):
                label = f"{label} (cached)"
            response = resp.get("response")
            error = resp.get("error")
            if response:
                sections.append(f"### {label}\n\n{response}")
            elif error:
                sections.append(f"### {label}\n\nError: {error}")
            else:
                sections.append(f"### {label}\n\n(No response)")
        return "\n\n---\n\n".join([section for section in sections if section]).strip()

    parallel_enabled = get_bool_env("AI_COMPARE_PARALLEL_QUERY", True)
    pending_tool = state.get("ai_compare_pending_tool") or {}
    if parallel_enabled:
        if pending_tool.get("step") == "ai_compare_query_all":
            tool_call_id = pending_tool.get("tool_call_id") or uuid4().hex
            tool_args = pending_tool.get("tool_args") or {}
            try:
                tool_output = await query_all_models.ainvoke(tool_args)
            except Exception as exc:
                tool_output = json.dumps(
                    {
                        "error": str(exc),
                        "success": False,
                    },
                    ensure_ascii=False,
                )
            payload = _parse_json_content(str(tool_output))
            responses = []
            if isinstance(payload, list):
                responses = [resp for resp in payload if isinstance(resp, dict)]
            elif isinstance(payload, dict) and payload.get("responses"):
                responses = [
                    resp
                    for resp in payload.get("responses", [])
                    if isinstance(resp, dict)
                ]
            existing = state.get("ai_compare_responses", [])
            merged = {
                resp.get("model"): resp for resp in existing if isinstance(resp, dict)
            }
            for resp in responses:
                if isinstance(resp, dict):
                    merged[resp.get("model")] = resp
            merged_responses = [resp for resp in merged.values() if resp]
            responses_json = json.dumps(merged_responses, ensure_ascii=False)
            if isinstance(current_plan, Plan):
                for step in current_plan.steps:
                    if not step.execution_res and step.step_type == StepType.AI_QUERY:
                        step.execution_res = f"Completed: {step.title}"
            response_text = _format_ai_compare_responses(merged_responses)
            messages = [
                ToolMessage(
                    content=response_text or str(tool_output),
                    tool_call_id=tool_call_id,
                    name="query_all_models",
                ),
                AIMessage(
                    content=response_text or "",
                    name="ai_compare_query",
                ),
            ]
            return Command(
                update={
                    **preserve_state_meta_fields(state),
                    "ai_compare_pending_tool": None,
                    "ai_compare_responses": merged_responses,
                    "ai_compare_responses_json": responses_json,
                    "messages": messages,
                    "current_plan": current_plan,
                },
                goto="ai_compare_team",
            )

        existing = state.get("ai_compare_responses", [])
        if existing:
            if isinstance(current_plan, Plan):
                for step in current_plan.steps:
                    if not step.execution_res and step.step_type == StepType.AI_QUERY:
                        step.execution_res = f"Completed: {step.title}"
            return Command(
                update={
                    **preserve_state_meta_fields(state),
                    "current_plan": current_plan,
                },
                goto="ai_compare_team",
            )

        query = state.get("research_topic", "")
        tool_call_id = uuid4().hex
        tool_args = {"query": query}
        messages = [
            AIMessage(
                content="",
                name="ai_compare_query",
                tool_calls=[
                    {
                        "id": tool_call_id,
                        "name": "query_all_models",
                        "args": tool_args,
                    }
                ],
            ),
        ]
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "ai_compare_pending_tool": {
                    "step": "ai_compare_query_all",
                    "tool_call_id": tool_call_id,
                    "tool_args": tool_args,
                },
                "messages": messages,
                "current_plan": current_plan,
            },
            goto="ai_compare_team",
        )

    model_tool_map = {
        "gpt-3.5-turbo": query_gpt35,
        "gemini-2.5-flash": query_gemini_flash,
        "deepseek-chat": query_deepseek,
        "grok-4-fast-reasoning": query_grok4,
        "oneseek-local": query_oneseek_local,
    }
    if pending_tool.get("step") == "ai_compare_query":
        selected_model = pending_tool.get("model_key")
        tool_args = pending_tool.get("tool_args") or {}
        tool_call_id = pending_tool.get("tool_call_id") or uuid4().hex
        selected_tool = model_tool_map.get(selected_model)
        if not selected_tool:
            return Command(
                update={
                    **preserve_state_meta_fields(state),
                    "ai_compare_pending_tool": None,
                },
                goto="ai_compare_team",
            )

        try:
            tool_output = await selected_tool.ainvoke(tool_args)
        except Exception as exc:
            tool_output = json.dumps(
                {
                    "model": selected_model or "unknown",
                    "display_name": selected_model or "Unknown",
                    "response": None,
                    "success": False,
                    "error": str(exc),
                },
                ensure_ascii=False,
            )

        payload = _parse_json_content(str(tool_output))
        def _build_meta_summary(meta_data: dict[str, Any], locale_value: str) -> str:
            if not isinstance(meta_data, dict):
                return ""
            labels_en = {
                "cognitive_properties": "Cognitive properties",
                "integrity_objectivity": "Integrity & objectivity",
                "stability_emotional": "Stability & emotional profile",
                "adaptivity_system": "Adaptivity & system role",
            }
            labels_sv = {
                "cognitive_properties": "Kognitiva egenskaper",
                "integrity_objectivity": "Integritet & objektivitet",
                "stability_emotional": "Stabilitet & emotionell profil",
                "adaptivity_system": "Adaptivitet & systemroll",
            }
            label_map = labels_sv if locale_value.startswith("sv") else labels_en
            sections = []
            for key in [
                "cognitive_properties",
                "integrity_objectivity",
                "stability_emotional",
                "adaptivity_system",
            ]:
                item = meta_data.get(key)
                if not item:
                    continue
                if isinstance(item, dict):
                    text = item.get("analysis") or item.get("error")
                    if not text:
                        text = json.dumps(item, ensure_ascii=False)
                else:
                    text = str(item)
                label = label_map.get(key, key.replace("_", " ").title())
                sections.append(f"### {label}\n\n{text}")
            return "\n\n".join(sections).strip()
        responses = []
        if isinstance(payload, dict) and payload:
            responses = [payload]
        existing = state.get("ai_compare_responses", [])
        merged = {resp.get("model"): resp for resp in existing if isinstance(resp, dict)}
        for resp in responses:
            if isinstance(resp, dict):
                merged[resp.get("model")] = resp
        merged_responses = [resp for resp in merged.values() if resp]
        responses_json = json.dumps(merged_responses, ensure_ascii=False)
        if current_step:
            display = selected_model or current_step.title
            current_step.execution_res = f"Completed: {display}"
        display_name = None
        if responses and isinstance(responses[0], dict):
            display_name = responses[0].get("display_name")
        name = display_name or tool_args.get("display_name") or selected_model or "Model"
        base_response = responses[0] if responses else {}
        response_text = _format_ai_compare_responses(
            [
                {
                    **(base_response if isinstance(base_response, dict) else {}),
                    "display_name": name,
                    "model": selected_model
                    or (base_response.get("model") if isinstance(base_response, dict) else None),
                }
            ]
        )
        messages = [
            ToolMessage(
                content=response_text or str(tool_output),
                tool_call_id=tool_call_id,
                name="query_model_in_round",
            ),
            AIMessage(
                content=response_text or "",
                name="ai_compare_query",
            ),
        ]
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "ai_compare_pending_tool": None,
                "ai_compare_responses": merged_responses,
                "ai_compare_responses_json": responses_json,
                "messages": messages,
                "current_plan": current_plan,
            },
            goto="ai_compare_team",
        )

    selected_tool = None
    selected_model = None
    if current_step:
        step_text = f"{current_step.title} {current_step.description}".lower()
        for model_key, tool in model_tool_map.items():
            if model_key in step_text or model_key.replace("-", " ") in step_text:
                selected_tool = tool
                selected_model = model_key
                break
    if not selected_tool:
        return Command(update=preserve_state_meta_fields(state), goto="ai_compare_team")

    existing = state.get("ai_compare_responses", [])
    already_completed = False
    for resp in existing:
        if (
            isinstance(resp, dict)
            and resp.get("model") == selected_model
            and (resp.get("response") or resp.get("error"))
        ):
            already_completed = True
            break
    if already_completed:
        if current_step and not current_step.execution_res:
            display = selected_model or current_step.title
            current_step.execution_res = f"Completed: {display}"
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "current_plan": current_plan,
            },
            goto="ai_compare_team",
        )

    query = state.get("research_topic", "")
    tool_call_id = uuid4().hex
    tool_args = {
        "query": query,
        "model_key": selected_model,
        "user_query": query,
        "locale": state.get("locale", "en-US"),
        "display_name": current_step.title if current_step else selected_model,
    }
    if selected_model == "oneseek-local":
        tool_args["peer_responses_json"] = state.get("ai_compare_responses_json") or json.dumps(
            state.get("ai_compare_responses", []), ensure_ascii=False
        )
    messages = [
        AIMessage(
            content="",
            name="ai_compare_query",
            tool_calls=[
                {
                    "id": tool_call_id,
                    "name": "query_model_in_round",
                    "args": tool_args,
                }
            ],
        ),
    ]
    return Command(
        update={
            **preserve_state_meta_fields(state),
            "ai_compare_pending_tool": {
                "step": "ai_compare_query",
                "tool_call_id": tool_call_id,
                "tool_args": tool_args,
                "model_key": selected_model,
            },
            "messages": messages,
            "current_plan": current_plan,
        },
        goto="ai_compare_team",
    )


async def ai_compare_fact_check_node(
    state: State, config: RunnableConfig
) -> Command[Literal["ai_compare_team"]]:
    """Fact-check AI model responses."""
    configurable = Configuration.from_runnable_config(config)
    set_ai_comparison_context(
        max_search_results=configurable.max_search_results,
        resources=state.get("resources", []),
    )
    current_plan = state.get("current_plan")
    from backend.deer_flow.prompts.planner_model import Plan, StepType
    pending_tool = state.get("ai_compare_pending_tool") or {}
    if pending_tool.get("step") == "ai_compare_fact_check":
        tool_call_id = pending_tool.get("tool_call_id") or uuid4().hex
        tool_args = pending_tool.get("tool_args") or {}
        if not tool_args:
            query = state.get("research_topic", "")
            model_responses_json = state.get("ai_compare_responses_json") or json.dumps(
                state.get("ai_compare_responses", []), ensure_ascii=False
            )
            tool_args = {"query": query, "model_responses_json": model_responses_json}
        try:
            tool_output = await fact_check_responses.ainvoke(tool_args)
        except Exception as exc:
            tool_output = json.dumps({"error": str(exc)}, ensure_ascii=False)
        payload = _parse_json_content(str(tool_output))
        ui_text = ""
        if isinstance(payload, dict) and payload:
            summary = payload.get("fact_check_summary") or payload.get("summary")
            if summary:
                ui_text = f"### Faktakoll\n\n{summary}"
        messages = [
            ToolMessage(
                content=ui_text or str(tool_output),
                tool_call_id=tool_call_id,
                name="fact_check_responses",
            ),
            AIMessage(
                content=ui_text or "",
                name="ai_compare_fact_check",
            ),
        ]
        if isinstance(current_plan, Plan):
            for step in current_plan.steps:
                if not step.execution_res and step.step_type == StepType.AI_FACT_CHECK:
                    step.execution_res = "Fact check completed"
                    break
        fact_check_json = json.dumps(payload, ensure_ascii=False) if payload else None
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "ai_compare_pending_tool": None,
                "ai_compare_fact_check": payload or None,
                "ai_compare_fact_check_json": fact_check_json,
                "messages": messages,
                "current_plan": current_plan,
            },
            goto="ai_compare_team",
        )

    query = state.get("research_topic", "")
    model_responses_json = state.get("ai_compare_responses_json") or json.dumps(
        state.get("ai_compare_responses", []), ensure_ascii=False
    )
    tool_call_id = uuid4().hex
    tool_args = {"query": query, "model_responses_json": model_responses_json}
    messages = [
        AIMessage(
            content="",
            name="ai_compare_fact_check",
            tool_calls=[
                {"id": tool_call_id, "name": "fact_check_responses", "args": tool_args}
            ],
        ),
    ]
    return Command(
        update={
            **preserve_state_meta_fields(state),
            "ai_compare_pending_tool": {
                "step": "ai_compare_fact_check",
                "tool_call_id": tool_call_id,
                "tool_args": tool_args,
            },
            "messages": messages,
            "current_plan": current_plan,
        },
        goto="ai_compare_team",
    )


async def ai_compare_meta_node(
    state: State, config: RunnableConfig
) -> Command[Literal["ai_compare_team"]]:
    """Run meta-analysis on AI model responses."""
    configurable = Configuration.from_runnable_config(config)
    def _build_meta_summary(meta_data: dict[str, Any], locale_value: str) -> str:
        if not isinstance(meta_data, dict):
            return ""
        labels_en = {
            "cognitive_properties": "Cognitive properties",
            "integrity_objectivity": "Integrity & objectivity",
            "stability_emotional": "Stability & emotional profile",
            "adaptivity_system": "Adaptivity & system role",
        }
        labels_sv = {
            "cognitive_properties": "Kognitiva egenskaper",
            "integrity_objectivity": "Integritet & objektivitet",
            "stability_emotional": "Stabilitet & emotionell profil",
            "adaptivity_system": "Adaptivitet & systemroll",
        }
        label_map = labels_sv if locale_value.startswith("sv") else labels_en
        sections = []
        for key in [
            "cognitive_properties",
            "integrity_objectivity",
            "stability_emotional",
            "adaptivity_system",
        ]:
            item = meta_data.get(key)
            if not item:
                continue
            if isinstance(item, dict):
                text = item.get("analysis") or item.get("error")
                if not text:
                    text = json.dumps(item, ensure_ascii=False)
            else:
                text = str(item)
            label = label_map.get(key, key.replace("_", " ").title())
            sections.append(f"### {label}\n\n{text}")
        return "\n\n".join(sections).strip()
    set_ai_comparison_context(
        max_search_results=configurable.max_search_results,
        resources=state.get("resources", []),
    )
    current_plan = state.get("current_plan")
    from backend.deer_flow.prompts.planner_model import Plan, StepType
    pending_tool = state.get("ai_compare_pending_tool") or {}
    if pending_tool.get("step") == "ai_compare_meta":
        tool_call_id = pending_tool.get("tool_call_id") or uuid4().hex
        tool_args = pending_tool.get("tool_args") or {}
        if not tool_args:
            query = state.get("research_topic", "")
            model_responses_json = state.get("ai_compare_responses_json") or json.dumps(
                state.get("ai_compare_responses", []), ensure_ascii=False
            )
            analysis_json = state.get("ai_compare_fact_check_json") or json.dumps(
                state.get("ai_compare_fact_check") or {}, ensure_ascii=False
            )
            tool_args = {
                "query": query,
                "model_responses_json": model_responses_json,
                "analysis_json": analysis_json,
            }
        try:
            tool_output = await run_meta_analysis.ainvoke(tool_args)
        except Exception as exc:
            tool_output = json.dumps({"error": str(exc)}, ensure_ascii=False)
        payload = _parse_json_content(str(tool_output))
        meta_results = payload.get("meta_results") if payload else None
        meta_payload = meta_results or payload
        meta_summary = _build_meta_summary(meta_payload or {}, state.get("locale", "en-US"))
        messages = [
            ToolMessage(
                content=str(tool_output),
                tool_call_id=tool_call_id,
                name="run_meta_analysis",
            ),
            AIMessage(
                content=meta_summary or "",
                name="ai_compare_meta",
            ),
        ]
        if isinstance(current_plan, Plan):
            for step in current_plan.steps:
                if not step.execution_res and step.step_type == StepType.AI_META:
                    step.execution_res = "Meta analysis completed"
                    break
        meta_results = payload.get("meta_results") if payload else None
        meta_payload = meta_results or payload
        meta_json = json.dumps(meta_payload, ensure_ascii=False) if meta_payload else None
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "ai_compare_pending_tool": None,
                "ai_compare_meta": meta_payload,
                "ai_compare_meta_json": meta_json,
                "messages": messages,
                "current_plan": current_plan,
            },
            goto="ai_compare_team",
        )

    query = state.get("research_topic", "")
    model_responses_json = state.get("ai_compare_responses_json") or json.dumps(
        state.get("ai_compare_responses", []), ensure_ascii=False
    )
    analysis_json = state.get("ai_compare_fact_check_json") or json.dumps(
        state.get("ai_compare_fact_check") or {}, ensure_ascii=False
    )
    tool_call_id = uuid4().hex
    tool_args = {
        "query": query,
        "model_responses_json": model_responses_json,
        "analysis_json": analysis_json,
    }
    messages = [
        AIMessage(
            content="",
            name="ai_compare_meta",
            tool_calls=[
                {"id": tool_call_id, "name": "run_meta_analysis", "args": tool_args}
            ],
        ),
    ]
    return Command(
        update={
            **preserve_state_meta_fields(state),
            "ai_compare_pending_tool": {
                "step": "ai_compare_meta",
                "tool_call_id": tool_call_id,
                "tool_args": tool_args,
            },
            "messages": messages,
            "current_plan": current_plan,
        },
        goto="ai_compare_team",
    )


async def ai_compare_synth_node(
    state: State, config: RunnableConfig
) -> Command[Literal["ai_compare_team"]]:
    """Synthesize optimal answer."""
    configurable = Configuration.from_runnable_config(config)
    set_ai_comparison_context(
        max_search_results=configurable.max_search_results,
        resources=state.get("resources", []),
    )
    current_plan = state.get("current_plan")
    from backend.deer_flow.prompts.planner_model import Plan, StepType
    pending_tool = state.get("ai_compare_pending_tool") or {}
    if pending_tool.get("step") == "ai_compare_synth":
        tool_call_id = pending_tool.get("tool_call_id") or uuid4().hex
        tool_args = pending_tool.get("tool_args") or {}
        if not tool_args:
            query = state.get("research_topic", "")
            model_responses_json = state.get("ai_compare_responses_json") or json.dumps(
                state.get("ai_compare_responses", []), ensure_ascii=False
            )
            analysis_json = state.get("ai_compare_fact_check_json") or json.dumps(
                state.get("ai_compare_fact_check") or {}, ensure_ascii=False
            )
            meta_json = state.get("ai_compare_meta_json") or json.dumps(
                state.get("ai_compare_meta") or {}, ensure_ascii=False
            )
            tool_args = {
                "query": query,
                "model_responses_json": model_responses_json,
                "analysis_json": analysis_json,
                "meta_json": meta_json,
                "locale": state.get("locale", "en-US"),
            }
        try:
            tool_result = await synthesize_optimal_answer.ainvoke(tool_args)
        except Exception as exc:
            tool_result = json.dumps({"error": str(exc)}, ensure_ascii=False)
        payload = _parse_json_content(str(tool_result))
        synthesis_payload = None
        if isinstance(payload, dict):
            synthesis_payload = payload.get("synthesis") or payload
        elif payload:
            synthesis_payload = payload
        synthesis_json = (
            json.dumps(synthesis_payload, ensure_ascii=False) if synthesis_payload else None
        )
        if isinstance(current_plan, Plan):
            for step in current_plan.steps:
                if not step.execution_res and step.step_type == StepType.AI_SYNTH:
                    step.execution_res = "AI comparison synthesis completed"
                    break
        messages = [
            ToolMessage(
                content=(
                    json.dumps(synthesis_payload, ensure_ascii=False)
                    if synthesis_payload
                    else str(tool_result)
                ),
                tool_call_id=tool_call_id,
                name="synthesize_optimal_answer",
            ),
            AIMessage(
                content=(
                    synthesis_payload.get("synthesized_answer")
                    if isinstance(synthesis_payload, dict)
                    and synthesis_payload.get("synthesized_answer")
                    else (
                        synthesis_payload.get("synthesis")
                        if isinstance(synthesis_payload, dict)
                        else ""
                    )
                ),
                name="ai_compare_synth",
            ),
        ]
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "ai_compare_pending_tool": None,
                "ai_compare_synthesis": synthesis_payload,
                "ai_compare_synthesis_json": synthesis_json,
                "messages": messages,
                "current_plan": current_plan,
            },
            goto="ai_compare_team",
        )

    query = state.get("research_topic", "")
    model_responses_json = state.get("ai_compare_responses_json") or json.dumps(
        state.get("ai_compare_responses", []), ensure_ascii=False
    )
    analysis_json = state.get("ai_compare_fact_check_json") or json.dumps(
        state.get("ai_compare_fact_check") or {}, ensure_ascii=False
    )
    meta_json = state.get("ai_compare_meta_json") or json.dumps(
        state.get("ai_compare_meta") or {}, ensure_ascii=False
    )
    tool_call_id = uuid4().hex
    tool_args = {
        "query": query,
        "model_responses_json": model_responses_json,
        "analysis_json": analysis_json,
        "meta_json": meta_json,
        "locale": state.get("locale", "en-US"),
    }
    return Command(
        update={
            **preserve_state_meta_fields(state),
            "ai_compare_pending_tool": {
                "step": "ai_compare_synth",
                "tool_call_id": tool_call_id,
                "tool_args": tool_args,
            },
            "messages": [
                AIMessage(
                    content="",
                    name="ai_compare_synth",
                    tool_calls=[
                        {
                            "id": tool_call_id,
                            "name": "synthesize_optimal_answer",
                            "args": tool_args,
                        }
                    ],
                )
            ],
            "current_plan": current_plan,
        },
        goto="ai_compare_team",
    )


async def ai_compare_reporter_node(
    state: State, config: RunnableConfig
) -> Command[Literal["__end__"]]:
    """Generate final AI comparison report."""
    configurable = Configuration.from_runnable_config(config)
    locale = state.get("locale", "en-US")
    messages = apply_prompt_template("ai_compare_reporter", state, configurable, locale)
    llm = get_llm_by_type(AGENT_LLM_MAP.get("ai_compare_reporter", "basic"))
    response = llm.invoke(messages)
    content = strip_think_tags(get_message_content(response) or "")
    current_plan = state.get("current_plan")
    from backend.deer_flow.prompts.planner_model import Plan, StepType
    if isinstance(current_plan, Plan):
        for step in current_plan.steps:
            if not step.execution_res and step.step_type == StepType.AI_REPORT:
                step.execution_res = "AI comparison report generated"
                break
    return Command(
        update={
            **preserve_state_meta_fields(state),
            "messages": [AIMessage(content=content, name="ai_compare_reporter")],
            "ai_compare_report_complete": True,
            "current_plan": current_plan,
        },
        goto="__end__",
    )

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
    scores = state.get("debate_scores", {"proponent": 0, "opponent": 0})
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
                        "debate_round": current_round,
                        "debate_scores": scores,
                        "debate_knockout": knockout,
                        "debate_max_rounds": max_rounds,
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
        thread_id = get_thread_id_from_config(config)
        user_query = state.get("clarified_research_topic") or state.get("research_topic", "")
        vote_results = None
        debate_rounds = []
        internal_fact_checks = []
        internal_summaries = []
        try:
            from backend.debate_flow import get_debate_flow
            debate_flow = get_debate_flow(thread_id=thread_id)
            round_3_responses = list(debate_flow.chain_so_far) if debate_flow.chain_so_far else []
            if round_3_responses:
                allowed_models = [resp.get("model") for resp in round_3_responses if resp.get("model")]
                vote_results = await debate_flow.collect_votes(
                    user_query,
                    round_3_responses,
                    allowed_models=allowed_models,
                )
            debate_rounds = list(debate_flow.debate_history)
            if round_3_responses:
                debate_rounds.append({
                    "round": debate_flow.current_round,
                    "responses": round_3_responses,
                })
            internal_fact_checks = list(getattr(debate_flow, "internal_fact_checks", []))
            internal_summaries = list(getattr(debate_flow, "internal_summaries", []))
        except Exception as e:
            logger.warning(f"Failed to collect debate votes or history: {e}")
        rounds_preview = build_rounds_preview(debate_rounds)
        summary_msg = AIMessage(
            content=json.dumps({
                "final_round": current_round - 1,
                "final_scores": scores,
                "exit_reason": exit_reason,
                "external_ai_models": ["Grok", "Gemini", "ChatGPT", "DeepSeek"],
                "vote_results": vote_results,
                "rounds": rounds_preview,
            }, ensure_ascii=False, indent=2),
            name="debate_orchestrator"
        )
        
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "messages": [summary_msg],
                "debate_complete": True,
                "debate_round": current_round,
                "debate_scores": scores,
                "debate_knockout": knockout,
                "debate_max_rounds": max_rounds,
                "debate_error_count": 0,  # Reset on successful completion
                "debate_results": {
                    "status": "completed",
                    "final_round": current_round - 1,
                    "rounds": debate_rounds,
                    "vote_results": vote_results,
                    "internal_fact_checks": internal_fact_checks,
                    "internal_summaries": internal_summaries,
                    "user_query": user_query,
                },
            },
            goto="reporter"
        )
    elif knockout:
        logger.info("Knockout detected in previous round")
        exit_reason = "Knockout-argument identifierat"
        thread_id = get_thread_id_from_config(config)
        user_query = state.get("clarified_research_topic") or state.get("research_topic", "")
        debate_rounds = []
        internal_fact_checks = []
        internal_summaries = []
        try:
            from backend.debate_flow import get_debate_flow
            debate_flow = get_debate_flow(thread_id=thread_id)
            current_responses = list(debate_flow.chain_so_far) if debate_flow.chain_so_far else []
            debate_rounds = list(debate_flow.debate_history)
            if current_responses:
                debate_rounds.append({
                    "round": debate_flow.current_round,
                    "responses": current_responses,
                })
            internal_fact_checks = list(getattr(debate_flow, "internal_fact_checks", []))
            internal_summaries = list(getattr(debate_flow, "internal_summaries", []))
        except Exception as e:
            logger.warning(f"Failed to collect debate history for knockout: {e}")
        rounds_preview = build_rounds_preview(debate_rounds)
        summary_msg = AIMessage(
            content=json.dumps({
                "final_round": current_round - 1,
                "final_scores": scores,
                "exit_reason": exit_reason,
                "external_ai_models": ["Grok", "Gemini", "ChatGPT", "DeepSeek"],
                "rounds": rounds_preview,
            }, ensure_ascii=False, indent=2),
            name="debate_orchestrator"
        )
        
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "messages": [summary_msg],
                "debate_complete": True,
                "debate_round": current_round,
                "debate_scores": scores,
                "debate_knockout": knockout,
                "debate_max_rounds": max_rounds,
                "debate_error_count": 0,  # Reset on successful completion
                "debate_results": {
                    "status": "completed",
                    "final_round": current_round - 1,
                    "rounds": debate_rounds,
                    "vote_results": None,
                    "internal_fact_checks": internal_fact_checks,
                    "internal_summaries": internal_summaries,
                    "user_query": user_query,
                },
            },
            goto="reporter"
        )
    
    # Start new round - route to external_ai_caller to get real AI responses
    logger.info(f"Round {current_round}: Routing to external_ai_caller for real AI model responses")
    
    # Build state update explicitly to debug
    preserved_fields = preserve_state_meta_fields(state)
    logger.info(f"Orchestrator: preserved_fields has debate_round={preserved_fields.get('debate_round')}")
    logger.info(f"Orchestrator: Setting debate_round={current_round} in state update (should override preserved value)")
    
    state_update = {
        **preserved_fields,
        "debate_round": current_round,
        "debate_scores": scores,
        "debate_knockout": knockout,
        "debate_max_rounds": max_rounds,
        "debate_complete": False,
        "debate_error_count": error_count,
        "debate_round_started": False,
        "debate_model_index": 0,
        "debate_model_order": [],
        "external_ai_responses": "",
        "debate_pending_model": None,
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
) -> Command[Literal["external_ai_caller", "fact_checker"]]:
    """
    External AI Caller node - orchestrates debate rounds one model at a time.
    
    This enables near-real-time UI updates by emitting tool calls/results
    after each model completes instead of after the full round.
    """
    logger.info("External AI Caller - orchestrating debate round (per-model)")
    configurable = Configuration.from_runnable_config(config)
    thread_id = get_thread_id_from_config(config)
    
    from backend.debate_flow import get_debate_flow
    # Reset debate_flow only when a new debate starts at round 1
    round_num = state.get("debate_round", 1)
    round_started = state.get("debate_round_started", False)
    debate_flow = get_debate_flow(
        max_search_results=configurable.max_search_results,
        resources=state.get("resources", []),
        thread_id=thread_id,
        reset=(round_num == 1 and not round_started),
    )
    
    # Determine model order and index
    model_order = state.get("debate_model_order") or []
    model_index = state.get("debate_model_index", 0)
    selected_models = state.get("debate_model_ids") or []
    if selected_models:
        allowed = set(selected_models)
        allowed.add("oneseek-local")
        model_order = [model for model in model_order if model in allowed]
        if model_index >= len(model_order):
            model_index = max(len(model_order) - 1, 0)
    pending_model = state.get("debate_pending_model")
    if pending_model and selected_models:
        allowed = set(selected_models)
        allowed.add("oneseek-local")
        if pending_model.get("model_key") not in allowed:
            pending_model = None
    
    try:
        tool_calls: list[dict[str, Any]] = []
        tool_results: list[ToolMessage] = []
        import uuid
        user_query = state.get("clarified_research_topic") or state.get("research_topic", "")
        locale = state.get("locale", "sv-SE")
        max_context_chars = int(os.getenv("DEBATE_TOOL_CONTEXT_MAX_CHARS", "4000"))
        max_tool_result_chars = int(os.getenv("DEBATE_TOOL_RESULT_MAX_CHARS", "12000"))
        
        if pending_model:
            model_key = pending_model.get("model_key")
            query_model_id = pending_model.get("tool_call_id")
            pending_index = pending_model.get("model_index", model_index)
            
            logger.info(f"Executing pending model {pending_index + 1}/{len(model_order)}: {model_key}")
            response = await debate_flow.query_model_in_debate(model_key, user_query, locale)
            
            if isinstance(response, dict):
                response_text = response.get("response", str(response))
                context_used = response.get("context_used", "")
            else:
                response_text = str(response)
                context_used = ""
            
            # Store full context for on-demand UI
            try:
                debate_flow.store_tool_context(query_model_id, context_used)
            except Exception:
                pass
            
            if context_used and len(context_used) > max_context_chars:
                context_used = (
                    context_used[:max_context_chars]
                    + f"... [trunkerat till {max_context_chars} tecken]"
                )
            tool_result_text = f"### {model_key} svar\n\n{response_text}"
            if isinstance(response, dict):
                latency_ms = response.get("latency_ms")
                tokens_in = response.get("tokens_in")
                tokens_out = response.get("tokens_out")
                metrics_parts = []
                if latency_ms is not None:
                    metrics_parts.append(f"latency_ms={latency_ms}")
                if tokens_in is not None:
                    metrics_parts.append(f"tokens_in={tokens_in}")
                if tokens_out is not None:
                    metrics_parts.append(f"tokens_out={tokens_out}")
                if metrics_parts:
                    tool_result_text += "\n\nMETRICS: " + " ".join(metrics_parts)
            if context_used:
                tool_result_text += "\n\n(Hela prompten kan hämtas via knappen i UI.)"
            if len(tool_result_text) > max_tool_result_chars:
                tool_result_text = (
                    tool_result_text[:max_tool_result_chars]
                    + f"... [trunkerat till {max_tool_result_chars} tecken]"
                )
            tool_results.append(
                ToolMessage(
                    content=tool_result_text,
                    tool_call_id=query_model_id,
                )
            )
            
            combined_response = state.get("external_ai_responses", "").strip()
            if combined_response:
                combined_response += "\n\n"
            combined_response += f"Model {model_key}: {response_text}"
            
            is_last_model = (pending_index + 1) >= len(model_order)
            messages_out: list[AIMessage | ToolMessage] = [*tool_results]
            if is_last_model:
                round_finished_id = f"call_{uuid.uuid4().hex[:24]}"
                messages_out.append(
                    AIMessage(
                        content="",
                        name="external_ai_caller",
                        tool_calls=[{
                            "id": round_finished_id,
                            "name": "round_finished",
                            "args": {"round_number": round_num},
                        }],
                        response_metadata={"finish_reason": "stop"},
                    )
                )
                messages_out.append(
                    ToolMessage(
                        content=f"Round {round_num} finished",
                        tool_call_id=round_finished_id,
                    )
                )
                summary_text = f"Runda {round_num} klar. {len(model_order)} modeller svarade."
                messages_out.append(
                    AIMessage(
                        content=summary_text,
                        name="external_ai_caller",
                        response_metadata={"finish_reason": "stop"},
                        additional_kwargs={
                            "round": round_num,
                            "models_queried": len(model_order),
                            "agent": "external_ai_caller",
                        },
                    )
                )
            
            next_index = pending_index + 1
            goto = "external_ai_caller" if next_index < len(model_order) else "fact_checker"
            
            return Command(
                update={
                    **preserve_state_meta_fields(state),
                    "messages": messages_out,
                    "external_ai_responses": combined_response,
                    "debate_round_started": round_started,
                    "debate_model_order": model_order,
                    "debate_model_index": next_index,
                    "debate_pending_model": None,
                },
                goto=goto,
            )
        
        if not round_started:
            # Initialize round and order
            logger.info(f"Starting debate round {round_num} for thread {thread_id}")
            debate_flow.start_new_round(round_num)
            model_order = debate_flow.get_randomized_order()
            selected_models = state.get("debate_model_ids") or []
            if selected_models:
                allowed = set(selected_models)
                allowed.add("oneseek-local")
                model_order = [model for model in model_order if model in allowed]
            model_index = 0
            round_started = True
            
            start_round_id = f"call_{uuid.uuid4().hex[:24]}"
            tool_calls.append({
                "id": start_round_id,
                "name": "start_debate_round",
                "args": {"round_number": round_num, "user_query": user_query, "locale": locale},
            })
            tool_results.append(
                ToolMessage(
                    content=f"Round {round_num} started",
                    tool_call_id=start_round_id,
                )
            )
        
        if not model_order:
            logger.warning("No debate models available; skipping to fact_checker")
            return Command(
                update={
                    **preserve_state_meta_fields(state),
                    "debate_round_started": round_started,
                    "debate_model_order": model_order,
                    "debate_model_index": model_index,
                    "debate_pending_model": None,
                },
                goto="fact_checker",
            )
        
        if model_index >= len(model_order):
            logger.info("All models already processed for this round")
            return Command(
                update={
                    **preserve_state_meta_fields(state),
                    "debate_round_started": round_started,
                    "debate_model_order": model_order,
                    "debate_model_index": model_index,
                    "debate_pending_model": None,
                },
                goto="fact_checker",
            )
        
        model_key = model_order[model_index]
        query_model_id = f"call_{uuid.uuid4().hex[:24]}"
        tool_calls.append({
            "id": query_model_id,
            "name": "query_model_in_round",
            "args": {
                "model_key": model_key,
                "round_number": round_num,
                "model_index": f"{model_index + 1}/{len(model_order)}",
                "models_total": len(model_order),
                "user_query": user_query,
                "locale": locale,
            },
        })
        
        response_message = AIMessage(
            content="",
            name="external_ai_caller",
            tool_calls=tool_calls,
            response_metadata={"finish_reason": "stop"},
            additional_kwargs={
                "round": round_num,
                "model_key": model_key,
                "model_index": model_index + 1,
                "models_total": len(model_order),
                "agent": "external_ai_caller",
            },
        )
        
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "messages": [response_message, *tool_results],
                "debate_round_started": round_started,
                "debate_model_order": model_order,
                "debate_model_index": model_index,
                "debate_pending_model": {
                    "tool_call_id": query_model_id,
                    "model_key": model_key,
                    "model_index": model_index,
                },
            },
            goto="external_ai_caller",
        )
    except Exception as e:
        logger.error(f"Error in external_ai_caller per-model flow: {e}", exc_info=True)
        error_message = AIMessage(
            content=f"Error in debate round: {str(e)}",
            name="external_ai_caller",
            response_metadata={"finish_reason": "stop"},
        )
        return Command(
            update={
                **preserve_state_meta_fields(state),
                "messages": [error_message],
                "debate_pending_model": None,
            },
            goto="fact_checker",
        )


async def fact_checker_node(
    state: State, config: RunnableConfig
) -> Command[Literal["synthesizer"]]:
    """Fact checker node - verifies claims from external AI models."""
    logger.info("Fact checker verifying external AI claims")
    configurable = Configuration.from_runnable_config(config)
    thread_id = get_thread_id_from_config(config)
    locale = state.get("locale", "en-US")
    
    from backend.debate_flow import get_debate_flow
    debate_flow = get_debate_flow(thread_id=thread_id)
    current_round = state.get("debate_round", 1)
    
    # Controlled claim extraction
    claims = extract_claim_sentences(state.get("external_ai_responses", ""))
    
    # Cached tools
    base_search_tool = get_web_search_tool(configurable.max_search_results)

    search_count = 0

    @tool("web_search")
    def cached_web_search(query: str) -> str:
        """Cached web search for fact checking (max 2)."""
        nonlocal search_count
        if search_count >= 2:
            return "SEARCH_LIMIT_REACHED: Max 2 web searches per round."
        search_count += 1
        return debate_flow.cached_web_search(query, current_round)

    @tool("crawl_tool")
    def cached_crawl(url: str) -> str:
        """Cached crawl for fact checking."""
        return debate_flow.cached_crawl(url, current_round)

    tools = [cached_web_search]
    
    # Build prompt for fact_checker
    messages = apply_prompt_template("fact_checker", state, configurable, locale)
    if claims:
        claims_text = "\n".join(f"- {claim}" for claim in claims)
        messages.append({
            "role": "system",
            "content": (
                "Verifiera endast följande explicit formulerade påståenden. "
                "Undvik att söka på nya eller vaga påståenden.\n\n"
                f"{claims_text}"
            ),
        })
    
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
    
    # Build synthesizer agent (run in parallel)
    synth_tools = [cached_web_search]
    synth_messages = apply_prompt_template("synthesizer", state, configurable, locale)
    synth_llm_limit = get_llm_token_limit_by_type(AGENT_LLM_MAP["synthesizer"])
    synth_pre_hook = partial(ContextManager(synth_llm_limit, 3).compress_messages)
    synth_agent = create_agent(
        "synthesizer",
        "synthesizer",
        synth_tools,
        "synthesizer",
        synth_pre_hook,
        interrupt_before_tools=configurable.interrupt_before_tools,
        locale=locale,
    )
    
    # Execute both agents concurrently
    synth_state = {**state, "messages": synth_messages}
    result, synth_result = await asyncio.gather(
        agent.ainvoke(state, config),
        synth_agent.ainvoke(synth_state, config),
    )
    
    # Extract responses
    response_content = ""
    if result and "messages" in result and len(result["messages"]) > 0:
        last_msg = result["messages"][-1]
        if hasattr(last_msg, "content"):
            response_content = last_msg.content
    
    synth_content = ""
    if synth_result and "messages" in synth_result and len(synth_result["messages"]) > 0:
        synth_msg = synth_result["messages"][-1]
        if hasattr(synth_msg, "content"):
            synth_content = synth_msg.content
    
    logger.info(f"Fact checker response length: {len(response_content)}")
    logger.info(f"Synthesizer response length: {len(synth_content)}")
    
    # Store internal fact-check + synthesis for next-round context
    try:
        if response_content:
            debate_flow.add_internal_fact_check(current_round, response_content)
        if synth_content:
            debate_flow.add_internal_summary(current_round, synth_content)
    except Exception as e:
        logger.warning(f"Failed to store internal fact/synth: {e}")
    
    combined_messages = []
    combined_messages.extend(result.get("messages", []) if result else [])
    combined_messages.extend(synth_result.get("messages", []) if synth_result else [])
    
    return Command(
        update={
            **preserve_state_meta_fields(state),
            "messages": combined_messages,
            "fact_checker_response": response_content,
            "synthesizer_response": synth_content,
        },
        goto="synthesizer"  # synthesizer node will skip if already present
    )


async def synthesizer_node(
    state: State, config: RunnableConfig
) -> Command[Literal["moderator"]]:
    """Synthesizer node - creates superior synthesis from both sides."""
    logger.info("Synthesizer creating integrated position")
    if state.get("synthesizer_response"):
        logger.info("Synthesizer already computed in parallel step, skipping.")
        return Command(
            update=preserve_state_meta_fields(state),
            goto="moderator",
        )
    configurable = Configuration.from_runnable_config(config)
    thread_id = get_thread_id_from_config(config)
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
    
    # Store internal synthesis summary for next-round context
    try:
        from backend.debate_flow import get_debate_flow
        debate_flow = get_debate_flow(thread_id=thread_id)
        current_round = state.get("debate_round", 1)
        if response_content:
            debate_flow.add_internal_summary(current_round, response_content)
    except Exception as e:
        logger.warning(f"Failed to store internal synthesis: {e}")
    
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

        # Enforce concise summary to keep UI readable
        summary_text = moderator_result.get("summary", "")
        if isinstance(summary_text, str) and len(summary_text) > 400:
            moderator_result["summary"] = summary_text[:400] + "... [trunkerat]"
        
        # Update scores
        round_proponent_score = moderator_result.get("proponent_score", 0)
        round_opponent_score = moderator_result.get("opponent_score", 0)
        
        scores["proponent"] += round_proponent_score
        scores["opponent"] += round_opponent_score
        
        knockout = moderator_result.get("knockout", False)
        
        logger.info(f"Round {current_round} scores: Proponent +{round_proponent_score}, Opponent +{round_opponent_score}")
        logger.info(f"Total scores: Proponent {scores['proponent']}, Opponent {scores['opponent']}")
        logger.info(f"Knockout: {knockout}")
        
        # Create summary message
        summary_msg = AIMessage(
            content=json.dumps(moderator_result, ensure_ascii=False, indent=2),
            name="moderator"
        )
        
        # Build state update - moderator only updates scores and knockout
        # debate_round is managed ONLY by debate_orchestrator to avoid conflicts
        state_update = {
            **preserve_state_meta_fields(state),
            "messages": [summary_msg],
            "debate_scores": scores,
            "debate_knockout": knockout,
            # DO NOT set debate_round here - let orchestrator manage it
        }
        
        logger.info(f"Moderator: Returning scores={scores}, knockout={knockout} to orchestrator")
        
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
