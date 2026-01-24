"""
Workflow orchestration patterns for OneSeek

Integrates DeerFlow's multi-agent workflow concepts with OneSeek's existing
LangGraph architecture.

Original concept from: https://github.com/bytedance/deer-flow
Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
SPDX-License-Identifier: MIT
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from deer_flow.agents import create_researcher_agent, create_analyst_agent

logger = logging.getLogger(__name__)


class DeepResearchState(Dict):
    """
    State for deep research workflow.
    
    Extends OneSeek's AgentState with DeerFlow-inspired fields for
    multi-step research processes.
    """
    messages: List[BaseMessage]
    retrieved_docs: List[Dict[str, Any]]
    steps: List[str]
    tool_actions: List[Dict[str, Any]]
    research_plan: Optional[str] = None
    analysis_results: Optional[Dict[str, Any]] = None
    final_report: Optional[str] = None


def create_deep_research_workflow(tools: List[Any]) -> StateGraph:
    """
    Create a multi-agent deep research workflow.
    
    This workflow follows DeerFlow's pattern of specialized agents working
    together:
    1. Researcher agent - gathers information
    2. Analyst agent - synthesizes findings
    3. Reporter - produces final output
    
    Args:
        tools: List of tools available to agents
        
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create specialized agents
    researcher = create_researcher_agent(tools)
    analyst = create_analyst_agent(tools)
    
    # Create workflow graph
    workflow = StateGraph(DeepResearchState)
    
    # Define workflow nodes
    def research_node(state: DeepResearchState) -> DeepResearchState:
        """Research node - gathers information."""
        logger.info("Executing research node")
        state["steps"].append("Gathering information...")
        
        # Use researcher agent to process query
        result = researcher.invoke(state["messages"])
        state["messages"].append(result)
        
        return state
    
    def analyze_node(state: DeepResearchState) -> DeepResearchState:
        """Analysis node - synthesizes information."""
        logger.info("Executing analysis node")
        state["steps"].append("Analyzing results...")
        
        # Use analyst agent to synthesize findings
        result = analyst.invoke(state["messages"])
        state["messages"].append(result)
        state["analysis_results"] = {"content": result.content}
        
        return state
    
    def should_continue(state: DeepResearchState) -> str:
        """Decide if more research is needed."""
        last_message = state["messages"][-1]
        
        # Check if agent wants to use tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        
        # Check if we have analysis results
        if state.get("analysis_results"):
            return "end"
        
        return "analyze"
    
    # Add nodes to graph
    workflow.add_node("research", research_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("tools", ToolNode(tools))
    
    # Set entry point
    workflow.set_entry_point("research")
    
    # Add edges
    workflow.add_conditional_edges(
        "research",
        should_continue,
        {
            "tools": "tools",
            "analyze": "analyze",
            "end": END,
        }
    )
    
    workflow.add_edge("tools", "research")  # Loop back after tool execution
    workflow.add_edge("analyze", END)
    
    return workflow.compile()


def create_simple_agent_workflow(tools: List[Any]) -> StateGraph:
    """
    Create a simplified single-agent workflow.
    
    This is compatible with OneSeek's existing agent_graph.py pattern
    but uses DeerFlow's agent creation approach.
    
    Args:
        tools: List of tools available to the agent
        
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create researcher agent
    agent = create_researcher_agent(tools)
    
    # Create workflow graph
    workflow = StateGraph(DeepResearchState)
    
    def agent_node(state: DeepResearchState) -> DeepResearchState:
        """Main agent node."""
        result = agent.invoke(state["messages"])
        state["messages"].append(result)
        return state
    
    def should_continue(state: DeepResearchState) -> str:
        """Check if tools should be called."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "end"
    
    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    
    # Set entry and edges
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END}
    )
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()
