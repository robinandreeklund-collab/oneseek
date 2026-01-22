"""
FastAPI backend for OneSeek.ai MVP
Provides chat endpoint that orchestrates RAG workflow via LangGraph
with streaming support as default
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, AsyncIterator
import uvicorn
import json
import asyncio
from agent import get_agent

app = FastAPI(
    title="OneSeek.ai API",
    description="RAG-enhanced chat API with LangGraph orchestration",
    version="0.2.0"
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
        "version": "0.2.0"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    agent = get_agent()
    
    return {
        "status": "ok",
        "vllm_url": agent.vllm_url,
        "vllm_model": agent.vllm_model,
        "vespa_configured": agent.retriever is not None,
        "vespa_url": agent.vespa_url if agent.vespa_url else "not configured"
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint with streaming support (default)
    
    Accepts a list of messages and returns an AI response enhanced with
    RAG context from Vespa. Streams the response by default for better UX.
    """
    try:
        # Convert Pydantic models to dicts for the agent
        messages = [msg.dict() for msg in request.messages]
        
        if request.stream:
            # Return streaming response in AI SDK format
            return StreamingResponse(
                stream_chat_response(messages),
                media_type="text/plain; charset=utf-8"
            )
        else:
            # Non-streaming response (legacy support)
            agent = get_agent()
            result = agent.run(messages)
            
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


async def stream_chat_response(messages: List[Dict[str, str]]) -> AsyncIterator[str]:
    """
    Stream chat response in Vercel AI SDK compatible format
    
    Streams text tokens and metadata for the frontend.
    Uses newline-delimited JSON format expected by AI SDK.
    """
    try:
        agent = get_agent()
        
        # Run agent to get result with streaming
        result = await asyncio.to_thread(agent.run_with_streaming, messages)
        
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
        # Format: "0:token_text\n" where 0 indicates text chunk
        for token in result.get("tokens", []):
            # Escape token if needed, but don't double-encode
            if isinstance(token, str):
                # Escape special characters for the stream format
                escaped_token = token.replace('\n', '\\n').replace('\r', '\\r')
                yield f"0:{escaped_token}\n"
            else:
                # If token is not a string, JSON encode it
                yield f"0:{json.dumps(token)}\n"
            await asyncio.sleep(0.001)  # Small delay for smoother streaming
        
        # Send final done message
        yield "d:\n"
        
    except Exception as e:
        # Send error in AI SDK format
        error_msg = f"Error: {str(e)}"
        yield f"3:{json.dumps(error_msg)}\n"


@app.get("/config")
async def get_config():
    """Get current configuration (for debugging)"""
    agent = get_agent()
    
    return {
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
