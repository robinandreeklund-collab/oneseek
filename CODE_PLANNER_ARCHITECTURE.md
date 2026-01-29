# Code Planner Architecture Implementation

This document describes the implementation of the Code Planner architecture for structured code development in OneSeek.

## Overview

The Code Planner architecture provides a structured, planned approach to code development with dedicated phases for planning, implementation, testing, and validation. This ensures consistent, high-quality code delivery with proper testing and documentation.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                            START                                 │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      COORDINATOR                                 │
│                                                                  │
│  Detects query type and routes appropriately                    │
└───────┬──────────┬──────────┬──────────┬──────────┬────────────┘
        │          │          │          │          │
   ┌────┴────┐ ┌──┴────┐ ┌──┴──────┐ ┌─┴────┐ ┌──┴─────┐
   │ Planner │ │ Debate│ │  Code   │ │ Coder│ │ Direct │
   │         │ │Planner│ │ Planner │ │      │ │Response│
   │         │ │       │ │         │ │      │ │        │
   └────┬────┘ └──┬────┘ └────┬────┘ └─┬────┘ └───┬────┘
        │         │           │         │          │
        └─────────┴───────────┴─────────┘          │
                  │                                 │
                  ▼                                 ▼
        ┌──────────────────┐                  ┌────────┐
        │  HUMAN FEEDBACK  │                  │  END   │
        │                  │                  └────────┘
        │  Plan approval   │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │  RESEARCH TEAM   │
        │                  │
        │  Routes to:      │
        └────┬─────────────┘
             │
             │ (conditional routing based on step type)
             │
    ┌────────┼────────┬────────┬────────┐
    │        │        │        │        │
    ▼        ▼        ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│Resea-│ │Analy-│ │Coder │ │Tester│ │Back  │
│rcher │ │st    │ │      │ │      │ │to    │
│      │ │      │ │      │ │      │ │Team  │
└──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──────┘
   │        │        │        │
   └────────┴────────┴────────┘
            │
            ▼
   ┌──────────────────┐
   │    REPORTER      │
   │                  │
   │  Final synthesis │
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │       END        │
   └──────────────────┘
```

## Components

### 1. Code Planner Node

**Location:** `backend/deer_flow/graph/nodes.py::code_planner_node()`

**Purpose:** Creates structured, detailed plans for code development tasks.

**Features:**
- Analyzes code task requirements
- Creates multi-step execution plans
- Identifies research needs (documentation, examples)
- Specifies testing strategy
- Supports Swedish and English locales

**Plan Structure:**
```json
{
  "locale": "en-US",
  "has_enough_context": false,
  "thought": "Breaking down code task into 4 steps...",
  "title": "Code Task: REST API with Authentication",
  "steps": [
    {
      "need_search": true,
      "title": "Research Flask Authentication",
      "description": "Gather documentation on Flask-Login and JWT",
      "step_type": "research"
    },
    {
      "need_search": false,
      "title": "Implement User Model",
      "description": "Create User model with SQLAlchemy",
      "step_type": "processing"
    },
    {
      "need_search": false,
      "title": "Test Authentication",
      "description": "Run pytest for auth endpoints, check with pylint",
      "step_type": "testing"
    },
    {
      "need_search": false,
      "title": "Validate Architecture",
      "description": "Review code structure and security",
      "step_type": "analysis"
    }
  ]
}
```

**Prompts:**
- English: `backend/deer_flow/prompts/code_planner.md`
- Swedish: `backend/deer_flow/prompts/code_planner.sv_SE.md`

### 2. Tester Node

**Location:** `backend/deer_flow/graph/nodes.py::tester_node()`

**Purpose:** Validates code quality, runs tests, performs linting and type checking.

**Features:**
- Automated test execution (pytest, jest)
- Code quality checks (pylint, eslint)
- Type safety validation (mypy, tsc)
- Structured result reporting
- Actionable feedback on failures

**Available Tools:**
- `python_test_tool`: pytest, pylint, mypy
- `javascript_test_tool`: jest/vitest, eslint, tsc
- `file_system_tool`: Read test files
- `python_repl_tool`: Debug tests

**Prompts:**
- English: `backend/deer_flow/prompts/tester.md`
- Swedish: `backend/deer_flow/prompts/tester.sv_SE.md`

### 3. Test Tools

**Location:** `backend/deer_flow/tools/test_tools.py`

**Python Test Tool:**
```python
python_test_tool(
    test_type="pytest",  # or "pylint", "mypy"
    path="tests/",
    verbose=True
)
```

**JavaScript Test Tool:**
```python
javascript_test_tool(
    test_type="jest",  # or "vitest", "eslint", "tsc"
    path="tests/",
    project_path=".",
    verbose=True
)
```

**Configuration:**
```bash
ENABLE_PYTHON_TEST_TOOL=true
ENABLE_JAVASCRIPT_TEST_TOOL=true
```

### 4. Step Types

**Added:** `TESTING` step type to `backend/deer_flow/prompts/planner_model.py`

**Step Type Enum:**
```python
class StepType(str, Enum):
    RESEARCH = "research"      # Web search, documentation
    ANALYSIS = "analysis"      # Pure reasoning, no tools
    PROCESSING = "processing"  # Code execution, implementation
    TESTING = "testing"        # Test execution, validation
