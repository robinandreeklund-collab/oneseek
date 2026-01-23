"""
FastAPI backend for OneSeek.ai MVP
Provides chat endpoint that orchestrates RAG workflow via LangGraph
with streaming support as default and multi-tool search capabilities
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, AsyncIterator
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
    """Retrieved document from Vespa"""
    title: str
    content: str
    relevance: Optional[float] = None


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
    Stream chat response in Vercel AI SDK compatible format
    
    Streams text tokens and metadata for the frontend.
    Uses newline-delimited JSON format expected by AI SDK.
    
    Args:
        messages: List of message dictionaries
        system_prompt: Optional custom system prompt
        enable_thinking: Enable thinking mode for Qwen models
        use_tools: Use multi-tool agent (True) or legacy RAG agent (False)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Select appropriate agent
        if use_tools:
            agent = get_agent_graph()
            logger.info("Using multi-tool agent")
        else:
            agent = get_agent()
            logger.info("Using legacy RAG agent")
        
        # Run agent to get result with streaming
        logger.info(f"Running agent with {len(messages)} messages")
        result = await asyncio.to_thread(
            agent.run_with_streaming, 
            messages, 
            system_prompt=system_prompt, 
            enable_thinking=enable_thinking
        )
        
        # Ensure result is valid
        if not result:
            raise ValueError("Agent returned empty result")
        
        logger.info(f"Agent result: {len(result.get('tokens', []))} tokens, {len(result.get('steps', []))} steps")
        
        # Send metadata about steps and retrieved docs first (as annotations)
        metadata = {
            "steps": result.get("steps", []),
            "retrieved": result.get("retrieved", [])
        }
        
        # Stream annotations/data first
        if metadata["steps"] or metadata["retrieved"]:
            # Send as data annotation (AI SDK format)
            yield f"2:{json.dumps([metadata])}\n"
        
        # Stream LLM response tokens as text chunks
        # Format: "0:{token_text}\n" where 0 indicates text chunk
        tokens = result.get("tokens", [])
        if tokens:
            for token in tokens:
                yield f"0:{json.dumps(token)}\n"
                await asyncio.sleep(0.001)  # Small delay for smoother streaming
        else:
            # If no tokens were streamed, send the full content as one chunk
            content = result.get("content", "")
            if content:
                logger.warning(f"No tokens, sending full content: {len(content)} chars")
                yield f"0:{json.dumps(content)}\n"
        
        # Send final done message
        yield "d:\n"
        logger.info("Streaming completed successfully")
        
    except Exception as e:
        # Send error in AI SDK format with more detail
        import traceback
        error_detail = traceback.format_exc()
        error_msg = f"Error: {str(e)}\n\nDetails:\n{error_detail}"
        logger.error(f"Streaming error: {error_msg}")
        yield f"3:{json.dumps(error_msg)}\n"
        # Also send done to close the stream properly
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
