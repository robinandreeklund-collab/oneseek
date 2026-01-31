# Frontend Display Issues - Root Cause Analysis

## Problem Statement (Comment #3816196607)

User reports that frontend shows very limited information in the code sidebar while backend logs show model doing much more work.

### Observed Issues

1. **"Filåtgärd: unknown"** - Tool action type shows as "unknown" instead of proper tool name
2. **Empty "Kör Python-kod" section** - Tool input/code section is empty or collapsed
3. **Only "Utdata" shown** - Only final output displayed, missing intermediate steps
4. **Empty "Filer" tab** - No files shown despite model creating files (tracked in backend)

### What Backend Shows vs Frontend

**Backend logs show:**
```
backend.deer_flow.tools.code_tools - INFO - File system operation: write on C:\Users\robin\oneseek_react_sandboxes\app.py
backend.deer_flow.tools.code_tools - INFO - [run_id=default] Tracking workspace file: app.py, operation: write
backend.deer_flow.tools.code_tools - INFO - [run_id=default] Current workspace files count: 1
backend.deer_flow.tools.decorators - INFO - Tool file_system_tool returned: ✓ Successfully wrote 402 bytes to 'app.py'
backend.deer_flow.tools.decorators - INFO - Tool python_repl_tool called with parameters: code=import subprocess...
```

**Frontend shows:**
- Filåtgärd: unknown
- Kör Python-kod: (empty/collapsed)
- Utdata: "✓ Successfully wrote 402 bytes to 'app.py'" (partial)

## Root Cause Analysis

### Issue 1: "Filåtgärd: unknown"

**Location:** `backend/agent_graph.py` lines 441, 632

**Code:**
```python
tool_name = tc.get("name", "unknown")
```

**Root Cause:**
- Tool call dictionary `tc` doesn't have "name" field populated
- Falls back to default value "unknown"
- Need to investigate why tool_calls structure lacks name field

**Investigation Needed:**
- Check how tools are invoked from LangChain
- Verify tool_call structure in LLM response
- Ensure tool name is preserved through invocation chain

### Issue 2: Empty "Kör Python-kod" Section

**Location:** Tool input should be in tool_action structure

**Code (agent_graph.py lines 442, 454-458):**
```python
tool_input = tc.get("args", {})
# ...
"input": tool_input,
"raw_request": {
    "tool": tool_name,
    "arguments": tool_input,
    "call_id": tool_call_id
}
```

**Root Cause:**
- Backend correctly includes `tool_input` in tool_action
- Data structure includes both "input" and "raw_request" with complete arguments
- Frontend component may not be rendering the input section
- Could be collapsed/hidden in UI

**Investigation Needed:**
- Check frontend tool-action-detail-sidebar.tsx component
- Verify if input field is being parsed and displayed
- Check if section is collapsed by default

### Issue 3: Only "Utdata" Shown

**Location:** Multiple tool invocations should all be visible

**Code (agent_graph.py lines 466, 511, 657, 702):**
```python
callback("tool_action", tool_action)  # Sent for each tool invocation
```

**Root Cause:**
- Each tool invocation triggers callback with complete tool_action
- Multiple tool calls should result in multiple entries
- Frontend may only show latest/final tool action
- Intermediate steps might be hidden or overwritten

**Investigation Needed:**
- Check how frontend accumulates multiple tool_actions
- Verify SSE streaming sends all tool_action events
- Check if frontend displays history of tool invocations

### Issue 4: Empty "Filer" Tab

**Location:** `backend/agent_graph.py` lines 502-506, 693-699

**Code:**
```python
# Add workspace files if any were tracked
logger.info("Getting workspace files for tool action")
workspace_files = get_workspace_files()
logger.info(f"Retrieved {len(workspace_files)} workspace files")
if workspace_files:
    tool_action["workspace_files"] = workspace_files
    logger.info(f"Attaching {len(workspace_files)} workspace files to tool action: {[f['path'] for f in workspace_files]}")
```