```

**Routing Logic:**
- `RESEARCH` → `researcher_node` (web search, crawl tools)
- `ANALYSIS` → `analyst_node` (no tools, pure LLM)
- `PROCESSING` → `coder_node` (python_repl, code tools)
- `TESTING` → `tester_node` (test tools)

### 5. Coordinator Routing

**Added:** `handoff_to_code_planner` tool

**Tools Available:**
1. `handoff_to_planner` - General research
2. `handoff_to_code_planner` - **NEW** - Structured code development
3. `handoff_to_coder` - Direct code implementation
4. `handoff_after_clarification` - After clarification
5. `direct_response` - Greetings, small talk

**Routing Decision Matrix:**

| Task Type | Complexity | Route To | Reason |
|-----------|-----------|----------|---------|
| Simple function | Low | Coder | Direct implementation |
| Full application | High | Code Planner | Needs planning & testing |
| Quick code snippet | Low | Coder | No planning needed |
| Multi-file project | High | Code Planner | Structured approach |
| Debug issue | Low | Coder | Quick fix |
| API with tests | High | Code Planner | Multiple phases |

### 6. Graph Builder Updates

**Location:** `backend/deer_flow/graph/builder.py`

**New Nodes:**
```python
builder.add_node("code_planner", code_planner_node)
builder.add_node("tester", tester_node)
```

**Updated Routing:**
```python
def continue_to_running_research_team(state: State):
    # ... existing logic ...
    if incomplete_step.step_type == StepType.TESTING:
        return "tester"
    # ... existing returns ...
```

**Conditional Edges:**
```python
builder.add_conditional_edges(
    "research_team",
    continue_to_running_research_team,
    ["planner", "researcher", "analyst", "coder", "tester"],
)
```

## Workflow Examples

### Example 1: Complex Python Project

**User Request:** "Create a Flask REST API with authentication"

**Flow:**
1. **Coordinator** detects complex code task → `handoff_to_code_planner`
2. **Code Planner** generates plan:
   ```
   - Step 1 (RESEARCH): Research Flask authentication patterns
   - Step 2 (PROCESSING): Implement User model and database
   - Step 3 (PROCESSING): Create authentication endpoints
   - Step 4 (TESTING): Run pytest, pylint, mypy
   - Step 5 (ANALYSIS): Security review
   ```
3. **Human Feedback** reviews and approves plan
4. **Research Team** executes:
   - **Researcher** gathers Flask documentation
   - **Coder** implements User model
   - **Coder** creates auth endpoints
   - **Tester** runs all tests
   - **Analyst** reviews security
5. **Reporter** generates final summary with test results

### Example 2: Simple Function

**User Request:** "Write a function to sort a list"

**Flow:**
1. **Coordinator** detects simple task → `handoff_to_coder`
2. **Coder** implements directly
3. **Response** with code

## Benefits

### 1. Consistency
✅ Same planning pattern across all code tasks
✅ Predictable workflow structure
✅ Uniform quality standards

### 2. Transparency
✅ User sees complete plan before execution
✅ Clear visibility of each phase
✅ Test results shown explicitly

### 3. Control
✅ Human approval before implementation
✅ Can edit plans before execution
✅ Configurable auto-accept mode

### 4. Quality
✅ Mandatory testing phase
✅ Linting and type checking
✅ Code review and analysis

### 5. Scalability
✅ Easy to add more step types
✅ Modular tool architecture
✅ Independent agent responsibilities

## Configuration

### Agent LLM Mapping

**Location:** `backend/deer_flow/config/agents.py`

```python
AGENT_LLM_MAP: dict[str, LLMType] = {
    # ... existing mappings ...
    "code_planner": "basic",
    "tester": "basic",
}
```

### Environment Variables

```bash
# Test tools
ENABLE_PYTHON_TEST_TOOL=true
ENABLE_JAVASCRIPT_TEST_TOOL=true

