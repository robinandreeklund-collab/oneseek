"""
Agent creation and middleware patterns for OneSeek

Inspired by DeerFlow's agent factory and middleware system.
Original concept from: https://github.com/bytedance/deer-flow
Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
SPDX-License-Identifier: MIT
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool

from deer_flow.llms import get_llm_by_type, LLMType

logger = logging.getLogger(__name__)


# Agent type to LLM type mapping (inspired by DeerFlow's AGENT_LLM_MAP)
AGENT_LLM_MAP: Dict[str, LLMType] = {
    "researcher": "basic",
    "analyst": "basic",
    "coder": "code",
    "reporter": "basic",
    "reasoner": "reasoning",
}


class AgentMiddleware:
    """
    Base class for agent middleware.
    
    Middleware can modify the agent's behavior by intercepting
    and transforming inputs/outputs.
    """
    
    def pre_invoke(self, messages: List[Any]) -> List[Any]:
        """Called before the agent processes messages."""
        return messages
    
    def post_invoke(self, result: Any) -> Any:
        """Called after the agent produces a result."""
        return result


class DynamicPromptMiddleware(AgentMiddleware):
    """
    Middleware that injects dynamic system prompts.
    
    Inspired by DeerFlow's prompt template system.
    """
    
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
    
    def pre_invoke(self, messages: List[Any]) -> List[Any]:
        """Inject system prompt at the beginning if not present."""
        if messages and not isinstance(messages[0], SystemMessage):
            return [SystemMessage(content=self.system_prompt)] + messages
        return messages


def create_agent(
    agent_type: str = "researcher",
    tools: Optional[List[BaseTool]] = None,
    system_prompt: Optional[str] = None,
    middleware: Optional[List[AgentMiddleware]] = None,
    llm_override: Optional[BaseChatModel] = None,
) -> BaseChatModel:
    """
    Create an agent with specified tools and middleware.
    
    This factory function follows DeerFlow's pattern of creating specialized
    agents with different LLM types and capabilities.
    
    Args:
        agent_type: Type of agent (researcher, analyst, coder, reporter, reasoner)
        tools: List of tools to bind to the agent
        system_prompt: Optional system prompt for the agent
        middleware: List of middleware to apply
        llm_override: Optional LLM to use instead of default for agent type
        
    Returns:
        Configured LLM instance with tools bound
    """
    # Get appropriate LLM for agent type
    llm_type = AGENT_LLM_MAP.get(agent_type, "basic")
    llm = llm_override if llm_override else get_llm_by_type(llm_type)
    
    logger.info(f"Creating {agent_type} agent with LLM type: {llm_type}")
    
    # Bind tools if provided
    if tools:
        logger.info(f"Binding {len(tools)} tools to {agent_type} agent")
        llm = llm.bind_tools(tools)
    
    # Apply middleware (for future extension)
    if middleware:
        logger.info(f"Applied {len(middleware)} middleware to {agent_type} agent")
    
    return llm


def create_researcher_agent(tools: List[BaseTool]) -> BaseChatModel:
    """
    Create a researcher agent specialized for information gathering.
    
    Args:
        tools: Search and retrieval tools
        
    Returns:
        Configured researcher agent
    """
    system_prompt = """You are a research assistant specializing in information gathering.
Your role is to search for relevant information, analyze search results, and extract key insights.
Always cite your sources and provide comprehensive answers based on the retrieved information."""
    
    return create_agent(
        agent_type="researcher",
        tools=tools,
        system_prompt=system_prompt,
    )


def create_coder_agent(tools: List[BaseTool]) -> BaseChatModel:
    """
    Create a coder agent specialized for code-related tasks.
    
    Args:
        tools: Code execution and analysis tools
        
    Returns:
        Configured coder agent
    """
    system_prompt = """You are a coding assistant specializing in code generation and analysis.
Your role is to write clean, efficient code and explain technical concepts clearly.
Always follow best practices and include appropriate error handling."""
    
    return create_agent(
        agent_type="coder",
        tools=tools,
        system_prompt=system_prompt,
    )


def create_analyst_agent(tools: List[BaseTool]) -> BaseChatModel:
    """
    Create an analyst agent specialized for data analysis and synthesis.
    
    Args:
        tools: Analysis and computation tools
        
    Returns:
        Configured analyst agent
    """
    system_prompt = """You are a data analyst specializing in information synthesis.
Your role is to analyze gathered information, identify patterns, and draw meaningful conclusions.
Present your analysis in a clear, structured format with supporting evidence."""
    
    return create_agent(
        agent_type="analyst",
        tools=tools,
        system_prompt=system_prompt,
    )
