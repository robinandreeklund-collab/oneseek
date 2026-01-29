# Fix: KeyError in Debate Nodes

## Problem
After implementing the parallel debate flow, the debate execution failed with:
```
KeyError: -1
at line 2724 in proponent_node
last_msg = agent_messages[-1]
```

## Root Cause
The debate nodes (proponent, opponent, fact_checker, synthesizer) were incorrectly treating the return value of `agent.ainvoke()` as a list, when it actually returns a **dictionary** with the structure:

```python
{
    "messages": [list of messages],
    ...
}
```

## Solution
Fixed all 4 debate nodes by:

1. **Changed variable name** from `agent_messages` to `result` for clarity
2. **Corrected message access**: 
   - Before: `agent_messages[-1]`
   - After: `result["messages"][-1]`
3. **Added proper validation**: `if result and "messages" in result`
4. **Fixed state storage**: `result.get("messages", [])` instead of `agent_messages`
5. **Added explanatory comment** about data structure

## Changes Made

### Before (Incorrect)
```python
agent_messages = await agent.ainvoke(state, config)

response_content = ""
if agent_messages and len(agent_messages) > 0:
    last_msg = agent_messages[-1]  # KeyError: -1
    if hasattr(last_msg, 'content'):
        response_content = last_msg.content

return Command(
    update={
        "messages": agent_messages,  # Wrong structure
        ...
    }
)
```

### After (Correct)
```python
result = await agent.ainvoke(state, config)

# Extract response - agent returns dict with "messages" key
response_content = ""
if result and "messages" in result and len(result["messages"]) > 0:
    last_msg = result["messages"][-1]  # Correct access
    if hasattr(last_msg, 'content'):
        response_content = last_msg.content

return Command(
    update={
        "messages": result.get("messages", []),  # Correct structure
        ...
    }
)
```

## Affected Nodes
- ✅ `proponent_node` (line ~2719)
- ✅ `opponent_node` (line ~2767)
- ✅ `fact_checker_node` (line ~2815)
- ✅ `synthesizer_node` (line ~2863)

## Testing
- ✅ Python syntax validation passes
- ✅ Debate chain tests pass (4/5, 1 fails due to test env dependencies only)
- ✅ Code follows same pattern as working `_execute_agent_step` function

## Commit
Fixed in commit `7a03c24`: "Fix KeyError in debate nodes - correct agent.ainvoke() result handling"