# Code tools (existing)
ENABLE_LINUX_SANDBOX=true
ENABLE_FILE_SYSTEM_TOOL=true
ENABLE_REACT_SANDBOX=true
```

### Admin Settings

- **Human Feedback**: ON by default, can be disabled
- **Auto-accept Plans**: OFF by default
- **Clarification Mode**: Configurable per session

## Integration with Existing Features

### Debate Mode
- Independent feature
- Both route through human_feedback
- Different use cases (debate vs code)

### AI Comparison
- Comparative analysis focus
- Code Planner for development
- Can coexist

### Direct Code Router
- Simple tasks → Direct coder
- Complex tasks → Code planner
- Coordinator decides based on complexity

## Testing

### Unit Tests
```bash
pytest tests/test_code_planner.py
pytest tests/test_tester_node.py
pytest tests/test_test_tools.py
```

### Integration Tests
```bash
pytest tests/integration/test_code_planner_flow.py
```

### Manual Testing

1. **Test Code Planner:**
   ```
   User: "Create a Python REST API with Flask and tests"
   Expected: Code Planner creates multi-step plan
   ```

2. **Test Tester:**
   ```
   - Create test files
   - Run tester_node with TESTING step
   - Verify pytest, pylint, mypy execution
   ```

3. **Test Direct Coder:**
   ```
   User: "Write a hello world function"
   Expected: Direct coder response (no planning)
   ```

## Future Enhancements

1. **Additional Test Frameworks**
   - Add support for more test frameworks
   - Coverage reporting
   - Performance testing

2. **Enhanced Planning**
   - ML-based complexity detection
   - Automatic test generation
   - Dependency analysis

3. **Frontend Integration**
   - Visual plan display
   - Interactive plan editing
   - Real-time test results in UI

4. **Advanced Routing**
   - Smart coordinator learns from history
   - Personalized routing based on user preferences
   - Context-aware complexity assessment

## Related Documentation

- [CODE_PLANNER_CONFIGURATION.md](./CODE_PLANNER_CONFIGURATION.md) - Usage and configuration
- [GRAPH_ARCHITECTURE_FUTURE.md](./docs/GRAPH_ARCHITECTURE_FUTURE.md) - Overall architecture vision
- [CODE_ROUTER_ARCHITECTURE.md](./CODE_ROUTER_ARCHITECTURE.md) - Direct code routing

## Implementation Summary

**Files Modified:**
1. `backend/deer_flow/graph/nodes.py` - Added code_planner_node, tester_node, handoff_to_code_planner
2. `backend/deer_flow/graph/builder.py` - Added nodes and routing
3. `backend/deer_flow/prompts/planner_model.py` - Added TESTING step type
4. `backend/deer_flow/config/agents.py` - Added LLM mappings

**Files Created:**
1. `backend/deer_flow/prompts/code_planner.md` - English prompt
2. `backend/deer_flow/prompts/code_planner.sv_SE.md` - Swedish prompt
3. `backend/deer_flow/prompts/tester.md` - English prompt
4. `backend/deer_flow/prompts/tester.sv_SE.md` - Swedish prompt
5. `backend/deer_flow/tools/test_tools.py` - Test tools implementation

**Total Lines Added:** ~1,245 lines
**Total Files Changed:** 10 files

---

**Last Updated:** 2026-01-28
**Author:** OneSeek Development Team
**Version:** 1.0.0
