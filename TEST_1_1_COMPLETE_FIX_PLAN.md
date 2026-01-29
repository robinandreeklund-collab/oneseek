# Test 1.1 Complete Fix Plan

## Three Problems to Fix

### Problem 1: Model Creating workspace_requirements.txt
**Issue:** Model created `workspace_requirements.txt` in workspace instead of using existing venv.

**Root Cause:**
- Prompts mention workspace_requirements.txt as something to use
- Not emphatic enough that venv ALREADY EXISTS
- No explicit warning against creating requirements files

**Fix:**
1. Add prominent warning in coder prompts: "⚠️ NEVER create requirements.txt or setup.py"
2. Emphasize venv is pre-configured and ready
3. Remove references to creating requirements files in tester prompts
4. Add note: "If packages missing, report to user - don't try to install"

### Problem 2: Frontend Shows Limited Info ("Filåtgärd: unknown")
**Issue:** Sidebar displays minimal content instead of full conversation.

**Root Cause Analysis Needed:**
- Check how tool_action is created in coder_node
- Verify tool_name is set correctly
- Ensure all AI messages are included in response
- Check streaming updates include context

**Investigation Areas:**
- `backend/deer_flow/graph/nodes.py` - coder_node implementation
- `backend/deer_flow/server/app.py` - streaming response handling
- Tool invocation and result handling

**Possible Fixes:**
- Ensure tool_name is set (not left as "unknown")
- Include all conversation messages in tool_action
- Verify streaming updates send complete context

### Problem 3: Files Tab Empty
**Issue:** Workspace files tracked but not appearing in frontend.

**Root Cause Analysis:**
- workspace_files tracked correctly in backend (logs confirm)
- Not attached to tool_action or not sent to frontend
- Frontend may not be parsing workspace_files

**Investigation:**
- Check where workspace_files should be attached to response
- Verify get_workspace_files() is called when creating response
- Ensure workspace_files included in streaming data

**Fix Strategy:**
1. Find where tool_action/response is created for file_system_tool
2. Call get_workspace_files() and attach to response
3. Ensure workspace_files is in the data sent to frontend
4. Verify frontend Files tab component can parse the data

## Implementation Order

**Phase 1: Prompt Fixes (Problem 1)** - Quickest win
- Update coder.md and coder.sv_SE.md
- Add warnings about NOT creating requirements files
- Emphasize venv is ready to use

**Phase 2: Backend Investigation (Problems 2 & 3)**
- Examine coder_node and tool invocation
- Find where responses are constructed
- Identify why tool_name might be "unknown"
- Find where workspace_files should be attached

**Phase 3: Backend Fixes**
- Fix tool_name setting
- Attach workspace_files to responses
- Ensure complete context in responses

**Phase 4: Verification**
- Test file creation
- Verify sidebar shows full conversation
- Verify Files tab shows created files
- Confirm no requirements files created

## Success Criteria

✅ **Problem 1 Fixed:** No workspace_requirements.txt or requirements.txt created by model
✅ **Problem 2 Fixed:** Sidebar shows full conversation, not "Filåtgärd: unknown"
✅ **Problem 3 Fixed:** Files tab displays all created files

## Testing

After fixes:
1. Restart backend
2. Run Test 1.1: "Skapa en Python-fil som heter test.py med en enkel print-funktion"
3. Verify:
   - File created at `C:\Users\robin\oneseek_react_sandboxes\test.py`
   - NO requirements files created
   - Sidebar shows full conversation with tool name
   - Files tab shows test.py

## Files to Modify

1. `backend/deer_flow/prompts/coder.md` - Add warnings
2. `backend/deer_flow/prompts/coder.sv_SE.md` - Add warnings
3. Backend code (TBD based on investigation) - Fix tool_name and workspace_files
