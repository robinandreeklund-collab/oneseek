# DeerFlow Integration Guide for OneSeek

This document explains how ByteDance's DeerFlow architecture has been integrated into OneSeek to enhance deep research capabilities.

## Overview

DeerFlow is a community-driven deep research framework that combines language models with specialized tools for tasks like web search, crawling, and code execution. OneSeek has integrated key architectural patterns from DeerFlow while maintaining compatibility with its VLLM-based local inference setup.

## What Was Integrated

### 1. LLM Provider Abstraction (`deer_flow/llms/`)

DeerFlow's flexible LLM provider system has been adapted to work with VLLM:

- **LLM Type System**: Support for different LLM types (basic, reasoning, code, vision)
- **Instance Caching**: Reuse LLM instances to reduce initialization overhead
- **VLLM Integration**: OpenAI-compatible API wrapper for local VLLM deployment

```python
from deer_flow.llms import get_llm_by_type

# Get a cached LLM instance
llm = get_llm_by_type("basic")  # Uses VLLM configuration
```

### 2. Agent Factory Pattern (`deer_flow/agents/`)

Specialized agents for different tasks, inspired by DeerFlow's multi-agent architecture:

- **Researcher Agent**: Optimized for information gathering and search
- **Analyst Agent**: Specialized in data synthesis and analysis
- **Coder Agent**: Focused on code generation with lower temperature

```python
from deer_flow.agents import create_researcher_agent, create_analyst_agent

# Create specialized agents
researcher = create_researcher_agent(tools=search_tools)
analyst = create_analyst_agent(tools=analysis_tools)
```

### 3. Configuration Management (`deer_flow/config/`)

Hybrid configuration approach combining environment variables with validation:

- **Modular Config**: Separate configs for VLLM, Vespa, and search tools
- **Validation**: Configuration validation before startup
- **Environment-First**: All configuration via environment variables

```python
from deer_flow.config import get_full_config, validate_config

# Get complete configuration
config = get_full_config()

# Validate configuration
is_valid, errors = validate_config()
```

### 4. Workflow Orchestration (`deer_flow/graph/`)

Multi-agent workflow patterns using LangGraph:

- **Deep Research Workflow**: Multi-step research with specialized agents
- **Simple Agent Workflow**: Compatible with existing OneSeek patterns
- **Tool Integration**: Seamless integration with existing OneSeek tools

```python
from deer_flow.graph import create_deep_research_workflow

# Create a multi-agent research workflow
workflow = create_deep_research_workflow(tools)
result = workflow.invoke({"messages": messages})
```

## Architectural Alignment

### DeerFlow's Foundation
- Multi-agent orchestration with specialized roles
- Tool interception and approval workflows
- State management with rich metadata tracking
- Flexible LLM provider abstraction

### OneSeek's Foundation
- VLLM for local GPU-accelerated inference
- LangGraph for agentic workflows
- Multi-tool search (Tavily, DuckDuckGo, Vespa)
- Streaming responses with transparency

### Integration Strategy
The integration preserves OneSeek's core strengths while adopting DeerFlow's patterns:

1. **LLM Layer**: DeerFlow's abstraction adapted for VLLM
2. **Agent Layer**: Specialized agent factories instead of monolithic agent
3. **Tool Layer**: OneSeek's tools work with DeerFlow's agent system
4. **Workflow Layer**: DeerFlow's multi-agent patterns as optional workflows

## Using DeerFlow Features in OneSeek

### Option 1: Use Existing OneSeek Agent (Backward Compatible)

```python
# In app.py - existing approach still works
from agent_graph import OneSeekGraphAgent

agent = OneSeekGraphAgent(
    vllm_url=os.getenv("VLLM_URL"),
    vllm_model=os.getenv("VLLM_MODEL")
)
```

### Option 2: Use DeerFlow-Inspired Agents

```python
# New approach using DeerFlow patterns
from deer_flow.agents import create_researcher_agent
from deer_flow.llms import get_llm_by_type
from tools import get_available_tools

# Get VLLM-backed LLM
llm = get_llm_by_type("basic")

# Create researcher with tools
tools = get_available_tools()
researcher = create_researcher_agent(tools)

# Use like any LangChain LLM
response = researcher.invoke(messages)
```

### Option 3: Use Deep Research Workflow

```python
# Multi-agent research workflow
from deer_flow.graph import create_deep_research_workflow
from tools import get_available_tools

workflow = create_deep_research_workflow(get_available_tools())

# Execute workflow
result = workflow.invoke({
    "messages": messages,
    "steps": [],
    "retrieved_docs": [],
    "tool_actions": []
})
```

## Configuration

All DeerFlow components use OneSeek's existing environment variables:

```bash
# VLLM Configuration (required)
VLLM_URL=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ
VLLM_TEMPERATURE=0.7
VLLM_MAX_TOKENS=2048

# Vespa Configuration (optional)
VESPA_URL=https://your-app.vespa-cloud.net
VESPA_CERT_PATH=/path/to/cert.pem
VESPA_KEY_PATH=/path/to/key.pem

# Search Configuration (optional)
TAVILY_API_KEY=your-tavily-key
```

## Benefits of Integration

1. **Specialized Agents**: Different agent types for different tasks
2. **Better Code Generation**: Dedicated code agent with lower temperature
3. **Multi-Agent Workflows**: Complex research tasks with agent collaboration
4. **Flexible Architecture**: Easy to add new agent types or workflows
5. **Maintained Compatibility**: Existing OneSeek features continue to work

## Future Enhancements

Based on DeerFlow's capabilities, potential future additions:

- **Tool Interception**: Pre-execution approval for sensitive operations
- **Checkpointing**: State persistence for long-running research tasks
- **Citation System**: Structured citation extraction and merging
- **Prompt Templates**: Internationalized prompt templates
- **RAG Integration**: Multiple vector store backends
- **Report Generation**: Structured report creation from research

## License and Attribution

This integration uses concepts from ByteDance's DeerFlow project, which is released under the MIT License. See `DEER_FLOW_ATTRIBUTION.md` for complete license information and attribution.

## References

- DeerFlow Repository: https://github.com/bytedance/deer-flow
- DeerFlow Documentation: https://deerflow.tech/
- OneSeek Repository: https://github.com/robinandreeklund-collab/oneseek
