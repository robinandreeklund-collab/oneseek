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
│  │  • ChatInterface component                               │   │
│  │  • TransparensAccordion (sources & steps)                │   │
│  │  • Dark/Light theme                                      │   │
│  │  • localStorage chat history                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                    │
│                              │ HTTP POST /chat                   │
│                              ▼                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                               │
│                  http://localhost:8001                           │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              LangGraph Agent Workflow                    │   │
│  │                                                           │   │
│  │        START → [retrieve] → [generate] → END            │   │
│  │                     │             │                      │   │
│  │                     │             │                      │   │
│  │                     ▼             ▼                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│              Vespa Retriever    OpenAI Client                   │
│                     │                  │                         │
└─────────────────────────────────────────────────────────────────┘
                      │                  │
                      │                  │
                      ▼                  ▼
         ┌──────────────────┐  ┌──────────────────┐
         │  Vespa Cloud     │  │  vLLM Server     │
         │  (RAG Search)    │  │  localhost:8000  │
         │                  │  │                  │
         │  • Hybrid search │  │  • GPU inference │
         │  • BM25 + vector │  │  • AWQ quant     │
         │  • 384-dim embed │  │  • OpenAI API    │
         └──────────────────┘  └──────────────────┘
```

## Data Flow

### 1. User Query
```
User types: "What are AI risks?"
↓
Frontend: ChatInterface captures input
↓
POST /chat with messages array
```

### 2. Backend Processing
```
FastAPI receives request
↓
LangGraph Agent starts workflow
↓
State: { messages, retrieved_docs: [], steps: [], final_response: "" }
```

### 3. Retrieve Node
```
Extract last user message: "What are AI risks?"
↓
Generate embedding (384-dim vector)
↓
Query Vespa: YQL with hybrid ranking
  - BM25 text matching on title/content
  - Vector similarity on embedding
  - Top 6 results
↓
Store in state: retrieved_docs = [...]
Add to steps: ["Retrieving...", "Retrieved 6 documents"]
```

### 4. Generate Node
```
Build context from retrieved_docs:
  "### Retrieved Context:
   **Source 1: AI Safety and Ethics**
   Expert warnings about AI risks...
   **Source 2: ...**
   ..."
↓
Build chat messages:
  - SystemMessage with context
  - Previous chat history
  - Current user question
↓
Call vLLM via OpenAI client
↓
Store response in state: final_response = "..."
Add to steps: ["Generating...", "Response generated"]
```

### 5. Response to Frontend
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

### 6. Frontend Display
```
ChatInterface receives response
↓
Display AI message bubble with content
↓
Render TransparensAccordion:
  - Show 6 retrieved sources
  - Show 4 processing steps
  - Expandable/collapsible
↓
Save to localStorage: "oneseek-chat-history"
```

## Component Responsibilities

### Frontend Components

**ChatInterface**
- Manages chat state (messages array)
- Handles user input and submission
- Makes API calls to backend
- Displays messages and metadata
- localStorage persistence

**TransparensAccordion**
- Displays retrieved sources
- Shows processing steps
- Expandable UI with Radix UI
- Relevance scores

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

**agent.py (LangGraph)**
- State management (TypedDict)
- Workflow definition (StateGraph)
- Retrieve node (Vespa query)
- Generate node (LLM call)
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

### Backend
- **FastAPI**: High-performance async Python framework
- **LangGraph**: Agent orchestration with state management
- **LangChain**: LLM abstractions and integrations
- **Pydantic**: Data validation and serialization
- **python-dotenv**: Environment configuration

### Infrastructure
- **vLLM**: Fast local LLM inference with GPU
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
