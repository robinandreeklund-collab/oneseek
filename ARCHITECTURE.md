# OneSeek.ai Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│                     http://localhost:3000                        │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           Next.js Frontend (React + TypeScript)          │   │
│  │                                                           │   │
│  │  • ChatInterface component (SSE streaming)               │   │
│  │  • Real-time token display with cursor                   │   │
│  │  • TransparensAccordion (sources & steps)                │   │
│  │  • Dark/Light theme                                      │   │
│  │  • localStorage chat history                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                    │
│                              │ HTTP POST /chat (stream=true)     │
│                              │ SSE Response ←───────────────┐   │
│                              ▼                                │   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                               │
│                  http://localhost:8001                           │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         LangGraph Agent Workflow (Streaming)             │   │
│  │                                                           │   │
│  │        START → [retrieve] → [generate_streaming] → END  │   │
│  │                     │             │                      │   │
│  │                     │             │ (tokens via callback)│   │
│  │                     ▼             ▼                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│              Vespa Retriever    ChatOpenAI.stream()             │
│                     │                  │                         │
└─────────────────────────────────────────────────────────────────┘
                      │                  │
                      │                  │ Streaming tokens
                      ▼                  ▼
         ┌──────────────────┐  ┌──────────────────┐
         │  Vespa Cloud     │  │  vLLM Server     │
         │  (RAG Search)    │  │  localhost:8000  │
         │                  │  │                  │
         │  • Hybrid search │  │  • GPU inference │
         │  • BM25 + vector │  │  • AWQ quant     │
         │  • 384-dim embed │  │  • Streaming API │
         └──────────────────┘  └──────────────────┘
```

## Data Flow (with Streaming)

### 1. User Query
```
User types: "What are AI risks?"
↓
Frontend: ChatInterface captures input
↓
POST /chat with messages array + stream: true (default)
↓
Frontend starts reading SSE stream
```

### 2. Backend Processing
```
FastAPI receives request
↓
LangGraph Agent starts workflow
↓
State: { messages, retrieved_docs: [], steps: [], final_response: "" }
```

### 3. Retrieve Node (Streaming)
```
Extract last user message: "What are AI risks?"
↓
SSE Event: { type: "step", content: "Retrieving relevant documents..." }
↓ (Frontend displays step immediately)
Generate embedding (384-dim vector)
↓
Query Vespa: YQL with hybrid ranking
  - BM25 text matching on title/content
  - Vector similarity on embedding
  - Top 6 results
↓
SSE Event: { type: "step", content: "Retrieved 6 documents" }
↓
SSE Event: { type: "retrieved", content: [...documents...] }
↓ (Frontend displays sources in accordion)
```

### 4. Generate Node (Streaming)
```
Build context from retrieved_docs
↓
SSE Event: { type: "step", content: "Generating response..." }
↓
Build chat messages with context + history
↓
Call vLLM with .stream() method
↓
For each token from vLLM:
  ↓
  SSE Event: { type: "token", content: "AI" }
  ↓ (Frontend appends token immediately - real-time display!)
  SSE Event: { type: "token", content: " risks" }
  ↓
  SSE Event: { type: "token", content: " include" }
  ↓
  ... (continues token by token)
↓
SSE Event: { type: "step", content: "Response generated successfully" }
↓
SSE Event: { type: "done", content: full_response, retrieved: [...], steps: [...] }
↓ (Frontend saves complete message to localStorage)
```

### 5. Frontend Streaming Display
```
SSE stream starts
↓
Create placeholder assistant message
↓
For each SSE event:
  ├─ type: "step" → Update steps array, re-render
  ├─ type: "retrieved" → Update retrieved docs, show accordion
  ├─ type: "token" → Append to content, show with cursor animation
  └─ type: "done" → Finalize message, save to localStorage
↓
Stream complete, enable input again
```
```
Return JSON:
{
  "content": "AI risks include control loss, bias...",
  "retrieved": [
    {
      "title": "AI Safety and Ethics",
      "content": "...",
      "relevance": 0.8542
    }
  ],
  "steps": [
    "Retrieving relevant documents from Vespa...",
    "Retrieved 6 documents",
    "Generating response with LLM...",
    "Response generated successfully"
  ]
}
```

### 6. User Experience
```
User sees:
1. Message sent immediately
2. "Retrieving relevant documents..." (live)
3. "Retrieved 6 documents" (live)
4. Sources appear in accordion (live)
5. "Generating response..." (live)
6. Tokens appear one by one with cursor: "AI▊"
7. Full sentence builds: "AI risks include control loss▊"
8. Final message complete with all metadata
9. Can interact immediately (cancel or new message)
```

## Streaming Architecture

### SSE (Server-Sent Events)

**Why SSE over WebSocket?**
- Simpler protocol (HTTP)
- Automatic reconnection
- Built-in browser support
- One-way communication sufficient
- Works through proxies/firewalls

**Event Format:**
```
data: {"type": "step", "content": "Retrieving..."}\n\n
data: {"type": "retrieved", "content": [...]}\n\n
data: {"type": "token", "content": "AI"}\n\n
data: {"type": "done", "content": "full response"}\n\n
```

### Backend Streaming Flow

```python
async def stream_chat_response(messages):
    # 1. Run retrieval (blocking but fast)
    result = await asyncio.to_thread(agent.run_with_streaming, messages)
    
    # 2. Stream steps
    for step in result["steps"]:
        yield f"data: {json.dumps({'type': 'step', 'content': step})}\n\n"
    
    # 3. Stream retrieved docs
    yield f"data: {json.dumps({'type': 'retrieved', 'content': docs})}\n\n"
    
    # 4. Stream LLM tokens (collected by callback)
    for token in result["tokens"]:
        yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
    
    # 5. Send final complete response
    yield f"data: {json.dumps({'type': 'done', ...})}\n\n"
