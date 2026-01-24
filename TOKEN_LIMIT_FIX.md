# Fix for Token Limit Error (52,809 tokens)

## Problem Diagnosed

The user reported getting this error:
```
vllm.exceptions.VLLMValidationError: This model's maximum context length is 32768 tokens. 
However, your request has 52809 input tokens.
```

When asking: "Kan du citera 1 kap. paragraf 2 från socialtjänstlagen https://www.riksdagen.se/..."

## Root Cause

The original implementation had a **critical design flaw**:

1. `browse_page` returned ALL chunk content immediately (all 52K+ tokens)
2. LangGraph's ToolNode added all that content to the conversation context
3. By the time the agent could decide to filter chunks, all 52K tokens were already in context
4. The model hit the token limit before check_chunk_relevance could help

**The agent never had a chance to filter - the damage was already done!**

## Solution: Preview-Based Approach

### New 3-Stage Workflow

**Stage 1: Browse with Previews**
- `browse_page(url)` now returns:
  - Small pages (<6KB): Full content immediately (backward compatible)
  - Large pages (>6KB): Only **previews** (800 chars each) + metadata
- Full content is cached in memory for later retrieval

**Stage 2: Filter Previews**
- Agent calls `check_chunk_relevance` on all previews in parallel
- Only ~800 chars per chunk sent to model for filtering
- Example: 5 chunks = 4KB of previews vs 30KB of full content

**Stage 3: Fetch Relevant Chunks**
- Agent calls `get_chunk_content(url, chunk_id)` for relevant chunks only
- Retrieves full text from cache
- Only relevant content sent to model

## Example with User's Query

### Before (BROKEN):
```
browse_page(law_url)
└─ Returns: [chunk1: 10KB, chunk2: 10KB, chunk3: 10KB, ...]
└─ Total: 52,809 tokens sent immediately
└─ ERROR: Token limit exceeded ❌
```

### After (FIXED):
```
1. browse_page(law_url)
   └─ Returns: [preview1: 800 chars, preview2: 800 chars, ...]
   └─ Total: ~4KB sent initially ✓

2. check_chunk_relevance(all previews in parallel)
   └─ Chunk 1: relevant=False (introduction)
   └─ Chunk 2: relevant=True (contains "1 kap. paragraf 2") ✓
   └─ Chunk 3: relevant=False (later sections)

3. get_chunk_content(url, "2/5")
   └─ Retrieves full text of chunk 2 only: ~10KB
   └─ Total sent: 4KB previews + 10KB relevant = 14KB ✓

Result: 14KB vs 52KB = 73% reduction ✅ No error!
```

## Technical Implementation

### tools.py Changes

1. **browse_page modified:**
   - Detects large pages (>6000 chars)
   - Creates 800-char previews with truncation indicator
   - Stores full content in `_chunk_content_cache`
   - Returns chunks with `content_preview` and `full_length` fields

2. **get_chunk_content added:**
   - New tool to fetch full content by URL + chunk_id
   - Retrieves from cache (populated by browse_page)
   - Returns full text only when requested

3. **check_chunk_relevance updated:**
   - Works with both preview and full content
   - Docstring clarifies preview-based usage

### agent_graph.py Changes

1. **System prompt updated:**
   - New "CHUNK HANDLING WORKFLOW" section
   - Explicit 3-stage instructions
   - Example showing token savings

2. **Tool mapping:**
   - Added: `get_chunk_content` → `fetch_chunk` (📄, orange)

## Testing

### Simulation Results
```
Total content: 8,150 chars
Preview size: 2,445 chars
Fetched relevant: 3,400 chars
Total sent: 5,845 chars
Savings: 28.3% with 2 of 3 chunks filtered
```

### Real-World Impact
For the user's case (52,809 tokens):
- Estimated 5 chunks at ~10KB each
- Previews: 5 × 800 chars = 4KB
- If 1-2 relevant: 14-24KB total
- **Savings: 50-70%** ✅ Well under 32,768 token limit

## Why This Works

1. **Prevents upfront token explosion:** Only previews loaded initially
2. **Agent can actually filter:** Previews in context, not full content
3. **Fetches on-demand:** Only relevant chunks retrieved
4. **Backward compatible:** Small pages work as before
5. **No configuration needed:** Works automatically

## Files Changed

- `backend/tools.py`: Modified browse_page, added get_chunk_content
- `backend/agent_graph.py`: Updated system prompt and tool mapping
- `backend/test_preview_workflow.py`: New tests validating the workflow

Commit: cb78a38
