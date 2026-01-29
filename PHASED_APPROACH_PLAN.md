# Phased Approach to Fix Workspace and File Tracking

## Overview

This document outlines a step-by-step approach to fix issues with the coder tool, focusing on workspace management, file tracking, venv handling, and human feedback loops.

## User's Request (Comment #3814214251)

> "Kan vi göra en plan för att stegvis gå igenom coder och dess verktyg en för en?"

Focus areas:
1. **Phase 1**: Workspace - files created in correct location, file tracking, Files tab working
2. **Phase 2**: Venv activation and correct usage
3. **Phase 3**: Human feedback loop functionality

## Current Issues Analysis

### From Terminal Log (smhi.yaml)

1. Files being created but not consistently tracked
2. Model doesn't always know where files are located
3. Files tab in sidebar not populating with created files
4. Possible confusion between CODE_WORKSPACE_ROOT and REACT_SANDBOX_ROOT
5. Path resolution issues on Windows

### Current Code Assessment

**What's Working:**
- ✅ `track_workspace_file()` function exists and implemented correctly
- ✅ Run-scoped storage for file tracking
- ✅ Files are tracked on write operations (line 319 in code_tools.py)
- ✅ CODE_WORKSPACE_ROOT environment variable is used

**What Needs Improvement:**
- ⚠️ Only relative paths are logged, not full absolute paths
- ⚠️ Workspace root usage not always clear in logs
- ⚠️ Coder prompts don't emphasize workspace consistency enough
- ⚠️ Model may not be aware that files are being tracked
- ⚠️ Tool output doesn't confirm absolute path where file was created

## Phase 1: Workspace and File Tracking

### Goals

1. Ensure all files are created in the correct workspace location
2. Improve file tracking visibility and logging
3. Make sure Files tab in UI shows created files
4. Model always knows where files are located

### Implementation Steps

#### Step 1: Enhanced Logging in code_tools.py

**Changes:**
- Log full absolute path when files are created/modified
- Log which workspace root is being used at tool invocation
- Add summary after file operations showing all tracked files
- Include workspace root in track_workspace_file calls

**Code Location:** `backend/deer_flow/tools/code_tools.py`
- Lines 283-284: Add logging for workspace root
- Line 299: Log full absolute path
- Line 319: Pass absolute path to track_workspace_file
- Line 321: Include absolute path in success message

#### Step 2: Improve Coder Prompts

**Changes:**
- Add new "Workspace Management" section
- Emphasize always using CODE_WORKSPACE_ROOT correctly
- Document that file tracking happens automatically
- Show examples of correct workspace usage
- Warn about path resolution on Windows

**Files:**
- `backend/deer_flow/prompts/coder.md` (English)
- `backend/deer_flow/prompts/coder.sv_SE.md` (Swedish)

#### Step 3: Enhanced Tool Output

**Changes:**
- file_system_tool returns absolute path in success messages
- Confirms which workspace root was used
- Makes it explicitly clear where files were created

#### Step 4: Documentation

**Create:** `WORKSPACE_FILE_TRACKING_GUIDE.md`

Include:
- How file tracking works
- Expected log output examples
- Troubleshooting common issues
- How to verify Files tab is working

### Expected Behavior After Phase 1

**When model creates a file:**

1. Model calls: `file_system_tool(operation="write", path="app.py", content="...")`
2. Tool logs:
   ```
   [file_system_tool] Using workspace root: C:\Users\robin\oneseek_react_sandboxes\oneseek_workspace
   [file_system_tool] Writing file: app.py
   [file_system_tool] Full absolute path: C:\Users\robin\oneseek_react_sandboxes\oneseek_workspace\app.py
   ```
3. Tool tracks: `track_workspace_file(absolute_path, "write", size, content)`
4. Tool logs:
   ```
   [track_workspace_file] Tracking workspace file: C:\Users\robin\oneseek_react_sandboxes\oneseek_workspace\app.py
   [track_workspace_file] Current workspace files count: 1
   ```