```

### Frontend Streaming Handling

```typescript
const reader = response.body?.getReader();
const decoder = new TextDecoder();
let buffer = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split("\n");
  buffer = lines.pop() || "";
  
  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const data = JSON.parse(line.slice(6));
      
      switch (data.type) {
        case "step": updateSteps(data.content); break;
        case "retrieved": updateRetrieved(data.content); break;
        case "token": appendToken(data.content); break;
        case "done": finalizeMessage(data); break;
      }
    }
  }
}
```

## Component Responsibilities

### Frontend Components

**ChatInterface (Streaming-aware)**
- Manages chat state (messages array)
- Handles user input and submission
- **SSE stream processing with ReadableStream API**
- **Real-time token display with cursor animation**
- **Cancel request support via AbortController**
- **Progressive rendering of steps and sources**
- localStorage persistence
- Error handling with retry logic

**TransparensAccordion**
- Displays retrieved sources
- Shows processing steps
- Expandable UI with Radix UI
- Relevance scores
- Updates live during streaming

**ThemeToggle**
- Dark/light mode switching
- localStorage preference
- System preference detection

### Backend Components

**app.py (FastAPI)**
- HTTP endpoints
- Request/response validation with Pydantic
- CORS configuration
- Error handling
- Agent orchestration

**agent.py (LangGraph with Streaming)**
- State management (TypedDict)
- Workflow definition (StateGraph)
- Retrieve node (Vespa query)
- Generate node (LLM call)
- **Generate node streaming (token callback)**
- **run_with_streaming() method**
- Agent singleton pattern

**deploy_vespa.py**
- Schema definition
- Application package creation
- Deployment to Vespa Cloud
- Document feeding
- Sample data generation

## Technology Choices

### Frontend
- **Next.js 14+**: Modern React framework with App Router
- **TypeScript**: Type safety and better DX
- **shadcn/ui**: High-quality, customizable components
- **Tailwind CSS**: Utility-first styling
- **Radix UI**: Accessible component primitives
- **ReadableStream API**: Native browser SSE handling

### Backend
- **FastAPI**: High-performance async Python framework with SSE support
- **LangGraph**: Agent orchestration with state management
- **LangChain**: LLM abstractions and streaming integrations
- **Pydantic**: Data validation and serialization
- **python-dotenv**: Environment configuration
- **asyncio**: Async streaming support

### Infrastructure
- **vLLM**: Fast local LLM inference with GPU + streaming
- **Vespa Cloud**: Hybrid search engine
- **sentence-transformers**: Local embeddings generation
- **Docker**: Optional containerization

## State Management

### Frontend State
- **Component state**: useState for UI state
- **localStorage**: Persistent chat history
- **Theme**: localStorage + CSS classes

### Backend State
- **Agent state**: LangGraph TypedDict
  - messages: Chat history
  - retrieved_docs: Vespa results
  - steps: Processing log
  - final_response: LLM output
- **Singleton agent**: Shared across requests

## Security Considerations

1. **API Keys**: vLLM uses "EMPTY" key (local only)
2. **CORS**: Restricted to localhost in development
3. **Vespa Certs**: File-based authentication
4. **No user auth**: MVP has no user management
5. **Local data**: Chat history in browser localStorage

## Performance Optimizations

1. **Agent singleton**: Reuse LLM client and embeddings
2. **HNSW index**: Fast vector search in Vespa
3. **Top-K retrieval**: Limit to 6 documents
4. **GPU inference**: vLLM with quantization
5. **Async FastAPI**: Non-blocking I/O

## Future Enhancements

1. **Streaming**: SSE from vLLM to frontend
2. **Caching**: Redis for repeated queries
3. **Multi-agent**: Parallel LLM comparison
4. **Tools**: Web search, code execution
5. **Auth**: User accounts and API keys
