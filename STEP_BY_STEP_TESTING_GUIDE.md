# Step-by-Step Testing Guide

## Purpose

This guide provides specific test questions to validate each feature of the coder system incrementally. Test each phase in order, checking off passing tests, and report any failures with the specific test number.

## How to Use

1. **Restart backend** before starting
2. **Test Phase 1** completely before moving to Phase 2
3. **Check off** each passing test (✓)
4. **If test fails:** Stop and report "Phase X Test Y.Z failed: [reason]"
5. **Continue** to next phase only after current phase passes

## Reporting Format

- ✓ "Phase 1 complete - all tests passed"
- ✗ "Phase 2 Test 2.2 failed - files not appearing in sidebar"
- ⏸ "Stopped at Phase 3 Test 3.1 - Windows path error in logs"

---

## Phase 1: Basic File Creation

Test core file creation functionality.

### Test 1.1: Create Single Python File

**Question:** "Skapa en Python-fil som heter test.py med en enkel print-funktion"

**Expected Behavior:**
- File created in workspace root
- File contains a print function
- File appears in Files tab in sidebar

**Success Criteria:**
- ✓ File exists at: `C:\Users\robin\oneseek_react_sandboxes\test.py`
- ✓ Content includes `def` or `print`
- ✓ Files tab shows "test.py"

**Logs to Check:**
```
[file_system_tool] Writing file: test.py
[track_workspace_file] Tracking workspace file: test.py
```

**Troubleshooting:**
- Check workspace root in logs
- Verify `.env` configuration
- Look for write permissions errors

---

### Test 1.2: Create Multiple Files

**Question:** "Skapa två Python-filer: calculator.py med add/subtract funktioner och utils.py med helper funktioner"

**Expected Behavior:**
- Two files created
- Both in workspace root
- Both appear in Files tab

**Success Criteria:**
- ✓ `calculator.py` exists with add/subtract
- ✓ `utils.py` exists with helper functions
- ✓ Both files show in sidebar

**Logs to Check:**
```
[file_system_tool] Writing file: calculator.py
[file_system_tool] Writing file: utils.py
[track_workspace_file] Current workspace files count: 2
```

---

### Test 1.3: Create File in Subdirectory

**Question:** "Skapa en mapp 'utils' och i den en fil helpers.py med string funktioner"

**Expected Behavior:**
- Directory `utils/` created
- File created inside: `utils/helpers.py`
- File shows in Files tab

**Success Criteria:**
- ✓ Directory exists: `C:\Users\robin\oneseek_react_sandboxes\utils\`
- ✓ File exists: `C:\Users\robin\oneseek_react_sandboxes\utils\helpers.py`
- ✓ Shows in sidebar as "utils/helpers.py"

**Logs to Check:**
```
[file_system_tool] Creating directory: utils
[file_system_tool] Writing file: utils/helpers.py
```

---

## Phase 2: Workspace Consistency

Verify files are created in correct workspace location.

### Test 2.1: Verify Workspace Root Usage

**Question:** "Skapa en fil config.py och visa mig den absoluta sökvägen"

**Expected Behavior:**
- File created in `CODE_WORKSPACE_ROOT`
- Path shown in response
- No nested `oneseek_workspace` directories

**Success Criteria:**
- ✓ Path is: `C:\Users\robin\oneseek_react_sandboxes\config.py`
- ✓ NOT: `C:\Users\robin\oneseek_workspace\oneseek_react_sandboxes\...`
- ✓ Response includes correct full path

**Logs to Check:**
```
[file_system_tool] Using workspace root: C:\Users\robin\oneseek_react_sandboxes
[file_system_tool] Full path: C:\Users\robin\oneseek_react_sandboxes\config.py
```

---

### Test 2.2: File Tracking Verification

**Question:** "Skapa en fil data.json med exempel data"

**Expected Behavior:**
- File created
- File tracked in workspace_files
- Count increments correctly

**Success Criteria:**
- ✓ File created successfully
- ✓ Logs show tracking
- ✓ File count in logs is correct

**Logs to Check:**
```
[track_workspace_file] Tracking workspace file: data.json
[track_workspace_file] Current workspace files count: X
```

---

### Test 2.3: Files Tab Display

**Question:** "Skapa tre filer: app.py, models.py, views.py"

**Expected Behavior:**
- All three files created
- All appear in Files tab
- Names and paths correct

**Success Criteria:**
- ✓ Files tab shows all 3 files
- ✓ Clicking shows file preview
- ✓ Paths are correct in sidebar

**UI Check:**
- Open Code sidebar
- Click "Files" tab
- Verify all 3 files listed

---

## Phase 3: Windows Path Handling

Test that Windows paths don't cause SyntaxErrors.

### Test 3.1: Raw String Usage

**Question:** "Skapa en Python-fil som lägger till workspace path i sys.path och importerar en modul"

**Expected Behavior:**
- Uses raw string: `r'C:\Users\...'`
- OR uses forward slashes: `'C:/Users/...'`
- No SyntaxError about `\U` escape

**Success Criteria:**
- ✓ Code contains `r'` or forward slashes
- ✓ No unicodeescape error
- ✓ sys.path.append works correctly

