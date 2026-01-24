"""
FastAPI backend for OneSeek.ai MVP
Provides chat endpoint that orchestrates RAG workflow via LangGraph
with streaming support as default and multi-tool search capabilities
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, AsyncIterator, Any
import uvicorn
import json
import asyncio
import os
from agent import get_agent
from agent_graph import get_agent_graph

app = FastAPI(
    title="OneSeek.ai API",
    description="RAG-enhanced chat API with LangGraph orchestration and multi-tool search",
    version="0.3.0"
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    """Single chat message"""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Request model for /chat endpoint"""
    messages: List[Message]
    stream: Optional[bool] = True  # Streaming is default
    system_prompt: Optional[str] = None  # Custom system prompt from frontend
    temperature: Optional[float] = None  # Model temperature
    model: Optional[str] = None  # Model selection
    enable_thinking: Optional[bool] = False  # Enable thinking mode (Qwen models)
    use_tools: Optional[bool] = True  # Enable multi-tool search (default: True)


class RetrievedDoc(BaseModel):
    """Retrieved document from search tools"""
    title: str
    content: str
    url: Optional[str] = None
    relevance: Optional[float] = None
    source: Optional[str] = None  # Which tool provided this result


class ChatResponse(BaseModel):
    """Response model for /chat endpoint"""
    content: str
    retrieved: List[RetrievedDoc]
    steps: List[str]


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "OneSeek.ai API",
        "version": "0.3.0",
        "features": ["multi-tool-search", "streaming", "rag"]
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    # Check if USE_TOOLS environment variable is set
    use_tools_default = os.getenv("USE_TOOLS", "true").lower() == "true"
    
    if use_tools_default:
        agent = get_agent_graph()
        return {
            "status": "ok",
            "mode": "multi-tool",
            "vllm_url": agent.vllm_url,
            "vllm_model": agent.vllm_model,
            "tools_available": ["tavily_search", "duckduckgo_search", "vespa_search"],
            "tavily_configured": bool(os.getenv("TAVILY_API_KEY")),
            "vespa_configured": bool(os.getenv("VESPA_URL"))
        }
    else:
        agent = get_agent()
        return {
            "status": "ok",
            "mode": "legacy-rag",
            "vllm_url": agent.vllm_url,
            "vllm_model": agent.vllm_model,
            "vespa_configured": agent.retriever is not None,
            "vespa_url": agent.vespa_url if agent.vespa_url else "not configured"
        }


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint with streaming support (default) and multi-tool search
    
    Accepts a list of messages and returns an AI response enhanced with
    multi-tool search (Tavily, DuckDuckGo, Vespa). Streams the response by default for better UX.
    
    Set use_tools=False to use legacy RAG-only mode.
    """
    try:
        # Convert Pydantic models to dicts for the agent
        messages = [msg.dict() for msg in request.messages]
        
        # Determine which agent to use
        use_tools = request.use_tools if request.use_tools is not None else True
        
        if request.stream:
            # Return streaming response in AI SDK format
            return StreamingResponse(
                stream_chat_response(
                    messages, 
                    request.system_prompt, 
                    request.enable_thinking,
                    use_tools
                ),
                media_type="text/plain; charset=utf-8"
            )
        else:
            # Non-streaming response (legacy support)
            if use_tools:
                agent = get_agent_graph()
            else:
                agent = get_agent()
            
            result = agent.run(
                messages, 
                system_prompt=request.system_prompt, 
                enable_thinking=request.enable_thinking
            )
            
            retrieved_docs = [
                RetrievedDoc(**doc) for doc in result.get("retrieved", [])
            ]
            
            return ChatResponse(
                content=result.get("content", ""),
                retrieved=retrieved_docs,
                steps=result.get("steps", [])
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )


async def stream_chat_response(
    messages: List[Dict[str, str]], 
    system_prompt: Optional[str] = None, 
    enable_thinking: Optional[bool] = False,
    use_tools: bool = True
) -> AsyncIterator[str]:
    """
    Stream chat response in Vercel AI SDK compatible format with real-time tool action updates
    
    Streams text tokens, tool actions, and metadata for the frontend in real-time.
    Uses newline-delimited JSON format expected by AI SDK.
    
    Args:
        messages: List of message dictionaries
        system_prompt: Optional custom system prompt
        enable_thinking: Enable thinking mode for Qwen models
        use_tools: Use multi-tool agent (True) or legacy RAG agent (False)
    """
    import logging
    import queue
    import threading
    logger = logging.getLogger(__name__)
    
    try:
        # Select appropriate agent
        if use_tools:
            agent = get_agent_graph()
            logger.info("Using multi-tool agent with real-time streaming")
        else:
            agent = get_agent()
            logger.info("Using legacy RAG agent")
        
        logger.info(f"Running agent with {len(messages)} messages")
        
        # Create a queue for real-time updates
        update_queue = queue.Queue()
        result_container = {"result": None, "error": None}
        
        # Custom callback that puts updates in the queue
        def queue_callback(event_type: str, content: Any):
            update_queue.put((event_type, content))
        
        # Run agent in background thread with queue callback
        def run_agent():
            try:
                result = agent.run_with_streaming_realtime(
                    messages,
                    system_prompt=system_prompt,
                    enable_thinking=enable_thinking,
                    realtime_callback=queue_callback
                )
                result_container["result"] = result
            except Exception as e:
                result_container["error"] = e
            finally:
                update_queue.put(("done", None))
        
        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()
        
        # Stream updates from queue in real-time
        tool_actions_list = []
        while True:
            try:
                event_type, content = update_queue.get(timeout=30)
                
                if event_type == "done":
                    break
                elif event_type == "tool_action":
                    # Stream tool action update immediately
                    tool_actions_list.append(content)
                    metadata = {
                        "tool_actions": tool_actions_list,
                        "live_update": True
                    }
                    yield f"2:{json.dumps([metadata])}\n"
                    await asyncio.sleep(0.001)
                    logger.info(f"Streamed tool action: {content.get('display_name')} - {content.get('status')}")
                    
            except queue.Empty:
                logger.warning("Queue timeout - no updates received")
                break
        
        # Wait for thread to complete
        thread.join(timeout=5)
        
        # Check for errors
        if result_container["error"]:
            raise result_container["error"]
        
        result = result_container["result"]
        if not result:
            raise ValueError("Agent returned empty result")
        
        logger.info(f"Agent result: {len(result.get('tokens', []))} tokens, {len(result.get('steps', []))} steps")
        
        # Send final metadata
        retrieved_docs = result.get("retrieved", [])
        final_tool_actions = result.get("tool_actions", [])
        metadata = {
            "steps": result.get("steps", []),
            "retrieved": retrieved_docs,
            "source_count": len(retrieved_docs),
            "tool_actions": final_tool_actions,
            "live_update": False
        }
        
        yield f"2:{json.dumps([metadata])}\n"
        
        # Stream LLM response tokens
        tokens = result.get("tokens", [])
        if tokens:
            for token in tokens:
                yield f"0:{json.dumps(token)}\n"
                await asyncio.sleep(0.001)
        else:
            content = result.get("content", "")
            if content:
                chunk_size = 100
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i + chunk_size]
                    yield f"0:{json.dumps(chunk)}\n"
                    await asyncio.sleep(0.001)
        
        # Send final done message
        yield "d:\n"
        logger.info("Streaming completed successfully")
        
    except Exception as e:
        # Send error in AI SDK format
        import traceback
        error_detail = traceback.format_exc()
        error_msg = f"Error: {str(e)}\n\nDetails:\n{error_detail}"
        logger.error(f"Streaming error: {error_msg}")
        yield f"3:{json.dumps(error_msg)}\n"
        yield "d:\n"


@app.get("/config")
async def get_config():
    """Get current configuration (for debugging)"""
    use_tools_default = os.getenv("USE_TOOLS", "true").lower() == "true"
    
    if use_tools_default:
        agent = get_agent_graph()
        return {
            "mode": "multi-tool",
            "vllm_url": agent.vllm_url,
            "vllm_model": agent.vllm_model,
            "tools_available": ["tavily_search", "duckduckgo_search", "vespa_search"],
            "tavily_configured": bool(os.getenv("TAVILY_API_KEY")),
            "vespa_configured": bool(os.getenv("VESPA_URL")),
            "embeddings_model": "sentence-transformers/all-MiniLM-L6-v2"
        }
    else:
        agent = get_agent()
        return {
            "mode": "legacy-rag",
            "vllm_url": agent.vllm_url,
            "vllm_model": agent.vllm_model,
            "vespa_configured": agent.retriever is not None,
            "embeddings_model": "sentence-transformers/all-MiniLM-L6-v2"
        }


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
