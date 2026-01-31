# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT


from dataclasses import field
from typing import Any

from langgraph.graph import MessagesState

from backend.deer_flow.prompts.planner_model import Plan
from backend.deer_flow.rag import Resource


class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    # Runtime Variables
    locale: str = "en-US"
    research_topic: str = ""
    clarified_research_topic: str = (
        ""  # Complete/final clarified topic with all clarification rounds
    )
    observations: list[str] = []
    resources: list[Resource] = []
    plan_iterations: int = 0
    current_plan: Plan | str = None
    final_report: str = ""
    auto_accepted_plan: bool = False
    enable_background_investigation: bool = True
    background_investigation_results: str = None
    
    # Citation metadata collected during research
    # Format: List of citation dictionaries with url, title, description, etc.
    citations: list[dict[str, Any]] = field(default_factory=list)

    # Clarification state tracking (disabled by default)
    enable_clarification: bool = (
        False  # Enable/disable clarification feature (default: False)
    )
    clarification_rounds: int = 0
    clarification_history: list[str] = field(default_factory=list)
    is_clarification_complete: bool = False
    max_clarification_rounds: int = (
        3  # Default: 3 rounds (only used when enable_clarification=True)
    )

    # Workflow control
    goto: str = "planner"  # Default next node
    coder_just_completed: bool = False  # Flag to indicate coder node just completed (for human feedback)
    
    # AI Comparison / Debate OS mode
    enable_ai_comparison: bool = False  # Enable AI comparison mode
    comparison_results: dict[str, Any] | None = None  # Results from AI comparison
    
    # Multi-Round Debate Engine mode
    enable_debate_mode: bool = False  # Enable multi-round debate mode
    debate_results: dict[str, Any] | None = None  # Results from debate (all rounds + voting)
    debate_round: int = 0
    debate_scores: dict[str, int] = field(default_factory=lambda: {"proponent": 0, "opponent": 0})
    debate_knockout: bool = False
    debate_max_rounds: int = 3
    debate_error_count: int = 0
    debate_complete: bool = False
    debate_model_index: int = 0
    debate_model_order: list[str] = field(default_factory=list)
    debate_round_started: bool = False
    external_ai_responses: str = ""
    debate_pending_model: dict[str, Any] | None = None
    debate_model_ids: list[str] = field(default_factory=list)
