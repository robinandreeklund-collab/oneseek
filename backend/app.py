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
            # Return streaming response
            return StreamingResponse(
                stream_chat_response(messages),
                media_type="text/event-stream"
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
    Stream chat response using SSE (Server-Sent Events)
    
    Yields JSON events for:
    - steps: Processing steps as they happen
    - retrieved: Retrieved documents from Vespa
    - content: LLM response tokens as they're generated
    - done: Final signal with complete data
    """
    try:
        agent = get_agent()
        
        # Run agent in background to get retrieval results
        # We'll stream this first, then stream LLM tokens
        result = await asyncio.to_thread(agent.run_with_streaming, messages)
        
        # Stream steps as they come
        for step in result.get("steps", []):
            yield f"data: {json.dumps({'type': 'step', 'content': step})}\n\n"
            await asyncio.sleep(0.01)  # Small delay for better UX
        
        # Stream retrieved documents
        if result.get("retrieved"):
            yield f"data: {json.dumps({'type': 'retrieved', 'content': result['retrieved']})}\n\n"
        
        # Stream LLM response tokens
        for token in result.get("tokens", []):
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            await asyncio.sleep(0.01)
        
        # Send final complete response
        yield f"data: {json.dumps({'type': 'done', 'content': result.get('content', ''), 'retrieved': result.get('retrieved', []), 'steps': result.get('steps', [])})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


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
