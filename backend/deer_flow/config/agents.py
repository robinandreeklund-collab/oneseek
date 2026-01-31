# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import Literal

# Define available LLM types
LLMType = Literal["basic", "reasoning", "vision", "code"]

# Define agent-LLM mapping
AGENT_LLM_MAP: dict[str, LLMType] = {
    "coordinator": "basic",
    "planner": "basic",
    "researcher": "basic",
    "analyst": "basic",
    "coder": "basic",
    "code_researcher": "basic",
    "code_architect": "basic",
    "code_reviewer": "basic",
    "code_refiner": "basic",
    "code_tester": "basic",
    "tester": "basic",
    "reporter": "basic",
    "podcast_script_writer": "basic",
    "ppt_composer": "basic",
    "prose_writer": "basic",
    "prompt_enhancer": "basic",
    "ai_comparison": "basic",
    "debate": "basic",
    "debate_planner": "basic",
    "code_planner": "basic",
    # Debate chain agents (using real external AI models)
    "debate_orchestrator": "basic",
    "external_ai_caller": "basic",  # Calls Grok, Gemini, ChatGPT, DeepSeek
    "fact_checker": "basic",
    "synthesizer": "basic",
    "moderator": "basic",
}
