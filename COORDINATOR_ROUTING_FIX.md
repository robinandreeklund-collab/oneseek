# Coordinator Code Routing Fix - Summary

## Problem

When users asked code-related questions, the coordinator was routing ALL code questions directly to `handoff_to_coder`, even complex multi-step projects that should go through the code planner for structured development.

### Observed Behavior (From Logs)
```
2026-01-28 13:45:50,356 - backend.deer_flow.graph.nodes - INFO - Handing off to coder for code-related task
2026-01-28 13:45:50,356 - backend.deer_flow.graph.nodes - INFO - Code task is clear, routing directly to coder
```

This happened regardless of whether the code task was:
- Simple: "Write a hello world function"
- Complex: "Create a Flask REST API with authentication and tests"

## Root Cause

The coordinator prompts (`coordinator.md` and `coordinator.sv_SE.md`) did not mention the code routing tools at all:

**Tools mentioned in prompt:**
- ✅ `handoff_to_planner` - for research questions
- ✅ `direct_response` - for greetings/small talk  
- ✅ `handoff_after_clarification` - after clarification
- ❌ `handoff_to_coder` - **MISSING**
- ❌ `handoff_to_code_planner` - **MISSING**

Without instructions about these tools, the LLM (coordinator) couldn't make informed decisions about code routing.

## Solution

Updated both coordinator prompts to add comprehensive code routing instructions:

### Added New Section: "Hand Off for Code Tasks"

**Category 3: Code Tasks** (new category added)

1. **Simple/Quick Code Tasks** → Use `handoff_to_coder()`:
   - Single function implementations
   - Quick code snippets or examples
   - Simple algorithms
   - Code explanations or debugging help
   - Quick script modifications
   - Examples: "Write a hello world function", "Sort a list in Python"

2. **Complex Code Tasks** → Use `handoff_to_code_planner()`:
   - Multi-step development projects
   - Full applications (REST APIs, web apps, etc.)
   - Projects requiring documentation research
   - Code that needs comprehensive testing
   - Multi-file or multi-component projects
   - Tasks requiring structured planning
   - Examples: "Create a Flask REST API with authentication", "Build a React app"

### Added Complexity Criteria

Clear guidelines for the LLM to assess complexity:

- Multiple files or components → `code_planner`
- Needs external documentation/research → `code_planner`
- Requires testing strategy → `code_planner`
- Multi-phase implementation → `code_planner`
- Single function/snippet → `coder`
- Quick fix or explanation → `coder`

### Updated Execution Rules

Added specific instructions in the execution rules section:
```markdown
- If the input is a code-related question (category 3):
  - **For simple, quick code tasks**: Call `handoff_to_coder()` tool
    - Single functions, snippets, explanations, quick fixes
    - Set clarity='clear' if task is straightforward
    - Set clarity='unclear' if task needs human clarification
  - **For complex, multi-step code projects**: Call `handoff_to_code_planner()` tool
    - Full applications, APIs, multi-component projects
    - Tasks requiring documentation research
    - Projects needing comprehensive testing
    - Multi-phase implementations
```

### Updated Tool Calling Requirements

Added to the critical requirements section:
```markdown
**CRITICAL**: You MUST call one of the available tools. This is mandatory:
- For greetings or small talk: use `direct_response()` tool
- For polite rejections: use `direct_response()` tool
- For simple code tasks: use `handoff_to_coder()` tool  ← NEW
- For complex code projects: use `handoff_to_code_planner()` tool  ← NEW
- For research questions: use `handoff_to_planner()` or `handoff_after_clarification()` tool
```

## Expected Behavior After Fix

### Simple Code Questions
**Input**: "Skriv en funktion som sorterar en lista" (Swedish)
**Expected Logs**:
```
INFO - Handing off to coder for code-related task
INFO - Code task is clear, routing directly to coder
INFO - Coder node is coding.
```

### Complex Code Questions
**Input**: "Skapa ett Flask REST API med autentisering och tester" (Swedish)
**Expected Logs**:
```
INFO - Handing off to code_planner for structured code development
INFO - Code planner mode activated, routing to code_planner
INFO - Code planner generating code development plan
```

## Files Changed

1. **backend/deer_flow/prompts/coordinator.md**
   - Added category 3: "Hand Off for Code Tasks"
   - Added complexity criteria
   - Updated execution rules for code handling
   - Updated tool calling requirements

2. **backend/deer_flow/prompts/coordinator.sv_SE.md**
   - Same changes as English version, translated to Swedish
   - Maintains consistency between languages

## Testing

See `COORDINATOR_CODE_ROUTING_TESTS.md` for comprehensive test cases.

### Quick Test
1. Start OneSeek server
2. Ask: "Skapa ett Flask REST API med autentisering" (complex)
3. Check logs - should see `handoff_to_code_planner`
4. Ask: "Skriv en hello world funktion" (simple)
5. Check logs - should see `handoff_to_coder`

## Impact

### Before
- ALL code questions → direct coder execution
- No planning for complex projects
- No structured testing phase
- No research/documentation gathering

### After
- Simple code questions → direct coder execution (fast)
- Complex code projects → code planner → structured development
- Proper planning, testing, and validation for complex tasks
- Research phase when documentation needed

## Architecture Alignment

This fix aligns with the Code Planner architecture implemented in previous commits:

```
Simple Code:  User → Coordinator → Coder → Response
Complex Code: User → Coordinator → Code Planner → Human Feedback → Research Team → Coder/Tester → Reporter
```

The coordinator now has the knowledge to make this routing decision intelligently.

## Related Documentation

- [CODE_PLANNER_ARCHITECTURE.md](./CODE_PLANNER_ARCHITECTURE.md) - Overall architecture
- [CODE_PLANNER_CONFIGURATION.md](./CODE_PLANNER_CONFIGURATION.md) - Configuration guide
- [COORDINATOR_CODE_ROUTING_TESTS.md](./COORDINATOR_CODE_ROUTING_TESTS.md) - Test cases
- [IMPLEMENTATION_COMPLETE.md](./IMPLEMENTATION_COMPLETE.md) - Implementation summary

## Commit

**Commit**: Update coordinator prompts to include code routing instructions
**Branch**: copilot/implement-code-planner
**Files**: 2 changed (coordinator.md, coordinator.sv_SE.md)
**Lines**: +80, -4

---

**Date**: 2026-01-28
**Issue**: Coordinator routing code questions directly to coder instead of code planner
**Status**: ✅ FIXED