5. Tool returns: `"✓ Successfully wrote 1234 bytes to 'app.py' at C:\Users\robin\oneseek_react_sandboxes\oneseek_workspace\app.py"`
6. File appears in Files tab in UI

### Success Criteria

- ✅ All log messages include full absolute paths
- ✅ Workspace root is clearly logged and used consistently
- ✅ Model receives absolute path in tool responses
- ✅ Files appear in Files tab reliably
- ✅ No confusion about where files are located

## Phase 2: Venv Management (Future Commit)

### Goals

1. Ensure Windows venv path is used correctly every time
2. Validate venv exists before attempting to use it
3. Better error messages when venv issues occur
4. Model always activates/uses venv properly

### Implementation Steps

1. Add venv validation function
2. Update coder prompts with explicit venv usage patterns
3. Check venv exists before operations that need it
4. Log venv path being used
5. Better error messages for missing venv

### Expected Behavior

- Model consistently uses: `C:\Users\robin\oneseek_react_sandboxes\workspace_venv\Scripts\python.exe`
- Validation happens before subprocess calls
- Clear error if venv not found
- No attempts to "activate" in subprocess.run()

## Phase 3: Human Feedback Loop (Future Commit)

### Goals

1. Debug why interrupt() isn't showing in UI
2. Ensure state propagation works correctly
3. Test complete flow: coder → human feedback → test plan

### Implementation Steps

1. Add more detailed logging around interrupt() calls
2. Verify LangGraph interrupt configuration
3. Check WebSocket connection for interrupt messages
4. Test state flag propagation end-to-end
5. Verify UI is listening for interrupt events

### Expected Behavior

- After coder completes, UI shows prompt
- User can respond with [TEST] or [SKIP]
- If [TEST], code planner creates test plan
- Test plan appears for approval
- Flow completes successfully

## Timeline

### Immediate (This Session)

- ✅ Create this plan document
- ⏳ Implement Phase 1 enhancements
- ⏳ Test Phase 1 with simple file creation
- ⏳ Document Phase 1 results

### Next Session

- Phase 2: Venv management improvements
- Test Phase 2 with code that uses venv

### Following Session

- Phase 3: Human feedback loop debugging
- End-to-end testing of complete flow

## Testing Strategy

### Phase 1 Testing

1. Restart backend
2. Ask model: "Skapa en Python-fil app.py med en enkel funktion"
3. Check logs for:
   - Workspace root logged
   - Full absolute path logged
   - File tracking confirmation
4. Check UI Files tab shows app.py
5. Ask model: "Vilka filer har du skapat?"
6. Verify model knows the absolute path

### Phase 2 Testing

1. Restart backend
2. Ask model: "Skapa en Flask app och kör den"
3. Check logs for:
   - Venv validation
   - Correct venv path used
4. Verify no subprocess activation errors
5. Verify code runs successfully

### Phase 3 Testing

1. Restart backend
2. Ask model: "Skapa ett Tic-Tac-Toe spel"
3. Wait for coding to complete
4. Verify human feedback prompt appears in UI
5. Reply [TEST]
6. Verify test plan is created
7. Approve test plan
8. Verify tests run

## Rollback Plan

If any phase causes issues:

1. Document the specific problem
2. Revert the commits for that phase
3. Analyze logs to understand root cause
4. Adjust approach and try again

Each phase is independent, so issues in one phase don't affect the others.

## Success Metrics

### Phase 1 Success

- Zero file location confusion errors
- 100% of created files appear in Files tab
- Model always knows absolute paths of files it created
- Logs are clear and detailed

### Phase 2 Success

- Zero venv path errors
- All code execution uses correct venv
- Clear error messages if venv missing
- No "activation" errors in subprocess

### Phase 3 Success

- Human feedback prompt appears 100% of time after coder
- User can successfully approve/decline testing
- Test plans are created when requested
- Complete flow works end-to-end

## Notes

- Backend restart required after each phase implementation
- Each phase builds on previous phases
- User testing and feedback incorporated between phases
- Documentation updated as we learn from each phase
