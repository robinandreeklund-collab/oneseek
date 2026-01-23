"""
LangGraph agent with tool-calling workflow for OneSeek.ai
Implements agent → tools → conditional edge → loops to final answers
"""

import os
from typing import TypedDict, List, Dict, Any, Optional, Literal, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage, BaseMessage
from dotenv import load_dotenv
import operator

from tools import AVAILABLE_TOOLS

load_dotenv()


class AgentState(TypedDict):
    """State object for the agent workflow with tool calling support"""
    messages: Annotated[List[BaseMessage], operator.add]
    retrieved_docs: List[Dict[str, Any]]
    steps: List[str]
    system_prompt: Optional[str]
    enable_thinking: Optional[bool]


class OneSeekGraphAgent:
    """OneSeek Agent using LangGraph with tool-calling workflow"""
    
    def __init__(self):
        self.vllm_url = os.getenv("VLLM_URL", "http://localhost:8000/v1")
        self.vllm_model = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ")
        
        # Initialize LLM with tool binding
        self.llm = ChatOpenAI(
            base_url=self.vllm_url,
            api_key="EMPTY",
            model=self.vllm_model,
            temperature=float(os.getenv("MODEL_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS", "2048"))
        )
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(AVAILABLE_TOOLS)
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow with conditional tool calling"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", ToolNode(AVAILABLE_TOOLS))
        
        # Add edges
        workflow.set_entry_point("agent")
        
        # Conditional edge: if agent calls tools, go to tools node; otherwise end
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )
        
        # After tools execute, always go back to agent
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    def _agent_node(self, state: AgentState) -> Dict[str, Any]:
        """Agent node - decides whether to use tools or provide final answer"""
        messages = state["messages"]
        system_prompt = state.get("system_prompt")
        enable_thinking = state.get("enable_thinking", False)
        steps = state.get("steps", [])
        
        # Build system message
        if system_prompt:
            system_content = system_prompt
        else:
            system_content = (
                "You are a helpful AI assistant for OneSeek.ai. "
                "You have access to multiple search tools:\n"
                "- tavily_search: Paid, robust, accurate web search with concise summaries\n"
                "- duckduckgo_search: Free, simple, anonymous web search\n"
                "- vespa_search: Local/cloud RAG with embeddings and hybrid searching\n\n"
                "When the user asks a question:\n"
                "1. Determine if you need to search for information\n"
                "2. If needed, call one or multiple tools in parallel\n"
                "3. Use the search results to provide a comprehensive, factual answer in Swedish\n"
                "4. Always cite your sources appropriately\n"
                "5. If no search is needed, answer directly based on your knowledge\n\n"
                "Provide transparent, well-sourced responses."
            )
        
        # Add thinking instructions if enabled
        if enable_thinking:
            system_content = (
                "Du måste tänka på svenska. Använd <think> taggar för att visa ditt resonemang på svenska. "
                "Think in Swedish and show your reasoning in <think> tags.\n\n"
                + system_content
            )
        
        # Add system message if not already present
        chat_messages = []
        if not messages or not isinstance(messages[0], SystemMessage):
            chat_messages.append(SystemMessage(content=system_content))
        
        chat_messages.extend(messages)
        
        # Log step
        if not any("Analyzing query" in s for s in steps):
            steps.append("Analyzing query and determining if tools are needed...")
        
        # Call LLM with tools
        response = self.llm_with_tools.invoke(chat_messages)
        
        # Check if tools were called
        if response.tool_calls:
            tool_names = [tc["name"] for tc in response.tool_calls]
            steps.append(f"Calling tools: {', '.join(tool_names)}")
        else:
            steps.append("Generating final response...")
        
        return {
            "messages": [response],
            "steps": steps
        }
    
    def _should_continue(self, state: AgentState) -> Literal["continue", "end"]:
        """Determine if we should continue to tools or end"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If the last message has tool calls, continue to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        
        # Otherwise, we're done
        return "end"
    
    def _agent_node_streaming(self, state: AgentState, callback) -> Dict[str, Any]:
        """Agent node with streaming support"""
        messages = state["messages"]
        system_prompt = state.get("system_prompt")
        enable_thinking = state.get("enable_thinking", False)
        steps = state.get("steps", [])
        
        # Build system message
        if system_prompt:
            system_content = system_prompt
        else:
            system_content = (
                "You are a helpful AI assistant for OneSeek.ai. "
                "You have access to multiple search tools:\n"
                "- tavily_search: Paid, robust, accurate web search with concise summaries\n"
                "- duckduckgo_search: Free, simple, anonymous web search\n"
                "- vespa_search: Local/cloud RAG with embeddings and hybrid searching\n\n"
                "When the user asks a question:\n"
                "1. Determine if you need to search for information\n"
                "2. If needed, call one or multiple tools in parallel\n"
                "3. Use the search results to provide a comprehensive, factual answer in Swedish\n"
                "4. Always cite your sources appropriately\n"
                "5. If no search is needed, answer directly based on your knowledge\n\n"
                "Provide transparent, well-sourced responses."
            )
        
        # Add thinking instructions if enabled
        if enable_thinking:
            system_content = (
                "Du måste tänka på svenska. Använd <think> taggar för att visa ditt resonemang på svenska. "
                "Think in Swedish and show your reasoning in <think> tags.\n\n"
                + system_content
            )
        
        # Add system message if not already present
        chat_messages = []
        if not messages or not isinstance(messages[0], SystemMessage):
            chat_messages.append(SystemMessage(content=system_content))
        
        chat_messages.extend(messages)
        
        # Check if this is a final generation (no tool calls in last message)
        last_message = messages[-1] if messages else None
        is_final_generation = (
            last_message and 
            isinstance(last_message, ToolMessage) or
            (isinstance(last_message, AIMessage) and not last_message.tool_calls)
        )
        
        # If this is final generation, stream the response
        # Check if last_message is AIMessage before accessing tool_calls
        if is_final_generation or (last_message and isinstance(last_message, AIMessage) and not last_message.tool_calls):
            steps.append("Generating final response (streaming)...")
            callback("step", "Generating final response (streaming)...")
            
            full_content = ""
            for chunk in self.llm.stream(chat_messages):
                token = chunk.content
                if token:
                    full_content += token
                    callback("token", token)
            
            response = AIMessage(content=full_content)
            steps.append("Response generated successfully")
        else:
            # Not final generation, check for tool calls
            steps.append("Analyzing query and determining if tools are needed...")
            callback("step", "Analyzing query and determining if tools are needed...")
            
            response = self.llm_with_tools.invoke(chat_messages)
            
            # Check if tools were called
            if response.tool_calls:
                tool_names = [tc["name"] for tc in response.tool_calls]
                steps.append(f"Calling tools: {', '.join(tool_names)}")
                callback("step", f"Calling tools: {', '.join(tool_names)}")
        
        return {
            "messages": [response],
            "steps": steps
        }
    
    def run(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None, 
            enable_thinking: Optional[bool] = False) -> Dict[str, Any]:
        """Run the agent workflow (non-streaming)"""
        # Convert dict messages to LangChain messages
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
        
        initial_state: AgentState = {
            "messages": lc_messages,
            "retrieved_docs": [],
            "steps": [],
            "system_prompt": system_prompt,
            "enable_thinking": enable_thinking
        }
        
        # Execute the graph
        final_state = self.graph.invoke(initial_state)
        
        # Extract final response
        final_message = final_state["messages"][-1]
        final_response = final_message.content if hasattr(final_message, "content") else ""
        
        # Collect retrieved docs from tool messages
        retrieved_docs = []
        for msg in final_state["messages"]:
            if isinstance(msg, ToolMessage):
                try:
                    import json
                    tool_result = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                    if isinstance(tool_result, list):
                        retrieved_docs.extend(tool_result)
                except:
                    pass
        
        return {
            "content": final_response,
            "retrieved": retrieved_docs,
            "steps": final_state.get("steps", [])
        }
    
    def run_with_streaming(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None, 
                          enable_thinking: Optional[bool] = False) -> Dict[str, Any]:
        """Run the agent workflow with streaming support"""
        tokens = []
        steps_list = []
        retrieved_docs = []
        
        def callback(event_type: str, content: Any):
            if event_type == "token":
                tokens.append(content)
            elif event_type == "step":
                steps_list.append(content)
        
        # Convert dict messages to LangChain messages
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
        
        # Run the graph with streaming
        # This is a simplified version - in a full implementation, you'd stream through the graph
        current_state: AgentState = {
            "messages": lc_messages,
            "retrieved_docs": [],
            "steps": [],
            "system_prompt": system_prompt,
            "enable_thinking": enable_thinking
        }
        
        max_iterations = 5  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Run agent node
            agent_result = self._agent_node_streaming(current_state, callback)
            current_state["messages"] = current_state.get("messages", []) + agent_result["messages"]
            current_state["steps"] = agent_result["steps"]
            
            # Check if we should continue
            if self._should_continue(current_state) == "end":
                break
            
            # Execute tools
            steps_list.append("Executing tools...")
            callback("step", "Executing tools...")
            
            tool_node = ToolNode(AVAILABLE_TOOLS)
            tool_result = tool_node.invoke(current_state)
            
            # Add tool messages to state
            current_state["messages"] = current_state.get("messages", []) + tool_result["messages"]
            
            # Extract retrieved docs from tool messages
            for msg in tool_result["messages"]:
                if isinstance(msg, ToolMessage):
                    try:
                        import json
                        tool_content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                        if isinstance(tool_content, list):
                            retrieved_docs.extend(tool_content)
                    except:
                        pass
            
            steps_list.append(f"Tools executed, retrieved {len(retrieved_docs)} documents")
            callback("step", f"Tools executed, retrieved {len(retrieved_docs)} documents")
        
        # Get final response
        final_message = current_state["messages"][-1]
        final_response = final_message.content if hasattr(final_message, "content") else ""
        
        return {
            "content": final_response,
            "retrieved": retrieved_docs,
            "steps": steps_list,
            "tokens": tokens
        }


# Singleton instance
_agent_graph_instance = None


def get_agent_graph() -> OneSeekGraphAgent:
    """Get or create the agent graph instance"""
    global _agent_graph_instance
    if _agent_graph_instance is None:
        _agent_graph_instance = OneSeekGraphAgent()
    return _agent_graph_instance
