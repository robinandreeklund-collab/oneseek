# Code Router Architecture

This document describes the architecture of the new code router in OneSeek's LangGraph implementation.

## Direct Routing Architecture

The code router implements a **direct response pattern** where code-related questions bypass the research workflow and get immediate responses from the Coder node.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         START                                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     COORDINATOR                               │
│  • Detects question type                                      │
│  • Routes based on handoff tool called                        │
└───────┬────────────────────┬───────────────┬────────────────┘
        │                    │               │
        │ handoff_to_       │ handoff_to_   │ handoff_to_
        │ planner           │ coder         │ debate_planner
        │                    │               │
        ▼                    ▼               ▼
┌──────────────┐   ┌──────────────────┐   ┌──────────────┐
│   PLANNER    │   │  CODER (Direct)  │   │DEBATE_PLANNER│
│              │   │  • Code execution│   │              │
│  Research    │   │  • Direct state  │   │  Debate flow │
│  workflow    │   │  • Extended tools│   │              │
└──────┬───────┘   └────────┬─────────┘   └──────┬───────┘
       │                    │                     │
       ▼                    ▼                     ▼
┌──────────────┐   ┌──────────────────┐   ┌──────────────┐
│RESEARCH_TEAM │   │    __END__       │   │HUMAN_FEEDBACK│
│              │   │  (Direct Response)│   │              │
│  Can call:   │   └──────────────────┘   └──────┬───────┘
│  • Researcher│                                  │
│  • Analyst   │                                  ▼
│  • Coder     │                           ┌──────────────┐
└──────┬───────┘                           │RESEARCH_TEAM │
       │                                   └──────────────┘
       ▼
┌──────────────┐
│   REPORTER   │
│              │
│  Final report│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   __END__    │
└──────────────┘
```

## Two Modes of Operation

### Mode 1: Direct Code Response (NEW)

**Trigger**: User asks a code-related question

**Flow**:
1. User: "Write a Python function to sort a list"
2. Coordinator detects code keywords → calls `handoff_to_coder`
3. **Coder node called directly** with full state
4. Coder executes with extended tools (Python REPL, Linux Sandbox, File System, React Sandbox)
5. **Coder responds directly to user** (goto __end__)

**Benefits**:
- ⚡ Fast response - no intermediate steps
- 🎯 Purpose-built - Coder designed for code tasks
- 🔧 Extended tools - Full sandbox environment
- 🚫 No unnecessary processing - Planner and Reporter skipped

### Mode 2: Research Workflow (Existing)

**Trigger**: Non-code research questions

**Flow**:
1. User: "What are the latest AI developments?"
2. Coordinator → Planner
3. Planner creates research plan
4. Research Team executes (may call Researcher, Analyst, or Coder as needed)
5. Reporter generates final report
6. Response to user

**When Coder is called from Research Team**:
- Coder detects it's part of a plan (not direct call)
- Coder returns to `research_team` instead of `__end__`
- Workflow continues through Reporter

## State Detection Logic

The Coder node determines its routing based on state:

```python
# In coder_node
current_plan = state.get("current_plan")
called_directly = current_plan is None or (
    isinstance(state.get("research_topic", ""), str) and 
    state.get("research_topic", "").startswith("[CODE]")
)

if called_directly:
    # Direct code question from coordinator
    return Command(update=result.update, goto="__end__")
else:
    # Called as part of research workflow
    return result  # Goes back to research_team
```

## Code Detection

The Coordinator uses keyword matching to identify code questions:

```python
code_keywords = [
    # Languages
    'python', 'javascript', 'java', 'typescript', 'c++', 'c#',
    
    # Code terms
    'code', 'programming', 'function', 'class', 'algorithm',
    
    # Frameworks
    'react', 'django', 'next.js', 'express',
    
    # Actions
    'write code', 'create app', 'build', 'debug', 'compile'
]
```

## Clarity Handling

For unclear code questions, Human-in-the-Loop is available:

```
Coordinator detects code + unclear
    ↓
handoff_to_coder(clarity="unclear")
    ↓
Human Feedback Node
    ↓
(After clarification)
    ↓
Coder Node → __end__
```

## Extended Tools Available to Coder

When called (either directly or from research_team), Coder has access to:

1. **Python REPL** - Execute Python code
2. **Linux Sandbox** - Run shell commands in isolated WSL/Docker
3. **File System** - Read/write files in secure workspace
4. **React Sandbox** - Create and preview Next.js applications

All tools are optional and can be enabled/disabled via environment variables.

## Comparison: Before vs After

### Before (Original Design)

```
Question → Coordinator → Planner → Research Team → Coder → Reporter → Response
```
- 6 nodes traversed
- Reporter formats research report (unnecessary for code)
- Planner creates execution plan (overkill for simple code questions)

### After (New Design)

```
Code Question → Coordinator → Coder → Response
```
- 3 nodes traversed
- Direct, purpose-built response
- Coder has full state and tools
- Planner/Reporter only used when needed (research workflow)

## Benefits of Direct Routing

1. **Performance**: Fewer nodes = faster response
2. **Simplicity**: Clear separation of concerns
3. **Flexibility**: Coder works in both modes (direct + workflow)
4. **Extensibility**: Easy to add more specialized routers
5. **User Experience**: Immediate code execution without research overhead

## Integration Points

### Backend
- `backend/deer_flow/graph/nodes.py` - Coordinator and Coder logic
- `backend/deer_flow/graph/builder.py` - Graph structure
- `backend/deer_flow/tools/code_tools.py` - Extended tools

### Frontend
- `frontend/src/components/code-preview.tsx` - Live preview component
- Integration via existing chat interface

## Future Enhancements

1. **More specialized routers**: Math, Data Analysis, Creative Writing
2. **Smart routing**: ML-based classification instead of keywords
3. **Multi-tool orchestration**: Let Coder decide which tools to use
4. **Streaming execution**: Show tool execution in real-time
5. **Collaborative coding**: Multiple users coding together

---

**Last Updated**: 2025-01-28
**Author**: OneSeek Development Team
