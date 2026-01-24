# Fix for Empty Response Issue

## Problem Report

User reported getting empty responses after the preview-based token limit fix:
- Question asked: "Kan du citera 1 kap. paragraf 2 från socialtjänstlagen [URL]"
- Response received: Just "Källor" (Sources) and "24 källor använda" (24 sources used)
- No actual content or answer provided

## Root Cause Analysis

The issue was that the agent was not reliably following the 3-stage workflow:

### Why the Agent Failed

1. **Field naming confusion**: `content_preview` looked like it could be used as content
2. **Insufficient warnings**: Instructions were not emphatic enough
3. **Agent behavior**: The model saw "preview" and tried to answer from it instead of following workflow
4. **Result**: Agent attempted to generate answer from 800-char previews, which were insufficient for detailed law citation

### The Workflow Breakdown

**Intended workflow:**
```
browse_page → previews → check_chunk_relevance → get_chunk_content → answer from full content
```

**What actually happened:**
```
browse_page → previews → agent tries to answer directly → incomplete/empty answer ❌
```

## Solution Implemented

Made it **impossible for agent to misinterpret** previews as complete content:

### 1. Field Naming Changes

**Before:**
```python
{
    "content_preview": "...",
    "full_length": 10000,
    "instructions": "Use check_chunk_relevance..."
}
```

**After:**
```python
{
    "preview": "...",  # Not "content" anything
    "full_length": 10000,
    "status": "preview_only",  # Explicit flag
    "instructions": "⚠️ PREVIEW ONLY - NOT COMPLETE CONTENT ⚠️\n..."
}
```

### 2. System Prompt Strengthening

**Added explicit prohibitions:**
- "⚠️ DO NOT attempt to answer from previews - they are INCOMPLETE ⚠️"
- Changed "use full content" → "ONLY use full content"
- Added step: "Generate answer from FULL CONTENT (not previews)"
- Emphasized previews are for filtering ONLY

**Before:**
```
c. IMMEDIATELY call check_chunk_relevance...
e. Use the full content from get_chunk_content...
```

**After:**
```
c. ⚠️ DO NOT attempt to answer from previews - they are INCOMPLETE ⚠️
d. IMMEDIATELY call check_chunk_relevance...
f. ONLY use the full content from get_chunk_content...
g. Generate answer from FULL CONTENT (not previews)
```

### 3. Enhanced Per-Chunk Instructions

Each chunk now contains step-by-step instructions:

```
⚠️ PREVIEW ONLY - NOT COMPLETE CONTENT ⚠️
This is a preview of part 2 of a large document. To get the full content:
1. Call check_chunk_relevance(chunk_id='2/5', chunk_content=preview, user_query='your query')
2. If relevant, call get_chunk_content(url='...', chunk_id='2/5')
3. Use full text from get_chunk_content to answer the question
```

## Expected Behavior After Fix

### Correct Workflow

1. **browse_page** returns chunks with:
   - `preview` field (NOT "content_preview")
   - `status: "preview_only"` (explicit flag)
   - ⚠️ warnings in instructions

2. **Agent sees**:
   - Clear "preview_only" status
   - Multiple warnings not to use previews
   - Step-by-step workflow instructions

3. **Agent follows workflow**:
   - Calls check_chunk_relevance on all previews
   - Identifies relevant chunks (e.g., chunk 2 contains "1 kap. paragraf 2")
   - Calls get_chunk_content for relevant chunks only
   - Generates complete answer from full content

4. **User receives**:
   - Complete citation of the requested paragraph
   - Proper sources
   - Full answer (not empty)

## Technical Changes

### Files Modified

**backend/tools.py:**
- Changed `content_preview` → `preview` (around line 351)
- Added `status: "preview_only"` (around line 355)
- Enhanced instructions with ⚠️ warnings (around line 356)
- Updated docstring to emphasize preview limitations (lines 237-267)

**backend/agent_graph.py:**
- Strengthened system prompt with explicit prohibitions (lines 163-176)
- Changed `content_preview` → `preview` in instructions
- Added "⚠️ DO NOT attempt to answer from previews" warning
- Changed "Use" → "ONLY use" for emphasis
- Added explicit step about generating from full content

## Testing

All tests pass:
- test_chunk_relevance.py: ✓
- test_preview_workflow.py: ✓
- Workflow simulation still shows proper token savings

## Why This Should Work

The combination of:
1. **Field naming** that doesn't suggest "content"
2. **Status flag** that explicitly marks as incomplete
3. **Multiple warnings** in system prompt and data
4. **Step-by-step instructions** in each chunk

Makes it extremely difficult for the agent to misinterpret the data or skip the workflow.

## Commit History

- cb78a38: Initial preview-based fix (solved token limit)
- 77d7954: Code quality improvements
- 0c5a99a: Fixed empty response issue (this fix)
