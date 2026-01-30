# Debate Flow Verification Guide

This document describes how to verify that all 3 critical issues have been fixed.

## Changes Made in Phase 1

### Fix 1: User Query Passing ✅

**File:** `backend/deer_flow/graph/nodes.py` line 2793

**Before:**
```python
user_query = state.get("user_query", "")  # Always empty!
```

**After:**
```python
user_query = state.get("clarified_research_topic") or state.get("research_topic", "")
```

**What this fixes:** Models will now receive and discuss the user's actual question instead of generic AI topics.

### Fix 2: State Management ✅

**File:** `backend/deer_flow/graph/nodes.py`

**Changes:**
1. Lines 238-263: Removed ALL debate fields from `preserve_state_meta_fields()`
   - Removed: `debate_round`, `debate_scores`, `debate_knockout`, `debate_max_rounds`, `debate_error_count`, `debate_complete`
   
2. Lines 2597-2605, 2632-2640, 2654-2662, 2678-2693: Added explicit debate state to ALL debate_orchestrator returns
   - Every `Command.update` now explicitly sets all 6 debate fields
   - No reliance on auto-preservation

**What this fixes:** Rounds will progress correctly: 1 → 2 → 3 → complete (no more Round 1 restart loop)

### Fix 3: Tool Visibility ⏳

**File:** `backend/deer_flow/graph/nodes.py` lines 2756-2788

**Current Implementation:**
- Tool calls are added to AIMessage.tool_calls
- Server should detect and stream them (backend/deer_flow/server/app.py:572-588)

**Status:** Implemented but needs user testing to verify visibility in frontend

## How to Verify

### Test 1: User Query is Passed to Models

1. Start a new debate with a specific question:
   - Example: "Vad är den bästa programmeringsspråket för webbutveckling?"
   
2. Check model responses:
   - ✅ PASS: Models discuss programming languages for web development
   - ❌ FAIL: Models discuss generic AI topics, ignore the question

3. Check logs for this line:
   ```
   INFO - Querying model with user_query: "Vad är den bästa programmeringsspråket för webbutveckling?"
   ```

### Test 2: Rounds Progress Correctly

1. Start a debate (any question)

2. Watch the logs for round progression:
   ```
   INFO - Starting debate round 1/3
   INFO - Step 3: Round 1 complete - all 5 models queried
   INFO - Fact checker verifying external AI claims
   INFO - Synthesizer creating integrated position
   INFO - Moderator evaluating round
   INFO - Round 1 scores: Proponent +X, Opponent +Y
   INFO - Orchestrator: Incremented to debate_round=2  ← Should be 2, not 1!
   INFO - Starting debate round 2/3
   ...
   INFO - Starting debate round 3/3
   ...
   INFO - Max rounds reached: 3
   INFO - Routing to reporter
   ```

3. Expected flow:
   - ✅ PASS: Round 1 → Round 2 → Round 3 → Reporter → END
   - ❌ FAIL: Round 1 → Round 1 → Round 1 (infinite loop)

4. Check these log lines specifically:
   ```
   INFO - Orchestrator: Read debate_round=0 from state (before increment)
   INFO - Orchestrator: Incremented to debate_round=1
   INFO - Moderator: Read debate_round=1 from state
   INFO - Moderator: Setting debate_round=1 in state update
   INFO - Orchestrator: Read debate_round=1 from state (before increment)  ← Should be 1, not 0!
   INFO - Orchestrator: Incremented to debate_round=2  ← Should increment to 2!
   ```

### Test 3: Tool Calls Visible in Sidebar

1. Start a debate

2. Check the frontend sidebar (Activities panel)

3. Expected:
   - ✅ PASS: See tool calls appearing:
     - "start_debate_round" (rounds 1, 2, 3)
     - "query_model_in_debate" (5 times per round for each model)
     - "web_search" (fact_checker and synthesizer)
   
   - ❌ FAIL: No tool calls visible, only final text responses

4. Check logs for:
   ```
   DEBUG - AIMessage has tool_calls, yielding tool_calls event
   ```

## Expected Final Behavior

**Complete successful debate flow:**

```
1. User asks: "Vad är den bästa programmeringsspråket för webbutveckling?"

2. Round 1:
   - external_ai_caller queries 5 models about web programming languages
   - fact_checker verifies claims
   - synthesizer integrates findings
   - moderator scores the round
   
3. Round 2:
   - external_ai_caller queries 5 models (with Round 1 context)
   - fact_checker verifies new claims
   - synthesizer integrates
   - moderator scores
   
4. Round 3:
   - external_ai_caller queries 5 models (with Round 1-2 context)
   - fact_checker verifies
   - synthesizer integrates
   - moderator scores
   
5. Reporter:
   - Summarizes all 3 rounds
   - Presents final analysis with scores
   
6. END
```

## Debugging

If any test fails, check these log patterns:

### Problem: Round restart at 1
**Look for:**
```
INFO - Orchestrator: Read debate_round=0 from state (before increment)
INFO - Orchestrator: Incremented to debate_round=1
... (Round 1 executes)
INFO - Moderator: Setting debate_round=1 in state update
INFO - Orchestrator: Read debate_round=0 from state (before increment)  ← BUG: Should be 1!
```

**Root cause:** State not being preserved between moderator and orchestrator

### Problem: Models ignore user question
**Look for:**
```
INFO - Querying model with user_query: ""  ← BUG: Empty!
```

**Root cause:** research_topic not being passed correctly

### Problem: Tool calls not visible
**Look for:**
```
DEBUG - AIMessage has tool_calls, yielding tool_calls event
```

If this log appears but sidebar is still empty, the issue is frontend rendering, not backend.

## Summary

All 3 fixes have been implemented. User should test and verify each one works correctly.

If any issue persists, provide the full terminal log and indicate which specific test failed.