**Look For:**
```python
# Correct:
sys.path.append(r'C:\Users\robin\oneseek_react_sandboxes')
# OR:
sys.path.append('C:/Users/robin/oneseek_react_sandboxes')
```

**NOT:**
```python
# Incorrect:
sys.path.append('C:\Users\robin\oneseek_react_sandboxes')  # ✗ Will error
```

---

### Test 3.2: File Path Operations

**Question:** "Skriv Python-kod som använder os.path.join för att skapa en path till workspace"

**Expected Behavior:**
- Uses os.path.join correctly
- Handles Windows paths properly
- No path escape errors

**Success Criteria:**
- ✓ Code uses `os.path.join()`
- ✓ Base path uses raw string
- ✓ Executes without error

---

### Test 3.3: Import with Workspace Path

**Question:** "Skapa två filer: mymodule.py med en funktion och main.py som importerar från mymodule"

**Expected Behavior:**
- Both files created
- main.py adds workspace to sys.path correctly
- Import works without path errors

**Success Criteria:**
- ✓ Both files exist
- ✓ sys.path.append uses correct format
- ✓ Import succeeds

---

## Phase 4: Venv Usage

Test that pre-configured venv is used correctly.

### Test 4.1: Flask App with Venv

**Question:** "Skapa en enkel Flask app.py med en hello world route"

**Expected Behavior:**
- File created with Flask code
- Uses venv Python path if executing
- Flask imported successfully

**Success Criteria:**
- ✓ File contains `from flask import Flask`
- ✓ If executed, uses workspace_venv Python
- ✓ No "Module not found" errors

**Logs to Check:**
```
Using venv python: C:\Users\robin\oneseek_react_sandboxes\workspace_venv\Scripts\python.exe
```

---

### Test 4.2: Script Execution with Venv

**Question:** "Skapa ett Python-script som använder requests biblioteket och kör det"

**Expected Behavior:**
- Script created with `import requests`
- Executed using venv Python
- No installation attempts

**Success Criteria:**
- ✓ Script contains `import requests`
- ✓ Execution uses venv path
- ✓ No pip install commands run
- ✓ No "Module not found" error

**Logs Should NOT Show:**
```
pip install requests  # Should NOT appear
```

**Logs SHOULD Show:**
```
C:\Users\robin\oneseek_react_sandboxes\workspace_venv\Scripts\python.exe script.py
```

---

### Test 4.3: Multiple Package Usage

**Question:** "Skapa en fil som importerar både flask och requests och använder dem"

**Expected Behavior:**
- Bothpackages imported
- No installation needed
- Code runs successfully

**Success Criteria:**
- ✓ Both `flask` and `requests` imported
- ✓ No pip install commands
- ✓ Code executes without errors

---

## Phase 5: Code Planner Integration

Test planning and execution flow.

### Test 5.1: Simple Code Task (Direct to Coder)

**Question:** "Skriv en Python-funktion som beräknar Fibonacci-tal"

**Expected Behavior:**
- Goes directly to coder (no planner)
- Creates single file
- Function implemented correctly

**Success Criteria:**
- ✓ No plan creation step
- ✓ File created immediately
- ✓ Fibonacci function works

**Logs Should Show:**
```
[coordinator] Routing to: coder
```

**NOT:**
```
[coordinator] Routing to: code_planner  # Should NOT for simple task
```

---

### Test 5.2: Complex Multi-File Task

**Question:** "Bygg ett Tic-Tac-Toe spel med Python och grafiskt gränssnitt"

**Expected Behavior:**
- Routes to code_planner first
- Plan shows ONLY implementation steps
- NO testing steps in plan

**Success Criteria:**
- ✓ Plan created with steps
- ✓ Steps are "research" and "processing" only
- ✓ NO "testing" step type
- ✓ Plan shows file structure

