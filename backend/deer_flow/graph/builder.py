# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from backend.deer_flow.prompts.planner_model import StepType

from .nodes import (
    ai_comparison_node,
    analyst_node,
    background_investigation_node,
    coder_node,
    code_planner_node,
    coordinator_node,
    debate_planner_node,
    extract_plan_content,
    human_feedback_node,
    planner_node,
    reporter_node,
    research_team_node,
    researcher_node,
    tester_node,
    # New debate chain nodes
    debate_orchestrator_node,
    debate_team_node,
    proponent_node,
    opponent_node,
    fact_checker_node,
    synthesizer_node,
    moderator_node,
)
from .types import State
import json
from backend.deer_flow.utils.json_utils import repair_json_output
from backend.deer_flow.prompts.planner_model import Plan


def continue_to_running_research_team(state: State):
    current_plan = state.get("current_plan")
    
    # Handle case where current_plan is a string (from planner when AI comparison is enabled)
    if isinstance(current_plan, str):
        try:
            # Parse JSON string to Plan object
            plan_dict = json.loads(repair_json_output(current_plan))
            plan_content = extract_plan_content(plan_dict)
            plan_dict = json.loads(repair_json_output(plan_content))
            current_plan = Plan.model_validate(plan_dict)
        except Exception:
            # If parsing fails, route to planner
            return "planner"
    
    if not current_plan or not current_plan.steps:
        return "planner"

    if all(step.execution_res for step in current_plan.steps):
        return "planner"

    # Find first incomplete step
    incomplete_step = None
    for step in current_plan.steps:
        if not step.execution_res:
            incomplete_step = step
            break

    if not incomplete_step:
        return "planner"

    if incomplete_step.step_type == StepType.RESEARCH:
        return "researcher"
    if incomplete_step.step_type == StepType.ANALYSIS:
        return "analyst"
    if incomplete_step.step_type == StepType.PROCESSING:
        return "coder"
    if incomplete_step.step_type == StepType.TESTING:
        return "tester"
    return "planner"


def _build_debate_team_subgraph():
    """
    Build the debate team sub-graph with specialized debate nodes.
    
    Flow: proponent → opponent → fact_checker → synthesizer → moderator
    
    Returns a compiled sub-graph.
    """
    debate_builder = StateGraph(State)
    
    # Add debate team nodes
    debate_builder.add_node("proponent", proponent_node)
    debate_builder.add_node("opponent", opponent_node)
    debate_builder.add_node("fact_checker", fact_checker_node)
    debate_builder.add_node("synthesizer", synthesizer_node)
    debate_builder.add_node("moderator", moderator_node)
    
    # Wire them in sequence
    debate_builder.add_edge(START, "proponent")
    debate_builder.add_edge("proponent", "opponent")
    debate_builder.add_edge("opponent", "fact_checker")
    debate_builder.add_edge("fact_checker", "synthesizer")
    debate_builder.add_edge("synthesizer", "moderator")
    # moderator routes back to debate_orchestrator via Command
    
    return debate_builder.compile()


def _build_base_graph():
    """Build and return the base state graph with all nodes and edges."""
    builder = StateGraph(State)
    builder.add_edge(START, "coordinator")
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("background_investigator", background_investigation_node)
    builder.add_node("ai_comparison", ai_comparison_node)
    builder.add_node("debate_planner", debate_planner_node)
    builder.add_node("code_planner", code_planner_node)
    builder.add_node("planner", planner_node)
    builder.add_node("reporter", reporter_node)
    builder.add_node("research_team", research_team_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("coder", coder_node)
    builder.add_node("tester", tester_node)
    builder.add_node("human_feedback", human_feedback_node)
    
    # Add new debate chain nodes
    builder.add_node("debate_orchestrator", debate_orchestrator_node)
    # debate_team is implemented as a sub-graph, but we can add it as a placeholder
    # Actually, let's wire the debate nodes directly for simplicity
    builder.add_node("proponent", proponent_node)
    builder.add_node("opponent", opponent_node)
    builder.add_node("fact_checker", fact_checker_node)
    builder.add_node("synthesizer", synthesizer_node)
    builder.add_node("moderator", moderator_node)
    
    # Wire standard edges
    builder.add_edge("background_investigator", "planner")
    # AI comparison returns Command(goto="reporter") to go directly to reporter.
    # This avoids looping through research_team which would trigger researcher repeatedly.
    # It executes all tools internally before routing to reporter.
    #
    # NEW: Separate debate chain:
    # coordinator → debate_planner → human_feedback → debate_orchestrator → debate_team (proponent → opponent → fact_checker → synthesizer → moderator) → debate_orchestrator → reporter
    # debate_orchestrator manages rounds and routes between debate_team and reporter
    #
    # Code planner mode follows structured code development workflow:
    # coordinator → code_planner → human_feedback → research_team → coder/tester (with code/test tools) → reporter
    #
    # Code router: coordinator can route directly to coder for simple code questions
    # coordinator → coder → __end__ (direct response)
    # The coder node determines whether to go to __end__ or research_team based on context
    
    # Wire debate chain edges (debate nodes use Command to route)
    # debate_planner already routes to human_feedback
    # We need to update human_feedback to route to debate_orchestrator for debate mode
    # debate_orchestrator routes to proponent (start of debate team sequence)
    builder.add_edge("proponent", "opponent")
    builder.add_edge("opponent", "fact_checker")
    builder.add_edge("fact_checker", "synthesizer")
    builder.add_edge("synthesizer", "moderator")
    # moderator and debate_orchestrator use Command to route dynamically
    
    builder.add_conditional_edges(
        "research_team",
        continue_to_running_research_team,
        ["planner", "researcher", "analyst", "coder", "tester"],
    )
    builder.add_edge("reporter", END)
    return builder


def build_graph_with_memory():
    """Build and return the agent workflow graph with memory."""
    # use persistent memory to save conversation history
    # TODO: be compatible with SQLite / PostgreSQL
    memory = MemorySaver()

    # build state graph
    builder = _build_base_graph()
    return builder.compile(checkpointer=memory)


def build_graph():
    """Build and return the agent workflow graph without memory."""
    # build state graph
    builder = _build_base_graph()
    return builder.compile()


graph = build_graph()
