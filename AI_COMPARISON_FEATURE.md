# AI Comparison / Debate OS Feature

## Overview

This feature implements a **Debate OS** capability for DeerFlow, allowing parallel querying of multiple AI models with synthesis and analysis.

## Features

### Backend (`backend/ai_comparison_flow.py`)

- **Parallel AI Model Queries**: Asynchronously queries multiple models:
  - GPT-3.5 (OpenAI)
  - Gemini 2.5 Flash (Google)
  - DeepSeek Chat
  - Grok-4 Fast Reasoning (xAI)
  - OneSeek Local (vLLM)

- **Analysis & Fact-Checking**: Uses DeerFlow's existing tools:
  - Web search (Tavily)
  - RAG retrieval (Vespa)
  - Crawling

- **Meta-Agents**: Four parallel meta-agents for deeper analysis:
  - Counterfactual Analysis
  - Robustness Evaluation
  - Consistency Check
  - Truth-Pressure Analysis

- **Synthesis**: Generates an optimal answer combining insights from all models

### Frontend

- **New Button**: "Jämför AI:er" / "Compare AIs" button in chat input
- **Icon**: Balance scale icon representing comparison
- **Translations**: English and Swedish support
- **Settings**: Toggle via settings store

### Integration

- **Graph Integration**: New `ai_comparison` node in LangGraph workflow
- **Routing**: Coordinator node checks `enable_ai_comparison` flag and routes accordingly
- **Reporter**: Updated to handle and format AI comparison results

## Configuration

### Required API Keys (in `.env` or `.env.deer`)

```bash
# OpenAI (for GPT-3.5)
OPENAI_API_KEY=your-openai-api-key

# Google (for Gemini 2.5 Flash)
GOOGLE_API_KEY=your-google-api-key

# DeepSeek
DEEPSEEK_API_KEY=your-deepseek-api-key

# xAI (for Grok-4 Fast Reasoning)
XAI_API_KEY=your-xai-api-key
XAI_BASE_URL=https://api.x.ai/v1

# Local model is automatically configured via VLLM_URL and VLLM_MODEL
```

**Note**: The feature works with any available models. If an API key is missing, that model is simply skipped.

## Usage

1. **Enable AI Comparison Mode**:
   - Click the "Jämför AI:er" button in the chat input
   - The button will be highlighted when active

2. **Send a Query**:
   - Type your question and send
   - The system will query all available models in parallel

3. **View Results**:
   - The report will show:
     - Individual model responses
     - Fact-checking sources
     - Synthesized optimal answer
     - Models and tools used

## Architecture

### Workflow Flow

```
User Query → Coordinator → [enable_ai_comparison?]
                             ↓ Yes
                          ai_comparison_node
                             ↓
                          Reporter → Final Report
```

### AI Comparison Flow

```
1. Parallel Queries (asyncio.gather)
   ├─ GPT-3.5
   ├─ Gemini 2.5 Flash
   ├─ DeepSeek
   ├─ Grok-4 Fast Reasoning
   └─ OneSeek Local

2. Fact-Check Analysis
   ├─ Web Search
   └─ RAG Retrieval

3. Meta-Agents (parallel)
   ├─ Counterfactual
   ├─ Robustness
   ├─ Consistency
   └─ Truth-Pressure

4. Synthesis
   └─ Optimal Answer + Sources
```

## Technical Details

### State Management

New fields in `State` (backend/deer_flow/graph/types.py):
```python
enable_ai_comparison: bool = False
comparison_results: dict[str, Any] | None = None
```

### API Integration

New parameter in `ChatRequest` (backend/deer_flow/server/chat_request.py):
```python
enable_ai_comparison: Optional[bool] = Field(
    False, description="Whether to enable AI comparison / Debate OS mode"
)
```

### Frontend Settings

New setting in `SettingsState` (web/src/core/store/settings-store.ts):
```typescript
enableAiComparison: boolean;
```

## Performance

- **Parallel Execution**: All model queries run concurrently using `asyncio.gather`
- **Scalability**: Supports up to 250 parallel calls (DeerFlow's deep research capability)
- **Streaming**: Results can be streamed to the UI as they arrive

## Future Enhancements

1. **Sidebar UI**: Dedicated comparison view with accordion for each model
2. **Model Selection**: Allow users to choose which models to include
3. **Comparison Metrics**: Add quantitative comparison scores
4. **Historical Tracking**: Save comparison results for analysis
5. **Custom Meta-Agents**: Allow users to define custom analysis criteria

## Notes

- The feature reuses DeerFlow's existing tools and infrastructure
- All analysis uses the same 32k context window as deep research
- Transparently shows sources, tools, and reasoning
- Compatible with existing DeerFlow features (background investigation, clarification, etc.)
