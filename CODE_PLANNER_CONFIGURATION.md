# Code Planner and Tester Configuration

This document describes how to configure and use the Code Planner and Tester agents.

## Environment Variables

### Test Tools Configuration

```bash
# Enable Python test tools (pytest, pylint, mypy)
ENABLE_PYTHON_TEST_TOOL=true

# Enable JavaScript test tools (jest, vitest, eslint, tsc)
ENABLE_JAVASCRIPT_TEST_TOOL=true
```

Add these to your `.env` file or set them in your environment before starting the application.

## Architecture Flow

### Code Planner Flow (Planned Development)

For complex code development tasks that benefit from structured planning:

```
User Request
    ↓
Coordinator (detects code task)
    ↓
Code Planner (creates detailed plan)
    ↓
Human Feedback (approves/edits plan)
    ↓
Research Team (if documentation needed)
    ↓
Coder (implements code)
    ↓
Tester (validates code)
    ↓
Reporter (final summary)
```

### Direct Coder Flow (Quick Development)

For simple, straightforward code questions:

```
User Request
    ↓
Coordinator (detects simple code task)
    ↓
Coder (direct implementation)
    ↓
Response
```

## Usage Examples

### Example 1: Complex Code Task with Planning

**User Request:**
```
Create a Python REST API with Flask that has user authentication, 
database integration, and comprehensive tests.
```

**Expected Flow:**
1. Coordinator detects complex code task → calls `handoff_to_code_planner`
2. Code Planner creates plan with steps:
   - Research Flask best practices and authentication patterns
   - Implement user model and database schema
   - Create authentication endpoints
   - Write unit tests for authentication
   - Run tests and validate code quality
3. Human approves plan
4. Research Team gathers Flask documentation
5. Coder implements each step
6. Tester validates with pytest, pylint, mypy
7. Reporter summarizes implementation

### Example 2: Simple Code Task (Direct)

**User Request:**
```
Write a Python function to calculate fibonacci numbers
```

**Expected Flow:**
1. Coordinator detects simple code task → calls `handoff_to_coder`
2. Coder implements function directly
3. Response with code

## Step Types

The Code Planner can create plans with these step types:

### RESEARCH Steps
- Gather documentation, examples, best practices
- Only included when external information is needed
- Executed by Researcher agent with web search tools

### PROCESSING Steps
- Actual code implementation
- File creation and modification
- Algorithm development
- Executed by Coder agent with code tools

### TESTING Steps
- Run unit tests (pytest, jest, etc.)
- Execute linters (pylint, eslint, etc.)
- Perform type checking (mypy, tsc, etc.)
- Validate code quality
- Executed by Tester agent with test tools

### ANALYSIS Steps
- Code review and architectural assessment
- Performance analysis
- Security review
- Executed by Analyst agent (pure reasoning)

## Test Tools

### Python Test Tool

```python
python_test_tool(
    test_type="pytest",      # or "pylint", "mypy"
    path="tests/",           # path to test directory or file
    verbose=True             # show detailed output
)
```

**Test Types:**
- `pytest`: Run unit and integration tests
- `pylint`: Code quality and style checking
- `mypy`: Static type checking

**Requirements:**
- pytest, pylint, mypy must be installed
- Test files should follow pytest conventions (`test_*.py`)

### JavaScript Test Tool

```python
javascript_test_tool(
    test_type="jest",        # or "vitest", "eslint", "tsc"
    path="src/",             # path to test directory or file
    project_path=".",        # project root (for tsc)
    verbose=True             # show detailed output
)
```

**Test Types:**
- `jest` or `vitest`: Run unit tests
- `eslint`: Linting and style checking
- `tsc`: TypeScript type checking

**Requirements:**
- jest/vitest, eslint, tsc must be installed via npm
- Configuration files: `jest.config.js`, `.eslintrc`, `tsconfig.json`

## Human Feedback Integration

Human feedback is controlled by admin settings (enabled by default):

1. **Plan Review**: After Code Planner creates plan, user reviews it
2. **Approval Options**:
   - `[ACCEPTED]` - Proceed with plan execution
   - `[EDIT_PLAN] <changes>` - Request plan modifications
3. **Auto-accept Mode**: Can be disabled in settings for automatic execution

## Coordinator Tool Selection

The Coordinator has these tools for routing:

1. **handoff_to_planner**: General research questions
2. **handoff_to_code_planner**: Complex code tasks requiring planning
3. **handoff_to_coder**: Simple, direct code questions
4. **handoff_after_clarification**: After clarification rounds
5. **direct_response**: Greetings, small talk

The LLM selects the appropriate tool based on:
- Task complexity
- Need for structured planning
- Whether documentation research would help
- Testing requirements

## Best Practices

### When to Use Code Planner

Use `handoff_to_code_planner` for:
- ✅ Multi-step development tasks
- ✅ Projects requiring documentation research
- ✅ Code that needs comprehensive testing
- ✅ Complex applications (APIs, web apps, etc.)
- ✅ Tasks with multiple components

### When to Use Direct Coder

Use `handoff_to_coder` for:
- ✅ Single function implementations
- ✅ Quick code snippets
- ✅ Simple algorithms
- ✅ Debugging assistance
- ✅ Code explanations

### Testing Strategy

For Python projects:
1. Run `pytest` for functionality
2. Run `pylint` for code quality (aim for 8.0+)
3. Run `mypy` for type safety

For JavaScript projects:
1. Run `jest`/`vitest` for functionality
2. Run `eslint` for code quality
3. Run `tsc` for TypeScript type checking

## Troubleshooting

### Test Tools Not Available

**Error:** "Tool disabled: Python test tool is disabled"

**Solution:** Set environment variable:
```bash
export ENABLE_PYTHON_TEST_TOOL=true
```

### Test Framework Not Installed

**Error:** "Error: pytest is not installed"

**Solution:** Install required tools:
```bash
pip install pytest pylint mypy
# or
npm install -D jest eslint typescript
```

### Tests Not Found

**Issue:** Tester reports "No tests found"

**Solution:**
- Ensure test files exist in expected locations
- Python: `tests/test_*.py`
- JavaScript: `tests/*.test.ts` or `*.test.js`

## Integration with Existing Features

### Debate Mode
- Debate mode and Code Planner are independent
- Can be enabled simultaneously if needed
- Both route through human_feedback

### AI Comparison
- AI Comparison focuses on comparing model responses
- Code Planner focuses on structured code development
- Different use cases, both route through planner

### Direct Code Router
- Existing direct coder routing still works
- Code Planner adds planned alternative
- Coordinator chooses based on task complexity
