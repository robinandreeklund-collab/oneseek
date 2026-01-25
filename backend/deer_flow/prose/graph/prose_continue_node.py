# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from backend.deer_flow.config.agents import AGENT_LLM_MAP
from backend.deer_flow.llms.llm import get_llm_by_type
from backend.deer_flow.prompts.template import get_prompt_template
from backend.deer_flow.prose.graph.state import ProseState

logger = logging.getLogger(__name__)


def prose_continue_node(state: ProseState):
    logger.info("Generating prose continue content...")
    model = get_llm_by_type(AGENT_LLM_MAP["prose_writer"])
    prose_content = model.invoke(
        [
            SystemMessage(content=get_prompt_template("prose/prose_continue")),
            HumanMessage(content=state["content"]),
        ],
    )
    return {"output": prose_content.content}