**Plan Should Look Like:**
```json
{
  "steps": [
    {"step_type": "research", "title": "Research Python GUI libraries"},
    {"step_type": "processing", "title": "Implement game logic"},
    {"step_type": "processing", "title": "Create GUI"}
  ]
}
```

**NOT:**
```json
{
  "steps": [
    ...
    {"step_type": "testing", "title": "Test game"} // ✗ Should NOT appear
  ]
}
```

---

### Test 5.3: Plan Review and Approval

**Question:** (After plan is shown) Reply: "[ACCEPTED]"

**Expected Behavior:**
- Plan execution begins
- Research team activates
- Coder implements according to plan

**Success Criteria:**
- ✓ Plan accepted successfully
- ✓ Implementation starts
- ✓ Files created as planned

**Logs to Check:**
```
[human_feedback_node] User approved plan
[research_team] Starting execution
[coder] Implementing step X
```

---

## Phase 6: Human Feedback Loop

Test the testing prompt after coding.

### Test 6.1: Prompt Appears After Coding

**Question:** (Use a complex task that goes through code_planner)
"Skapa en Flask REST API med två endpoints"

**Expected Behavior:**
- Code implementation completes
- Human feedback prompt appears
- Prompt asks about testing

**Success Criteria:**
- ✓ Coding completes successfully
- ✓ Prompt shows: "Kodningen är klar! Vill du att jag testar koden?"
- ✓ Options shown: [TEST] [SKIP]

**Logs to Check:**
```
[coder_node] Setting coder_just_completed=True in update dict
Coder completed, routing to human_feedback to ask about testing
[human_feedback_node] ENTERED - coder_just_completed=True
[human_feedback_node] Coder just completed. Asking user about testing.
[human_feedback_node] Calling interrupt() with prompt (locale=sv-SE): Kodningen är klar...
```

**If This Fails:**
- Backend might not be restarted
- Check logs for flag value
- Verify state propagation

---

### Test 6.2: Accept Testing Option

**Question:** (After prompt appears) Reply: "[TEST]"

**Expected Behavior:**
- System acknowledges
- Routes to code_planner in testing mode
- Test plan created

**Success Criteria:**
- ✓ Response acknowledged
- ✓ Testing mode activated
- ✓ Test plan generated

**Logs to Check:**
```
[human_feedback_node] User chose to create test plan
[code_planner] Testing mode: True
[code_planner] Creating test plan for: ...
```

---

### Test 6.3: Skip Testing Option

**Question:** (In a different task, after coding completes) Reply: "[SKIP]"

**Expected Behavior:**
- System acknowledges
- Skips testing
- Goes to reporter/completion

**Success Criteria:**
- ✓ Testing skipped
- ✓ Task marked complete
- ✓ No test plan created

**Logs to Check:**
```
[human_feedback_node] User chose to skip testing
[reporter] Generating final report
```

---

## Summary Checklist

Use this to track your progress:

```
□ Phase 1: Basic File Creation
  □ Test 1.1: Single file
  □ Test 1.2: Multiple files
  □ Test 1.3: Subdirectory

□ Phase 2: Workspace Consistency
  □ Test 2.1: Workspace root
  □ Test 2.2: File tracking
  □ Test 2.3: Files tab

□ Phase 3: Windows Path Handling
  □ Test 3.1: Raw strings
  □ Test 3.2: Path operations
  □ Test 3.3: Imports

□ Phase 4: Venv Usage
  □ Test 4.1: Flask app
  □ Test 4.2: Script execution
  □ Test 4.3: Multiple packages

□ Phase 5: Code Planner Integration
  □ Test 5.1: Simple task
  □ Test 5.2: Complex task
  □ Test 5.3: Plan approval

□ Phase 6: Human Feedback Loop
  □ Test 6.1: Prompt appears
  □ Test 6.2: Accept testing
  □ Test 6.3: Skip testing
```

## Reporting Results

After testing, report like this:

**Example 1 - All Pass:**
```
Testing Results:
✓ Phase 1: All tests passed
✓ Phase 2: All tests passed
✓ Phase 3: All tests passed
✓ Phase 4: All tests passed
✓ Phase 5: All tests passed
✗ Phase 6 Test 6.1: Failed - no prompt after coding
```

**Example 2 - Early Failure:**
```
Testing Results:
✓ Phase 1: All tests passed
✗ Phase 2 Test 2.3: Failed - Files tab is empty
⏸ Stopped testing, awaiting fix
```

This allows targeted debugging of specific failing features!
