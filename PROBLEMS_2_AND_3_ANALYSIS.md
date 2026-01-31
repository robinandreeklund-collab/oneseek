# Problems 2 & 3: Frontend Display Issues - Analysis and Fix Plan

## Problem 2: Frontend Shows "Filåtgärd: unknown" with Limited Content

### Current Behavior
- Sidebar displays: "Filåtgärd: unknown"
- Shows only: "Utdata: ✓ Successfully wrote 22 bytes to 'test.py'"
- Missing: Full conversation context, AI reasoning, tool invocations

### Expected Behavior
- Sidebar should show complete conversation
- Tool name should be "file_system_tool" not "unknown"
- All AI messages and tool calls should be visible in real-time

### Root Cause Analysis

The issue is likely in one of these areas:

**1. Tool Action Creation**
- When file_system_tool is invoked, a tool_action object should be created
- This object needs proper tool_name set
- If tool_name is missing or "unknown", frontend can't display it correctly

**2. Message Streaming**
- Backend streams messages to frontend via SSE (Server-Sent Events)
- Each AI message, tool call, and tool result should be streamed
- If only tool result is streamed, conversation context is lost

**3. Tool Result Handling**
- Tool results need to include not just output but full context
- Messages before and after tool execution should be included

### Investigation Areas

**Files to Check:**
1. `backend/deer_flow/graph/nodes.py` - coder_node implementation
2. `backend/deer_flow/server/app.py` - SSE streaming logic  
3. `backend/deer_flow/tools/code_tools.py` - file_system_tool
4. Frontend: `tool-action-detail-sidebar.tsx` - display logic

**Key Questions:**
- Where is tool_name set when file_system_tool is invoked?
- Are all messages being streamed or just final result?
- Is tool_action properly created with complete data?
- Does frontend receive all message types?

### Proposed Fix

**Backend Changes Needed:**
1. Ensure tool_name is set correctly in tool invocations
2. Stream all messages (AI reasoning, tool calls, results)
3. Include full conversation context in tool_action
4. Verify message format matches frontend expectations

**Investigation Steps:**
1. Trace code flow from coder_node through tool invocation
2. Check SSE streaming implementation  
3. Verify tool_action creation includes all required fields
4. Test with logging to see what data reaches frontend

## Problem 3: Files Tab Empty

### Current Behavior
- Backend logs show: "Tracking workspace file: test.py"
- Backend tracks files correctly in `_workspace_files_by_run` dict
- Frontend Files tab shows no files

### Expected Behavior
- Files created during coding should appear in Files tab
- Each file should show: name, path, operation (create/update), timestamp

### Root Cause Analysis

**The Disconnect:**
1. Backend tracks files: ✅ Working (logs confirm)
2. Files stored in memory: ✅ Working (_workspace_files_by_run)
3. Files attached to response: ❌ NOT HAPPENING
4. Frontend receives files: ❌ NO DATA

**Where It Breaks:**
- Files are tracked but never attached to the data sent to frontend
- `get_workspace_files()` exists but may not be called
- Tool action/response may not include workspace_files field

### Investigation Areas

**Key Code Locations:**
1. `backend/deer_flow/tools/code_tools.py`:
   - `track_workspace_file()` - ✅ Working
   - `get_workspace_files()` - ✅ Exists, needs to be called
   - Line 319: Tracking happens in file_system_tool

2. Response Creation:
   - Where is tool response/action created?
   - Where should `workspace_files = get_workspace_files(run_id)` be called?
   - How to attach workspace_files to response?

3. Streaming:
   - Are workspace_files included in streamed data?
   - Does SSE format include workspace_files field?

**Data Flow:**
```
file_system_tool writes file
  → track_workspace_file(file_info)
  → _workspace_files_by_run[run_id].append(file_info)
  
??? Should happen but doesn't ???
  → get_workspace_files(run_id)
  → attach to response/tool_action
  → stream to frontend
  → frontend Updates Files tab
```

### Proposed Fix

**Step 1: Find Response Creation Point**
- Locate where coder_node or tool invocation creates response
- This is where we need to call `get_workspace_files()`

**Step 2: Attach Workspace Files**
```python
# Pseudocode for fix
workspace_files = get_workspace_files(run_id)
response_data = {
    ...existing_fields,
    "workspace_files": workspace_files  # Add this
}
```

**Step 3: Ensure Streaming Includes Files**
- Verify SSE streaming sends workspace_files
- Frontend should receive updates when files are tracked

**Step 4: Frontend Verification**
- Check tool-action-detail-sidebar.tsx handles workspace_files
- Verify Files tab component receives and displays data

### Combined Fix Strategy

Both problems likely stem from the same root cause: **incomplete data in tool actions/responses**.

**Unified Fix:**
1. Locate where tool results are packaged for frontend
2. Ensure complete data is included:
   - Full conversation context (Problem 2)
   - Workspace files list (Problem 3)
   - Proper tool_name (Problem 2)
3. Verify streaming sends all data types
4. Test end-to-end

### Next Steps

**Immediate Actions:**
1. Search codebase for tool_action creation patterns
2. Find where responses are sent to frontend
3. Identify integration points for workspace_files
4. Implement fixes
5. Test with Test 1.1

**Success Criteria:**
- ✅ Sidebar shows full conversation with proper tool name
- ✅ Files tab displays all created files
- ✅ Real-time updates as files are created
- ✅ No "unknown" tool names

## Implementation Notes

The fixes for Problems 2 & 3 are interconnected and should be implemented together. The core issue is ensuring complete data reaches the frontend. This requires:

1. Backend code changes to attach data
2. Verification that streaming sends data
3. Testing to confirm frontend receives and displays data

These are non-trivial changes that require careful investigation of the backend codebase to find the correct integration points.

---

**Status:** Investigation phase
**Priority:** High - blocks Test 1.1 completion
**Complexity:** Medium-High - requires understanding backend streaming architecture
