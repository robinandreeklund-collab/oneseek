# Workspace Nesting and VLLM Crash Fixes

## Overview

This document explains the fixes for workspace directory nesting issues and VLLM crashes caused by code planner creating testing steps.

## Problem 1: Workspace Directory Nesting

### Issue

User's `.env` configuration had workspace directories pointing **into each other**, creating nested directory structures:

```bash
CODE_WORKSPACE_ROOT=C:\Users\robin\oneseek_react_sandboxes
REACT_SANDBOX_ROOT=C:\Users\robin\oneseek_workspace
```

This created confusing nested paths:
- `C:\Users\robin\oneseek_workspace\oneseek_react_sandboxes\todo-app`
- `C:\Users\robin\oneseek_react_sandboxes\oneseek_workspace\oneseek_react_sandboxes`

### Why This Causes Problems

1. **File Creation Confusion**: Model creates files in multiple locations
2. **Path Resolution Errors**: Can't find files it just created
3. **Recursive Directory Creation**: Leads to deeply nested structures
4. **Workspace Boundary Issues**: Security restrictions don't work properly

### Solution

Workspace directories should be **sibling directories**, not nested:

**Option 1: Direct Siblings**
```bash
CODE_WORKSPACE_ROOT=C:\Users\robin\oneseek_workspace
REACT_SANDBOX_ROOT=C:\Users\robin\oneseek_react_sandboxes
```

**Option 2: Under Common Parent**
```bash
CODE_WORKSPACE_ROOT=C:\Users\robin\workspaces\code
REACT_SANDBOX_ROOT=C:\Users\robin\workspaces\react
```

**Option 3: Completely Separate**
```bash
CODE_WORKSPACE_ROOT=C:\Users\robin\oneseek_workspace
REACT_SANDBOX_ROOT=D:\projects\react_sandboxes
```

### Directory Structure After Fix

```
C:\Users\robin\
├── oneseek_workspace\           ← CODE_WORKSPACE_ROOT
│   ├── workspace_venv\          ← Python venv
│   ├── my_flask_app\
│   │   ├── app.py
│   │   └── routes.py
│   └── ...
└── oneseek_react_sandboxes\     ← REACT_SANDBOX_ROOT (sibling)
    ├── todo-app\
    │   ├── src\
    │   └── package.json
    └── ...
```

## Problem 2: VLLM Crashes from Testing Steps

### Issue

Code Planner was creating testing steps in plans despite "DO NOT USE" warnings:

```json
{
  "steps": [
    {"title": "Research Flask", "step_type": "research"},
    {"title": "Implement API", "step_type": "processing"},
    {"title": "Test with pytest", "step_type": "testing"},  ← Causing crash!
    {"title": "Validate quality", "step_type": "testing"}    ← Causing crash!
  ]
}
```

### Why This Causes VLLM Crashes

1. **Too Many Sequential Operations**: Research + Implement + Test + Validate = 4+ agent calls
2. **Large Context Windows**: Each step accumulates more context
3. **Memory Pressure**: VLLM server runs out of memory
4. **Server Disconnect**: VLLM crashes with "Server disconnected" error

### Solution

**Completely removed testing step type from code planner prompts** (Commit 9be091e):

**Before:**
```markdown
### Testing Steps (`step_type: "testing"`) - **DO NOT USE**
- **IMPORTANT: Do NOT create testing steps**
- Testing handled separately
```

**After:**
```markdown
(Section completely removed)

**Note on Testing:** Testing is NOT included in plans.
Valid step types: "research", "processing", "analysis" ONLY
```

### Expected Behavior After Fix

Code Planner now creates lean plans:

```json
{
  "steps": [
    {"title": "Research Flask patterns", "step_type": "research"},
    {"title": "Implement REST API", "step_type": "processing"}
  ]
}
```

After coding completes → Human feedback asks: "Vill du att jag testar koden?" → User decides.

## Related Fixes

### Human Feedback Flag Fix (Commit e80dbd2)

