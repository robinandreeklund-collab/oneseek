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
import os
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
    # Convert Pydantic models to dicts for the agent
    messages = [msg.dict() for msg in request.messages]
    
    if request.stream:
        # Return streaming response in AI SDK format
        # Note: Errors must be handled within the stream itself
        return StreamingResponse(
            stream_chat_response(messages),
            media_type="text/plain; charset=utf-8"
        )
    else:
        # Non-streaming response (legacy support)
        try:
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
    
    IMPORTANT: This generator MUST yield something immediately to start
    the streaming response, preventing FastAPI from returning HTML error pages.
    """
    agent = None
    result = None
    
    try:
        # Get agent instance (might fail if vLLM is not available)
        try:
            agent = get_agent()
        except Exception as agent_error:
            # Agent initialization failed - yield error immediately
            import traceback
            error_details = traceback.format_exc()
            print(f"=" * 80)
            print(f"AGENT INITIALIZATION ERROR:")
            print(f"Error: {str(agent_error)}")
            print(f"Traceback:")
            print(error_details)
            print(f"=" * 80)
            
            yield f"0:I apologize, but I'm unable to connect to the AI model. Please ensure vLLM is running on {os.getenv('VLLM_URL', 'http://localhost:8000/v1')}.\n"
            yield "d:\n"
            return
        
        # Run agent to get result with streaming (might fail during execution)
        try:
            result = await asyncio.to_thread(agent.run_with_streaming, messages)
        except Exception as run_error:
            # Execution failed - yield error
            import traceback
            error_details = traceback.format_exc()
            print(f"=" * 80)
            print(f"AGENT EXECUTION ERROR:")
            print(f"Error: {str(run_error)}")
            print(f"Traceback:")
            print(error_details)
            print(f"=" * 80)
            
            yield f"0:I apologize, but I encountered an error while processing your request: {str(run_error)}\n"
            yield "d:\n"
            return
        
        # Validate result has expected structure
        if not isinstance(result, dict):
            error_msg = f"Invalid result type from agent: {type(result)}"
            print(error_msg)
            yield f"0:I apologize, but I received an unexpected response format from the AI.\n"
            yield "d:\n"
            return
        
        # Send metadata about steps and retrieved docs first (as annotations)
        metadata = {
            "steps": result.get("steps", []),
            "retrieved": result.get("retrieved", [])
        }
        
        # Stream annotations/data first
        if metadata["steps"] or metadata["retrieved"]:
            try:
                # Send as data annotation (AI SDK format)
                yield f"2:{json.dumps([metadata])}\n"
            except Exception as meta_error:
                print(f"Error sending metadata: {meta_error}")
                # Continue without metadata
        
        # Get tokens list
        tokens = result.get("tokens", [])
        
        if not tokens:
            # If no tokens but there's content, send it as a single token
            content = result.get("content", "")
            if content:
                # Escape special characters for the stream format
                escaped_content = content.replace('\n', '\\n').replace('\r', '\\r')
                yield f"0:{escaped_content}\n"
            else:
                # No content at all - send a fallback message
                yield f"0:I apologize, but I was unable to generate a response.\n"
        else:
            # Stream LLM response tokens as text chunks
            # Format: "0:token_text\n" where 0 indicates text chunk
            for token in tokens:
                try:
                    # Escape token if needed, but don't double-encode
                    if isinstance(token, str):
                        # Escape special characters for the stream format
                        escaped_token = token.replace('\n', '\\n').replace('\r', '\\r')
                        yield f"0:{escaped_token}\n"
                    else:
                        # If token is not a string, convert to string first
                        yield f"0:{str(token)}\n"
                    await asyncio.sleep(0.001)  # Small delay for smoother streaming
                except Exception as token_error:
                    print(f"Error streaming token: {token_error}")
                    # Skip this token and continue
                    continue
        
        # Send final done message
        yield "d:\n"
        
    except Exception as e:
        # Catch-all for any unexpected errors
        # Log the error for debugging
        import traceback
        error_details = traceback.format_exc()
        print(f"=" * 80)
        print(f"UNEXPECTED STREAMING ERROR:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print(f"Full traceback:")
        print(error_details)
        print(f"=" * 80)
        
        # Send error as plain text token (not JSON encoded)
        try:
            error_text = f"I apologize, but I encountered an unexpected error: {str(e)}"
            yield f"0:{error_text}\n"
            yield "d:\n"
        except:
            # Last resort - yield something to prevent HTML error page
            yield "0:Error\n"
            yield "d:\n"


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
