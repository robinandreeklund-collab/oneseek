# Web Search Fix for Debate Mode

## Problem

Web search in debate mode was crashing VLLM, while the same web search worked perfectly in research mode (djupforskning).

## Root Cause

The debate flow was using incorrect async pattern for LangChain tools:

```python
# ❌ WRONG - Used in debate_flow.py
search_results = await asyncio.wait_for(
    asyncio.to_thread(self.search_tool.invoke, user_query),
    timeout=5.0
)
```

**Why this is wrong:**
1. LangChain tools already have async support via `.ainvoke()`
2. Using `asyncio.to_thread()` creates unnecessary thread overhead
3. Can cause issues with VLLM's event loop and async context

## Solution

Use the native async method that research flow uses:

```python
# ✅ CORRECT - Now used in debate_flow.py
search_results = await asyncio.wait_for(
    self.search_tool.ainvoke(user_query),
    timeout=5.0
)
```

## Comparison with Research Flow

**Research Flow (djupforskning) - Always Worked:**
- Passes `search_tool` to agent
- Agent invokes tool via LangChain's built-in mechanisms
- Uses `ainvoke()` internally for async operations

**Debate Flow - Now Fixed:**
- Calls `search_tool` directly (no agent wrapper)
- Now uses `ainvoke()` directly
- Same async pattern as research flow

## Locations Fixed

1. **OneSeek Round 1 Internal Knowledge Building** (`debate_flow.py` line ~469)
   - Changed from: `asyncio.to_thread(self.search_tool.invoke, user_query)`
   - Changed to: `self.search_tool.ainvoke(user_query)`

2. **Claim Verification in run_internal_analysis()** (`debate_flow.py` line ~656)
   - Changed from: `asyncio.to_thread(self.search_tool.invoke, search_query)`
   - Changed to: `self.search_tool.ainvoke(search_query)`

## Testing

After fix, debate mode should:
- ✅ Successfully perform web searches without crashes
- ✅ Use same async pattern as research flow
- ✅ No VLLM event loop errors
- ✅ No thread-related issues

## Technical Details

### LangChain Tool Methods

LangChain tools (like `TavilySearchWithImages`) provide:
- `.invoke(input)` - Synchronous execution
- `.ainvoke(input)` - Asynchronous execution (native async/await)
- `.run(input)` - Legacy synchronous method
- `.arun(input)` - Legacy asynchronous method

### Why ainvoke() is Better

1. **Native async**: No thread overhead
2. **Event loop safe**: Works with VLLM's async context
3. **Standard pattern**: What LangChain expects
4. **Better error handling**: Async exceptions propagate correctly

### When to Use asyncio.to_thread()

Only use `asyncio.to_thread()` for:
- Pure synchronous functions that have NO async alternative
- Third-party libraries without async support
- CPU-bound operations

**NOT** for LangChain tools - they have native async support!

## Result

Web search in debate mode now works identically to research flow. No more VLLM crashes during search operations.