**Problem:** `coder_just_completed` flag not persisting to human_feedback_node

**Solution:** Create new dict with spread operator instead of mutating:
```python
# Before (didn't persist)
result.update["coder_just_completed"] = True

# After (persists correctly)
updated_state = {
    **result.update,
    "coder_just_completed": True
}
return Command(update=updated_state, goto="human_feedback")
```

### Windows Path Escaping Fix (Earlier Commits)

**Problem:** Agent used `'C:\Users\path'` causing unicodeescape errors

**Solution:** Added guidance showing 3 correct approaches:
- Raw strings: `r'C:\Users\path'` (recommended)
- Forward slashes: `'C:/Users/path'` (cross-platform)
- Double backslashes: `'C:\\Users\\path'`

## Testing Instructions

### 1. Fix Workspace Configuration

Edit `backend/.env`:
```bash
# Change from nested:
CODE_WORKSPACE_ROOT=C:\Users\robin\oneseek_react_sandboxes
REACT_SANDBOX_ROOT=C:\Users\robin\oneseek_workspace

# To sibling directories:
CODE_WORKSPACE_ROOT=C:\Users\robin\oneseek_workspace
REACT_SANDBOX_ROOT=C:\Users\robin\oneseek_react_sandboxes
```

### 2. Clean Up Nested Directories (Optional)

Remove any nested workspace directories that were created:
```bash
# Remove nested structures if they exist
rm -rf C:\Users\robin\oneseek_workspace\oneseek_react_sandboxes
rm -rf C:\Users\robin\oneseek_react_sandboxes\oneseek_workspace
```

### 3. Restart Backend

```bash
# Stop backend
# Start backend again to load new .env
```

### 4. Test Complex Code Task

Run a complex code task:
```
"Bygg ett Tic-Tac-Toe spel med Python och grafiskt gränssnitt"
```

**Expected Behavior:**
1. ✅ Code Planner creates plan with NO testing steps
2. ✅ Only "research" and "processing" steps
3. ✅ Coder executes without VLLM crash
4. ✅ Files created in single workspace location
5. ✅ Human feedback prompt appears: "Vill du att jag testar koden?"
6. ✅ User can choose [TEST] or [SKIP]

### 5. Verify Logs

Check terminal logs for:
```
[coder_node] Setting coder_just_completed=True
Coder completed, routing to human_feedback to ask about testing
[human_feedback_node] ENTERED - coder_just_completed=True
[human_feedback_node] Calling interrupt() with prompt...
```

## Troubleshooting

### Issue: Still seeing testing steps in plan

**Solution:** Backend restart required for prompt changes to take effect

### Issue: Human feedback not appearing

**Check logs for:** `coder_just_completed=True`

If `False`, ensure you've pulled latest commits (e80dbd2 and later)

### Issue: Files in wrong locations

**Check:** Workspace directories are siblings, not nested

**Verify paths don't contain both workspace names:**
- ❌ `oneseek_workspace\oneseek_react_sandboxes\...`
- ✅ `oneseek_workspace\my_project\...`

### Issue: VLLM still crashing

**Check plan for testing steps:** If present, backend needs restart

**Check plan complexity:** Should be 1-3 steps max

## Files Modified

1. `backend/deer_flow/prompts/code_planner.md` - Removed testing step type
2. `backend/deer_flow/prompts/code_planner.sv_SE.md` - Removed testing step type (Swedish)
3. `backend/deer_flow/graph/nodes.py` - Fixed flag persistence + added logging
4. `backend/deer_flow/prompts/coder.md` - Added Windows path handling
5. `backend/deer_flow/prompts/coder.sv_SE.md` - Added Windows path handling (Swedish)

## Summary

All code fixes are complete. User must:
1. ✅ Update .env to use sibling workspace directories
2. ✅ Restart backend
3. ✅ Test with complex code task

Expected: No VLLM crashes, clean workflows, human feedback prompts working!
