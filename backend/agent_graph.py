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
        
        # Filter tools to only include configured ones
        self.available_tools = self._get_configured_tools()
        
        # Bind only configured tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.available_tools)
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _get_configured_tools(self):
        """Get list of tools that are properly configured"""
        from tools import AVAILABLE_TOOLS
        configured_tools = []
        
        for tool in AVAILABLE_TOOLS:
            tool_name = tool.name
            
            # Skip DuckDuckGo due to rate limiting issues
            if tool_name == "duckduckgo_search":
                continue
            
            # Check if Tavily is configured
            if tool_name == "tavily_search":
                if os.getenv("TAVILY_API_KEY"):
                    configured_tools.append(tool)
                continue
            
            # Check if Vespa is configured
            if tool_name == "vespa_search":
                if os.getenv("VESPA_URL") and os.getenv("VESPA_CERT_PATH") and os.getenv("VESPA_KEY_PATH"):
                    configured_tools.append(tool)
                continue
            
            # browse_page and smhi_weather_forecast are always available (no config needed)
            if tool_name in ["browse_page", "smhi_weather_forecast"]:
                configured_tools.append(tool)
                continue
        
        return configured_tools
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow with conditional tool calling"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", ToolNode(self.available_tools))
        
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
    
    def _build_system_prompt(self, custom_prompt: Optional[str] = None, enable_thinking: bool = False) -> str:
        """Build system prompt with tool descriptions - extracted to avoid duplication"""
        if custom_prompt:
            system_content = custom_prompt
        else:
            # Build tool descriptions dynamically based on configured tools
            tool_descriptions = []
            for tool in self.available_tools:
                if tool.name == "tavily_search":
                    tool_descriptions.append("- tavily_search: Paid, robust, accurate web search with concise summaries")
                elif tool.name == "duckduckgo_search":
                    tool_descriptions.append("- duckduckgo_search: Free, simple, anonymous web search")
                elif tool.name == "vespa_search":
                    tool_descriptions.append("- vespa_search: Local/cloud RAG with embeddings and hybrid searching")
                elif tool.name == "browse_page":
                    tool_descriptions.append("- browse_page: Fetch and read content from any webpage URL with automatic intelligent chunking for large pages")
                elif tool.name == "smhi_weather_forecast":
                    tool_descriptions.append("- smhi_weather_forecast: Get real-time weather forecast from SMHI for locations in Sweden")
            
            tools_text = "\n".join(tool_descriptions) if tool_descriptions else "No tools available."
            
            system_content = (
                "You are a helpful AI assistant for OneSeek.ai. "
                "Du svarar ALLTID på flytande svenska (Swedish). "
                f"You have access to the following tools:\n{tools_text}\n\n"
                "When the user asks a question:\n"
                "1. Determine if you need to search for information or browse specific pages\n"
                "2. For weather questions about locations in Sweden, ALWAYS use smhi_weather_forecast for accurate, real-time data\n"
                "3. If needed, call one or multiple tools IN PARALLEL for efficiency\n"
                "4. You can combine web search with browse_page to read specific articles\n"
                "5. The browse_page tool automatically chunks large pages into semantic sections with overlap\n"
                "   - Small pages return 1 chunk, large pages return multiple chunks\n"
                "   - When you receive multiple chunks from browse_page, analyze ALL chunks to get complete understanding\n"
                "   - The chunks are designed for parallel processing - vLLM batches them for throughput\n"
                "6. Use the results to provide a comprehensive, factual answer IN SWEDISH\n"
                "7. Always cite your sources with URLs\n"
                "8. If no search is needed, answer directly based on your knowledge\n\n"
                "Important: Do NOT show your thinking process or internal reasoning to the user. "
                "Only provide the final answer with source citations.\n\n"
                "Var transparent och ge välgrundade svar på svenska (Be transparent and provide well-sourced responses in Swedish)."
            )
        
        # Add thinking instructions if enabled
        if enable_thinking:
            system_content = (
                "Du måste tänka på svenska. Använd <think> taggar för att visa ditt resonemang på svenska. "
                "Think in Swedish and show your reasoning in <think> tags.\n\n"
                + system_content
            )
        
        return system_content
    
    def _agent_node(self, state: AgentState) -> Dict[str, Any]:
        """Agent node - decides whether to use tools or provide final answer"""
        messages = state["messages"]
        system_prompt = state.get("system_prompt")
        enable_thinking = state.get("enable_thinking", False)
        steps = state.get("steps", [])
        
        # Build system message using helper method
        system_content = self._build_system_prompt(system_prompt, enable_thinking)
        
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
        
        # Build system message using helper method
        system_content = self._build_system_prompt(system_prompt, enable_thinking)
        
        # Add system message if not already present
        chat_messages = []
        if not messages or not isinstance(messages[0], SystemMessage):
            chat_messages.append(SystemMessage(content=system_content))
        
        chat_messages.extend(messages)
        
        # Check if this is a final generation (after tools have been called)
        # Final generation happens when the last message is a ToolMessage (tools just executed)
        last_message = messages[-1] if messages else None
        is_after_tool_execution = last_message and isinstance(last_message, ToolMessage)
        
        # If we're after tool execution, stream the final response
        if is_after_tool_execution:
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
            # First pass or need to check for tool calls
            steps.append("Analyzing query and determining if tools are needed...")
            callback("step", "Analyzing query and determining if tools are needed...")
            
            # IMPORTANT: Use llm_with_tools to allow tool calling
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
        import logging
        logger = logging.getLogger(__name__)
        
        tokens = []
        steps_list = []
        retrieved_docs = []
        
        def callback(event_type: str, content: Any):
            if event_type == "token":
                tokens.append(content)
                logger.debug(f"Token collected: {content[:50] if len(content) > 50 else content}")
            elif event_type == "step":
                steps_list.append(content)
                logger.info(f"Step: {content}")
        
        # Convert dict messages to LangChain messages
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
        
        logger.info(f"Starting workflow with {len(lc_messages)} messages")
        
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
            logger.info(f"Iteration {iteration}")
            
            # Run agent node
            agent_result = self._agent_node_streaming(current_state, callback)
            current_state["messages"] = current_state.get("messages", []) + agent_result["messages"]
            current_state["steps"] = agent_result["steps"]
            
            last_msg = current_state["messages"][-1]
            logger.info(f"Agent returned: {type(last_msg).__name__}, has tool_calls: {hasattr(last_msg, 'tool_calls') and bool(last_msg.tool_calls)}")
            
            # Check if we should continue
            if self._should_continue(current_state) == "end":
                logger.info("Workflow ending - no more tool calls")
                break
            
            # Execute tools
            logger.info("Executing tools...")
            steps_list.append("Executing tools...")
            callback("step", "Executing tools...")
            
            tool_node = ToolNode(self.available_tools)
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
        
        logger.info(f"Workflow complete. Tokens collected: {len(tokens)}, Final response length: {len(final_response)}")
        
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
