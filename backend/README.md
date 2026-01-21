# OneSeek Backend

FastAPI backend with LangGraph orchestration for RAG-enhanced chat via Vespa Cloud and vLLM.

## Features

- **FastAPI**: Modern async API framework
- **LangGraph**: Agent workflow orchestration (retrieve → generate)
- **Vespa Cloud**: Hybrid search (BM25 + semantic) for RAG
- **vLLM Integration**: Local LLM inference via OpenAI-compatible API
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your Vespa Cloud credentials and vLLM URL
```

4. Deploy Vespa schema and feed data:
```bash
python deploy_vespa.py
```

5. Start the API server:
```bash
uvicorn app:app --reload --port 8001
```

## Configuration

Edit `.env`:

```bash
# Vespa Cloud Configuration
VESPA_URL=https://your-app.your-tenant.vespa-cloud.net
VESPA_CERT_PATH=/path/to/certificate.pem
VESPA_KEY_PATH=/path/to/private-key.pem

# vLLM Configuration
VLLM_URL=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ

# Optional
MODEL_TEMPERATURE=0.7
MAX_TOKENS=2048
```

## API Endpoints

### POST /chat
Main chat endpoint with RAG enhancement.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "What are AI risks?"},
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "Tell me more"}
  ]
}
```

**Response:**
```json
{
  "content": "AI risks include...",
  "retrieved": [
    {
      "title": "AI Safety and Ethics",
      "content": "Experts warn about...",
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

### GET /health
Health check with configuration status.

**Response:**
```json
{
  "status": "ok",
  "vllm_url": "http://localhost:8000/v1",
  "vllm_model": "Qwen/Qwen2.5-14B-Instruct-AWQ",
  "vespa_configured": true,
  "vespa_url": "https://..."
}
```

### GET /config
Configuration details (for debugging).

## Architecture

### LangGraph Workflow

The agent uses a simple two-node workflow:

1. **retrieve**: Query Vespa for relevant documents
   - Uses last user message as query
   - Retrieves top-6 documents
   - Combines BM25 and semantic search

2. **generate**: Generate response with LLM
   - Builds context from retrieved docs
   - Adds chat history
   - Calls vLLM via OpenAI-compatible API

### State Management

```python
class AgentState(TypedDict):
    messages: List[Dict[str, str]]
    retrieved_docs: List[Dict[str, Any]]
    steps: List[str]
    final_response: str
```

## Vespa Deployment

Run `deploy_vespa.py` to:

1. Create application package with schema:
   - `doc_id`: string
   - `title`: string (indexed)
   - `content`: string (indexed)
   - `embedding`: tensor<float>(x[384]) (HNSW index)

2. Deploy to Vespa Cloud

3. Feed 15 sample documents (Swedish content about AI, Sweden, tech, etc.)

4. Test with sample query

### Schema Highlights

- **Hybrid ranking**: Combines nativeRank (BM25) with semantic similarity
- **HNSW index**: Fast approximate nearest neighbor search
- **384-dim embeddings**: From all-MiniLM-L6-v2

## Development

### Running without Vespa

The backend gracefully handles missing Vespa configuration:
- Will skip retrieval step
- Still generates responses via vLLM
- Useful for testing LLM integration

### Testing

```bash
# Health check
curl http://localhost:8001/health

# Test chat
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is AI?"}]}'
```

## Dependencies

- **fastapi**: API framework
- **uvicorn**: ASGI server
- **langgraph**: Agent orchestration
- **langchain**: LLM abstractions
- **langchain-openai**: OpenAI-compatible LLM client
- **pyvespa**: Vespa Cloud SDK
- **sentence-transformers**: Embedding models
- **python-dotenv**: Environment configuration

## Troubleshooting

### vLLM Connection Error
- Ensure vLLM is running: `vllm serve Qwen/Qwen2.5-14B-Instruct-AWQ --port 8000`
- Check `VLLM_URL` in `.env`

### Vespa Authentication Error
- Verify cert/key paths in `.env`
- Download from Vespa Console → Security
- Ensure files are readable

### No Retrieved Documents
- Check Vespa deployment with `deploy_vespa.py`
- Verify documents were fed successfully
- Test queries that match fed content
