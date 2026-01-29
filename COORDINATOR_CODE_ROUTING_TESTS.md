# Coordinator Code Routing Test Guide

This document provides test cases to verify that the coordinator properly routes code-related questions to the appropriate handler.

## Test Cases

### Simple Code Tasks (Should route to `handoff_to_coder`)

1. **Test: Simple Function**
   - **Input (Swedish)**: "Skriv en funktion som sorterar en lista"
   - **Input (English)**: "Write a function to sort a list"
   - **Expected**: `handoff_to_coder` with clarity='clear'
   - **Log Pattern**: "Handing off to coder for code-related task" → "routing directly to coder"

2. **Test: Code Snippet**
   - **Input (Swedish)**: "Visa hur man läser en fil i Python"
   - **Input (English)**: "Show how to read a file in Python"
   - **Expected**: `handoff_to_coder` with clarity='clear'
   - **Log Pattern**: "Handing off to coder for code-related task" → "routing directly to coder"

3. **Test: Code Explanation**
   - **Input (Swedish)**: "Förklara vad denna kod gör: def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)"
   - **Input (English)**: "Explain what this code does: def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)"
   - **Expected**: `handoff_to_coder` with clarity='clear'
   - **Log Pattern**: "Handing off to coder for code-related task" → "routing directly to coder"

4. **Test: Simple Algorithm**
   - **Input (Swedish)**: "Skriv en hello world funktion"
   - **Input (English)**: "Write a hello world function"
   - **Expected**: `handoff_to_coder` with clarity='clear'
   - **Log Pattern**: "Handing off to coder for code-related task" → "routing directly to coder"

### Complex Code Tasks (Should route to `handoff_to_code_planner`)

1. **Test: Full Application**
   - **Input (Swedish)**: "Skapa ett Flask REST API med användarautentisering och databas"
   - **Input (English)**: "Create a Flask REST API with user authentication and database"
   - **Expected**: `handoff_to_code_planner`
   - **Log Pattern**: "Handing off to code_planner for structured code development" → "routing to code_planner"

2. **Test: Multi-Component Project**
   - **Input (Swedish)**: "Bygg en React-app med användarhantering och backend API"
   - **Input (English)**: "Build a React app with user management and backend API"
   - **Expected**: `handoff_to_code_planner`
   - **Log Pattern**: "Handing off to code_planner for structured code development" → "routing to code_planner"

3. **Test: Project with Tests**
   - **Input (Swedish)**: "Utveckla ett Python-bibliotek med omfattande tester och dokumentation"
   - **Input (English)**: "Develop a Python library with comprehensive tests and documentation"
   - **Expected**: `handoff_to_code_planner`
   - **Log Pattern**: "Handing off to code_planner for structured code development" → "routing to code_planner"

4. **Test: Complex Multi-Step Project**
   - **Input (Swedish)**: "Skapa en e-handelsplattform med produktkatalog, kundvagn och betalningsintegration"
   - **Input (English)**: "Create an e-commerce platform with product catalog, shopping cart, and payment integration"
   - **Expected**: `handoff_to_code_planner`
   - **Log Pattern**: "Handing off to code_planner for structured code development" → "routing to code_planner"

### Edge Cases

1. **Test: Unclear Code Task**
   - **Input (Swedish)**: "Hjälp mig med kod"
   - **Input (English)**: "Help me with code"
   - **Expected**: May ask for clarification OR route to `handoff_to_coder` with clarity='unclear'

2. **Test: Medium Complexity**
   - **Input (Swedish)**: "Skapa en funktion som hämtar data från ett REST API"
   - **Input (English)**: "Create a function that fetches data from a REST API"
   - **Expected**: `handoff_to_coder` (single function, even if it involves API)

## How to Test

### Method 1: Direct Testing with Application

1. Start the OneSeek server
2. Open the UI
3. Submit each test case
4. Monitor the logs for routing decisions
5. Verify correct handler is called

### Method 2: Log Analysis

After running a test, check logs for these patterns:

**For simple tasks (coder):**
```
INFO - Handing off to coder for code-related task
INFO - Code task is clear, routing directly to coder
INFO - Coder node is coding.
```

**For complex tasks (code_planner):**
```
INFO - Handing off to code_planner for structured code development
INFO - Code planner mode activated, routing to code_planner
INFO - Code planner generating code development plan
```

## Expected Behavior After Fix

### Before (Current Issue)
All code questions route to `handoff_to_coder`, even complex ones:
```
INFO - Handing off to coder for code-related task
INFO - Code task is clear, routing directly to coder
```

### After (Expected Fix)
Simple questions route to coder:
```
INFO - Handing off to coder for code-related task
INFO - Code task is clear, routing directly to coder
```

Complex questions route to code_planner:
```
INFO - Handing off to code_planner for structured code development
INFO - Code planner mode activated, routing to code_planner
```

## Verification Checklist

- [ ] Simple code snippets → coder (direct execution)
- [ ] Single function implementations → coder (direct execution)
- [ ] Code explanations → coder (direct execution)
- [ ] Full applications → code_planner (structured planning)
- [ ] Multi-component projects → code_planner (structured planning)
- [ ] Projects with tests → code_planner (structured planning)
- [ ] Projects requiring research → code_planner (structured planning)

## Troubleshooting

If code questions still route to coder instead of code_planner:

1. **Check prompt loading**: Verify coordinator prompts are being loaded correctly
2. **Check LLM configuration**: Ensure coordinator LLM has tool calling enabled
3. **Check tool availability**: Verify `handoff_to_code_planner` is in coordinator's tools list
4. **Check logs**: Look for tool calling errors or warnings

## Notes

- The coordinator uses the LLM to decide which tool to call based on the prompt
- Complexity assessment is done by the LLM, guided by criteria in the prompt
- Swedish and English prompts should behave identically
- The fix updates only the coordinator prompts, not the graph routing logic
