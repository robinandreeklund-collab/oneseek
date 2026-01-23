# LangGraph Multi-Tool Integration

This document describes the new LangGraph-based multi-tool search integration for OneSeek.ai.

## ⚠️ Important: vLLM Configuration Required

**The multi-tool search requires vLLM to be started with tool calling support:**

```bash
vllm serve Qwen/Qwen2.5-14B-Instruct-AWQ \
  --dtype auto \
  --quantization awq \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.92 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --host 0.0.0.0 --port 8000
```

**Required flags:**
- `--enable-auto-tool-choice` - Enables automatic tool calling
- `--tool-call-parser hermes` - Uses Hermes format for tool calls (works with Qwen models)

**Without these flags, you'll get an error:**
```
Error code: 400 - "auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set
```

## Overview

OneSeek now supports three powerful search tools that can be used simultaneously:

1. **Tavily Search** - Paid, robust, and highly accurate web search with concise summaries
2. **DuckDuckGo Search** - Free, simple, and anonymous web search
3. **Vespa Search** - Local/cloud-based RAG with embeddings and hybrid searching

The agent automatically decides which tools to use based on the user's query and can execute multiple tools in parallel for maximum efficiency.

## Architecture

### LangGraph Workflow

```
User Query
    ↓
[Agent Node]
    ├─ Decides if tools are needed
    ├─ Selects appropriate tools
    └─ Calls multiple tools in parallel
    ↓
[Tools Node] (parallel execution)
    ├─ Tavily Search
    ├─ DuckDuckGo Search
    └─ Vespa Search
    ↓
[Agent Node] (synthesis)
    ├─ Receives all tool results
    └─ Generates final answer with citations
    ↓
Response with Sources
```

## Files Created/Modified

### New Files

1. **`backend/tools.py`**
   - Defines the three search tools using LangChain's `@tool` decorator
   - Each tool returns structured results with title, content, URL, and relevance scores
   - Handles errors gracefully (missing API keys, network issues, etc.)

2. **`backend/agent_graph.py`**
   - Implements LangGraph workflow with conditional tool calling
   - Agent node that decides whether to use tools or answer directly
   - Tool node for parallel execution using LangGraph's ToolNode
   - Conditional edges that route between agent, tools, and final answer
   - Streaming support for real-time token display

3. **`backend/test_integration.py`**
   - Integration tests for the new functionality
   - Tests tool imports, agent instantiation, and backward compatibility

### Modified Files

1. **`backend/app.py`**
   - Added `use_tools` parameter to ChatRequest (default: True)
   - Updated `/chat` endpoint to support both new and legacy agents
   - Enhanced `/health` endpoint to show tool availability
   - Updated `/config` endpoint with tool configuration details
   - Version bumped to 0.3.0

2. **`backend/requirements.txt`**
   - Added `tavily-python==0.5.0`
   - Added `duckduckgo-search==7.0.1`

3. **`backend/.env.example`**
   - Added `TAVILY_API_KEY` configuration

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Search Tools Configuration

# Tavily API Key (optional - get from https://tavily.com/)
TAVILY_API_KEY=your-tavily-api-key-here

# Vespa configuration (existing)
VESPA_URL=https://your-app.your-tenant.vespa-cloud.net
VESPA_CERT_PATH=/path/to/certificate.pem
VESPA_KEY_PATH=/path/to/private-key.pem

# vLLM configuration (existing)
VLLM_URL=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ
```

### Tool Requirements

- **DuckDuckGo**: No configuration needed (always available)
- **Tavily**: Requires API key from https://tavily.com/
- **Vespa**: Requires Vespa Cloud setup (existing requirement)

## Usage

### API Endpoint

The `/chat` endpoint now accepts an optional `use_tools` parameter:

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What are the latest AI developments?"}
    ],
    "use_tools": true,
    "stream": true
  }'
```

### Request Parameters

```typescript
{
  messages: Array<{role: string, content: string}>,
  stream?: boolean,              // Default: true
  system_prompt?: string,        // Custom system prompt
  enable_thinking?: boolean,     // Default: false
  use_tools?: boolean            // Default: true (new!)
}
```

### Behavior

- **`use_tools=true`** (default): Uses new LangGraph agent with multi-tool search
- **`use_tools=false`**: Uses legacy agent with Vespa-only RAG

### Agent Intelligence

The agent automatically:
1. Analyzes the user's query
2. Decides if external search is needed
3. Selects appropriate tools (can use multiple in parallel)
4. Synthesizes results with proper citations
5. Provides transparent sourcing

