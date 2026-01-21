"""
FastAPI backend for OneSeek.ai MVP
Provides chat endpoint that orchestrates RAG workflow via LangGraph
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
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
    stream: Optional[bool] = False


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


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint
    
    Accepts a list of messages and returns an AI response enhanced with
    RAG context from Vespa, along with metadata about retrieved documents
    and processing steps.
    """
    try:
        # Convert Pydantic models to dicts for the agent
        messages = [msg.dict() for msg in request.messages]
        
        # Get the agent and run the workflow
        agent = get_agent()
        result = agent.run(messages)
        
        # Convert retrieved docs to response model
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
