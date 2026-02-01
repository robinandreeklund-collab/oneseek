CODER MANUAL TEST GUIDE
========================

Purpose: quick manual checks for the Coder code-chain features.

Prereqs
-------
1) Backend running (API on http://localhost:8000/api by default).
2) Frontend running (http://localhost:3000).
3) Optional: set venv path for Python runs:
   - WORKSPACE_VENV_PYTHON=C:\Users\robin\oneseek_react_sandboxes\workspace_venv\Scripts\python.exe
   - or WORKSPACE_VENV_PATH=C:\Users\robin\oneseek_react_sandboxes

Tests
-----
1) Code planner chain (no research steps)
   - Prompt: "Build a simple CSV parser in Python and add basic tests."
   - Expected:
     - Plan shows step types: processing / analysis / review / refactor only.
     - No research step appears.
     - After accept, code_team runs (coder + code_architect/reviewer/refiner as needed).

2) Plan duplication
   - Accept a code plan.
   - Expected:
     - Plan card appears once.
     - No second plan is generated after code_team completes.

3) Code architect
   - Use a task with an architecture review step.
   - Expected:
     - Messages from agent "code_architect" appear in Coder session.
     - It does not edit files, only analysis.

4) Code tester
   - After code finishes, answer "[TEST]" to the testing prompt.
   - Expected:
     - code_tester runs and uses test tools only.
     - Results appear in chat as test output.

5) Files tab: diff + run
   - Open Files tab in Coder sidebar.
   - Select a file, switch to Diff view.
   - Click the Run icon on a .py file.
   - Expected:
     - Diff loads for the latest change.
     - Run output dialog shows stdout or errors.

6) Undo/Redo
   - Use Undo/Redo buttons in Files tab.
   - Expected:
     - File list updates after each action.
     - Counts decrement as actions are applied.

Notes
-----
- If "Failed to fetch" appears, verify NEXT_PUBLIC_API_URL or ensure backend is reachable.
- For Windows paths, always use raw string or forward slashes in Python code.