**Root Cause:**
- Backend correctly attaches workspace_files to tool_action
- Data structure: `tool_action["workspace_files"]` contains list of file objects
- Files tracked via `track_workspace_file()` in code_tools.py
- Frontend Files tab component not receiving or not parsing this data

**Investigation Needed:**
- Verify workspace_files is included in SSE stream
- Check frontend Files tab component
- Verify data structure matches frontend expectations
- Check if Files tab queries different data source

## Data Flow

### Backend (Working Correctly)

```
1. Tool Call → Agent Graph
   ├─ Extract tool name: tc.get("name", "unknown")  ← ISSUE: Falls to "unknown"
   ├─ Extract tool input: tc.get("args", {})  ← OK
   ├─ Create tool_action structure  ← OK
   └─ Send via callback("tool_action", ...)  ← OK

2. Tool Execution → ToolNode
   ├─ Execute tool (file_system_tool, python_repl_tool, etc.)  ← OK
   ├─ Track workspace files via track_workspace_file()  ← OK
   └─ Return ToolMessage with result  ← OK

3. Result Processing → Agent Graph
   ├─ Get workspace_files via get_workspace_files()  ← OK
   ├─ Attach to tool_action["workspace_files"]  ← OK
   ├─ Update tool_action with output  ← OK
   └─ Send updated via callback("tool_action", ...)  ← OK

4. SSE Streaming → Server
   └─ Stream tool_action to frontend  ← Needs verification
```

### Frontend (Issues)

```
1. Receive SSE Event
   └─ Parse tool_action data  ← Needs verification

2. Display in Sidebar
   ├─ Tool name: Shows "unknown"  ← ISSUE
   ├─ Tool input: Not displayed  ← ISSUE
   ├─ Tool output: Shows partial  ← ISSUE
   └─ Intermediate steps: Hidden  ← ISSUE

3. Files Tab
   └─ workspace_files: Not displayed  ← ISSUE
```

## Proposed Investigation Steps

### Step 1: Verify Tool Name in Tool Calls

**Check:**
- LLM response structure
- tool_call_chunks in AIMessageChunk
- Consolidated tool_calls in AIMessage

**Log Points:**
- `backend/deer_flow/server/app.py` lines 439-441
- Before `tc.get("name", "unknown")` call

### Step 2: Verify SSE Streaming

**Check:**
- `_astream_workflow_generator` function
- How callback events are converted to SSE
- Complete tool_action structure in stream

**Test:**
- Add logging to see exact JSON sent to frontend
- Verify workspace_files included in stream

### Step 3: Verify Frontend Parsing

**Check:**
- `tool-action-detail-sidebar.tsx` component
- How tool_action events are processed
- Data binding for all fields

**Test:**
- Frontend console logs
- Verify all fields received
- Check rendering logic

### Step 4: Test Data Round Trip

**Create test:**
1. Trigger simple file creation
2. Log tool_action at backend creation
3. Log tool_action in SSE stream
4. Log tool_action received by frontend
5. Compare structures at each step

## Success Criteria

After fixes, frontend should show:

✅ **Correct tool name**: "file_system_tool", "python_repl_tool", etc.
✅ **Tool input section**: Full code/parameters visible
✅ **All tool invocations**: Complete history of steps
✅ **Files tab populated**: List of created workspace files

## Next Steps

1. Add comprehensive logging to track tool_name through complete flow
2. Verify SSE streaming includes all tool_action fields
3. Check frontend component rendering logic
4. Test with simple file creation scenario
5. Document exact data structure at each step

## Related Files

**Backend:**
- `backend/agent_graph.py` - Tool action creation (lines 437-511, 628-702)
- `backend/deer_flow/server/app.py` - SSE streaming
- `backend/deer_flow/tools/code_tools.py` - File tracking

**Frontend:**
- Frontend components (need investigation)

## Summary

The backend is correctly:
- Creating tool_action structures
- Tracking workspace files
- Sending data via callbacks

The issues are:
- Tool name extraction falling back to "unknown"
- Frontend not displaying all tool_action fields
- Frontend Files tab not showing workspace_files

This requires full-stack debugging from tool invocation through SSE streaming to frontend rendering.
