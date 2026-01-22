"""
LangGraph agent definition for OneSeek.ai MVP
Implements a simple RAG workflow: retrieve → generate
"""

import os
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.vectorstores import VespaStore
from langchain_community.embeddings import HuggingFaceEmbeddings
from dotenv import load_dotenv

load_dotenv()


class AgentState(TypedDict):
    """State object for the agent workflow"""
    messages: List[Dict[str, str]]
    retrieved_docs: List[Dict[str, Any]]
    steps: List[str]
    final_response: str
    system_prompt: Optional[str]


class OneSeekAgent:
    """OneSeek RAG Agent using LangGraph"""
    
    def __init__(self):
        self.vllm_url = os.getenv("VLLM_URL", "http://localhost:8000/v1")
        self.vllm_model = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ")
        self.vespa_url = os.getenv("VESPA_URL")
        self.vespa_cert = os.getenv("VESPA_CERT_PATH")
        self.vespa_key = os.getenv("VESPA_KEY_PATH")
        
        # Initialize embeddings model
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            base_url=self.vllm_url,
            api_key="EMPTY",
            model=self.vllm_model,
            temperature=float(os.getenv("MODEL_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS", "2048"))
        )
        
        # Initialize Vespa retriever if configured
        self.retriever = None
        if self.vespa_url and self.vespa_cert and self.vespa_key:
            try:
                self.retriever = self._init_vespa_retriever()
            except Exception as e:
                print(f"Warning: Could not initialize Vespa retriever: {e}")
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _init_vespa_retriever(self):
        """Initialize Vespa retriever with proper configuration"""
        from pyvespa import Vespa
        
        # Connect to Vespa
        vespa_app = Vespa(
            url=self.vespa_url,
            cert=self.vespa_cert,
            key=self.vespa_key
        )
        
        # Create VespaStore (simplified - in production, use proper configuration)
        # Note: This is a simplified version; actual implementation may vary
        # based on your Vespa schema
        return vespa_app
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("generate", self._generate_node)
        
        # Add edges
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile()
    
    def _retrieve_node(self, state: AgentState) -> AgentState:
        """Retrieve relevant documents from Vespa"""
        steps = state.get("steps", [])
        steps.append("Retrieving relevant documents from Vespa...")
        
        retrieved_docs = []
        
        if not self.retriever:
            steps.append("Vespa retriever not configured - skipping retrieval")
            return {
                **state,
                "retrieved_docs": retrieved_docs,
                "steps": steps
            }
        
        try:
            # Get the last user message
            messages = state.get("messages", [])
            if messages:
                last_message = messages[-1]
                query = last_message.get("content", "")
                
                # Query Vespa
                # This is simplified - actual implementation depends on your Vespa schema
                from pyvespa.application import Vespa
                
                yql = f"""
                    select title, content from rag 
                    where userQuery() 
                    limit 6
                """
                
                response = self.retriever.query(
                    yql=yql,
                    query=query
                )
                
                # Extract documents from response
                if hasattr(response, 'hits'):
                    for hit in response.hits[:6]:
                        doc = {
                            "title": hit.get("fields", {}).get("title", ""),
                            "content": hit.get("fields", {}).get("content", ""),
                            "relevance": hit.get("relevance", 0)
                        }
                        retrieved_docs.append(doc)
                
                steps.append(f"Retrieved {len(retrieved_docs)} documents")
        
        except Exception as e:
            steps.append(f"Error during retrieval: {str(e)}")
            print(f"Retrieval error: {e}")
        
        return {
            **state,
            "retrieved_docs": retrieved_docs,
            "steps": steps
        }
    
    def _generate_node(self, state: AgentState) -> AgentState:
        """Generate response using LLM with retrieved context"""
        steps = state.get("steps", [])
        steps.append("Generating response with LLM...")
        
        messages = state.get("messages", [])
        retrieved_docs = state.get("retrieved_docs", [])
        custom_system_prompt = state.get("system_prompt")
        
        # Build context from retrieved documents
        context = ""
        if retrieved_docs:
            context = "### Retrieved Context:\n\n"
            for i, doc in enumerate(retrieved_docs, 1):
                context += f"**Source {i}: {doc.get('title', 'Untitled')}**\n"
                context += f"{doc.get('content', '')}\n\n"
            context += "---\n\n"
        
        # Build chat history
        chat_messages = []
        
        # System message with context
        # Use custom system prompt if provided, otherwise use default
        if custom_system_prompt:
            system_content = custom_system_prompt
        else:
            system_content = (
                "You are a helpful AI assistant. "
                "Use the following retrieved context to enhance your answers. "
                "If the context is relevant, incorporate it naturally into your response. "
                "If the context is not relevant, answer based on your knowledge."
            )
        
        if context:
            system_content += f"\n\n{context}"
        
        chat_messages.append(SystemMessage(content=system_content))
        
        # Add chat history
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                chat_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                chat_messages.append(AIMessage(content=content))
        
        # Generate response
        try:
            response = self.llm.invoke(chat_messages)
            final_response = response.content
            steps.append("Response generated successfully")
        except Exception as e:
            final_response = f"Error generating response: {str(e)}"
            steps.append(f"Error during generation: {str(e)}")
            print(f"Generation error: {e}")
        
        return {
            **state,
            "final_response": final_response,
            "steps": steps
        }
    
    def _generate_node_streaming(self, state: AgentState, callback) -> AgentState:
        """Generate response with streaming support"""
        steps = state.get("steps", [])
        steps.append("Generating response with LLM (streaming)...")
        callback("step", "Generating response with LLM (streaming)...")
        
        messages = state.get("messages", [])
        retrieved_docs = state.get("retrieved_docs", [])
        custom_system_prompt = state.get("system_prompt")
        
        # Build context from retrieved documents
        context = ""
        if retrieved_docs:
            context = "### Retrieved Context:\n\n"
            for i, doc in enumerate(retrieved_docs, 1):
                context += f"**Source {i}: {doc.get('title', 'Untitled')}**\n"
                context += f"{doc.get('content', '')}\n\n"
            context += "---\n\n"
        
        # Build chat history
        chat_messages = []
        
        # System message with context
        # Use custom system prompt if provided, otherwise use default
        if custom_system_prompt:
            system_content = custom_system_prompt
        else:
            system_content = (
                "You are a helpful AI assistant. "
                "Use the following retrieved context to enhance your answers. "
                "If the context is relevant, incorporate it naturally into your response. "
                "If the context is not relevant, answer based on your knowledge."
            )
        
        if context:
            system_content += f"\n\n{context}"
        
        chat_messages.append(SystemMessage(content=system_content))
        
        # Add chat history
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                chat_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                chat_messages.append(AIMessage(content=content))
        
        # Generate response with streaming
        final_response = ""
        try:
            for chunk in self.llm.stream(chat_messages):
                token = chunk.content
                if token:
                    final_response += token
                    callback("token", token)
            steps.append("Response generated successfully")
        except Exception as e:
            final_response = f"Error generating response: {str(e)}"
            steps.append(f"Error during generation: {str(e)}")
            print(f"Generation error: {e}")
        
        return {
            **state,
            "final_response": final_response,
            "steps": steps
        }
    
    def run(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Run the agent workflow (non-streaming)"""
        initial_state: AgentState = {
            "messages": messages,
            "retrieved_docs": [],
            "steps": [],
            "final_response": "",
            "system_prompt": system_prompt
        }
        
        # Execute the graph
        final_state = self.graph.invoke(initial_state)
        
        return {
            "content": final_state.get("final_response", ""),
            "retrieved": final_state.get("retrieved_docs", []),
            "steps": final_state.get("steps", [])
        }
    
    def run_with_streaming(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Run the agent workflow with streaming support"""
        tokens = []
        steps_list = []
        retrieved_docs = []
        
        def callback(event_type: str, content: Any):
            if event_type == "token":
                tokens.append(content)
            elif event_type == "step":
                steps_list.append(content)
        
        # Step 1: Retrieve documents
        initial_state: AgentState = {
            "messages": messages,
            "retrieved_docs": [],
            "steps": [],
            "final_response": "",
            "system_prompt": system_prompt
        }
        
        # Run retrieve node
        state_after_retrieve = self._retrieve_node(initial_state)
        retrieved_docs = state_after_retrieve.get("retrieved_docs", [])
        steps_list.extend(state_after_retrieve.get("steps", []))
        
        # Step 2: Generate with streaming
        state_after_generate = self._generate_node_streaming(state_after_retrieve, callback)
        steps_list.extend([s for s in state_after_generate.get("steps", []) if s not in steps_list])
        
        return {
            "content": state_after_generate.get("final_response", ""),
            "retrieved": retrieved_docs,
            "steps": steps_list,
            "tokens": tokens
        }


# Singleton instance
_agent_instance = None


def get_agent() -> OneSeekAgent:
    """Get or create the agent instance"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = OneSeekAgent()
    return _agent_instance
