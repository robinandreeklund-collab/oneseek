# VLLM Crash Fix - Context Explosion from Search Results

## Problem

When OneSeek performed internal web search in Round 1, the search results from Tavily contained extensive data including:
- Raw content (thousands of characters)
- Image data
- Multiple search results
- Metadata

The `_summarize_search_results` method was not properly limiting the output size, causing:
- Context explosion: 1,270 tokens → 36,797 tokens
- VLLM EngineCore crash
- Debate mode failure

## Root Cause

The original implementation had critical issues with string conversion happening BEFORE slicing, creating huge intermediate strings.

## Solution

### 1. Enhanced `_summarize_search_results` Method
- Configurable limit (default 500 chars)
- Multiple results handled (up to 3)
- Dict handling without full string conversion
- Nested structures handled recursively
- Final safety check guarantees max_chars

### 2. Additional Safety in `query_model_in_debate`
- Explicit 500 char limit for Round 1 search
- Token counting before adding to context
- Hard truncation if still >200 tokens
- Logging of char and token counts

## Impact

**Before Fix:**
- Context: 1,270 tokens + Search: 35,527 tokens = 36,797 tokens → VLLM crash

**After Fix:**
- Context: 1,270 tokens + Search: ~125 tokens = ~1,400 tokens → Safe

**Token Reduction:** 96% (36,797 → ~1,400 tokens)

## Testing

All tests pass in `test_search_summarize_logic.py`:
- ✅ Large list results (50KB+) → Limited to 318 chars
- ✅ Dict with huge fields (10KB+) → Limited to 300 chars
- ✅ Nested structures → Limited correctly
- ✅ Empty results → Handled gracefully
- ✅ Huge object (100KB+) → Limited to 100 chars