Example queries that benefit from tools:
- "What's happening with AI regulation in 2026?"
- "Compare the latest LLM models"
- "What are experts saying about AI safety?"

## Features

### Multi-Tool Parallel Execution

When the agent decides to search, it can call multiple tools simultaneously:
- Tavily for high-quality web results
- DuckDuckGo for additional perspectives
- Vespa for internal knowledge base

This leverages vLLM's continuous batching for 2-5× throughput improvement.

### Streaming Support

Results stream in real-time:
1. Steps update live ("Calling tools: tavily_search, vespa_search")
2. Tool results appear as retrieved documents
3. Final answer streams token-by-token
4. All sources cited appropriately

### Error Handling

Each tool gracefully handles:
- Missing API keys
- Network failures
- Configuration issues
- Empty results

The agent continues with available tools if some fail.

## Backward Compatibility

The original `agent.py` is preserved and still works:
- Set `use_tools=false` in requests
- Or set `USE_TOOLS=false` in environment
- Legacy behavior: Vespa RAG only, no external search

## Testing

Run integration tests:

```bash
cd backend
python test_integration.py
```

Expected output:
```
✓ Tools Import
✓ Agent Graph Import
✓ App Import
✓ Tool Execution (DuckDuckGo)
✓ Backward Compatibility
```

## Health Check

Check tool availability:

```bash
curl http://localhost:8001/health
```

Response:
```json
{
  "status": "ok",
  "mode": "multi-tool",
  "vllm_url": "http://localhost:8000/v1",
  "vllm_model": "Qwen/Qwen2.5-14B-Instruct-AWQ",
  "tools_available": ["tavily_search", "duckduckgo_search", "vespa_search"],
  "tavily_configured": true,
  "vespa_configured": true
}
```

## Performance

### Throughput Improvements

- **Parallel tool execution**: All tools run simultaneously
- **vLLM batching**: Multiple queries processed together
- **Continuous batching**: New requests join in-flight batches
- **Expected improvement**: 2-5× throughput under load

### Response Quality

- **Factual accuracy**: Web search ensures current information
- **Transparency**: All sources clearly cited
- **Multi-perspective**: Multiple search engines provide diverse results
- **RAG enhancement**: Local knowledge base adds context

## Future Enhancements

Potential additions:
- X (Twitter) search integration
- Code execution tool
- Calculator/math tool
- Image search
- Academic paper search (arXiv, Semantic Scholar)

## Troubleshooting

### Tools not being called

- Check that `use_tools=true` in request
- Verify environment variable `USE_TOOLS` is not set to "false"
- Query must require external information

### vLLM tool calling error (400 Bad Request)

**Error message:**
```
Error code: 400 - "auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set
```

**Solution:**
Restart vLLM with the required flags:
```bash
vllm serve YOUR_MODEL \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  [other flags...]
```

The `hermes` parser works with most models including Qwen, Llama, and Mistral.

### DuckDuckGo errors

- May hit rate limits with heavy use
- Wait a few seconds and retry
- Consider using Tavily for production

### Tavily not working

- Verify `TAVILY_API_KEY` in `.env`
- Check API key is valid at https://tavily.com/
- Free tier has usage limits

### Vespa not working

- Verify `VESPA_URL`, `VESPA_CERT_PATH`, `VESPA_KEY_PATH` are set
- Check certificates are valid
- Ensure Vespa app is deployed

## Example Workflow

1. User asks: "What are the latest breakthroughs in quantum computing?"
2. Agent analyzes query → determines web search needed
3. Agent calls Tavily + DuckDuckGo in parallel
4. Tools return results with URLs and snippets
5. Agent synthesizes answer, citing sources:
   - "According to [Source 1], IBM achieved..."
   - "Research from [Source 2] shows..."
6. Response streams to frontend with live updates
7. User sees sources in TransparensAccordion

## Migration Guide

For existing deployments:

1. Update dependencies: `pip install -r requirements.txt`
2. Add `TAVILY_API_KEY` to `.env` (optional)
3. Restart backend: `uvicorn app:app --reload --port 8001`
4. Test with `curl` or frontend
5. Monitor `/health` endpoint

No frontend changes required! The API is backward compatible.

## Credits

- LangGraph for workflow orchestration
- Tavily for web search API
- DuckDuckGo for free anonymous search
- Vespa for hybrid RAG search
