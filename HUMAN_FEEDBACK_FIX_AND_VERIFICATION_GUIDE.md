# Human Feedback Fix and Verification Guide

## Issue Summary

Human feedback prompt not appearing after coder node completes. Logs show:
```
[coder_node] Setting coder_just_completed=True
[human_feedback_node] ENTERED - coder_just_completed=False  ❌
```

The flag is being set but not persisting to the next node.

## Fix Applied (Commit 0805504)

Added `coder_just_completed` field to State class in `backend/deer_flow/graph/types.py` (line 49):

```python
class State(TypedDict):
    # ... other fields ...
    coder_just_completed: bool = False  # Added this field
```

### Why This Should Work

In LangGraph, all state fields must be explicitly declared in the State class to persist across node transitions. Undeclared fields don't survive Command updates even when included in the update dictionary.

By declaring the field, LangGraph knows to track and persist it through the state transition from coder_node to human_feedback_node.

## Complete Backend Restart Procedure

**CRITICAL:** The fix requires a complete backend restart with cache clearing.

```bash
# Step 1: Kill ALL Python backend processes
pkill -9 -f "uvicorn"
pkill -9 -f "deer_flow"
pkill -9 -f "python.*backend"

# Verify all killed
ps aux | grep python | grep backend
# If any remain, note PID and: kill -9 <PID>

# Step 2: Clear Python module cache
cd /path/to/oneseek/backend
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

# Step 3: Restart backend fresh
python -m uvicorn deer_flow.server.app:app --reload --port 8000
```

## Verification Steps

After complete restart, run a coding task and check the logs:

### Expected Log Sequence

```
2026-01-29 HH:MM:SS - backend.deer_flow.graph.nodes - INFO - Coder completed, routing to human_feedback to ask about testing
2026-01-29 HH:MM:SS - backend.deer_flow.graph.nodes - INFO - [coder_node] Setting coder_just_completed=True in update dict
2026-01-29 HH:MM:SS - backend.deer_flow.graph.nodes - INFO - [human_feedback_node] ENTERED - coder_just_completed=True  ✓
2026-01-29 HH:MM:SS - backend.deer_flow.graph.nodes - INFO - [human_feedback_node] Calling interrupt() with prompt...
```

### What to Check

1. **First log line must appear:**
   ```
   [coder_node] Setting coder_just_completed=True in update dict
   ```
   If this is missing, the coder_node code didn't execute (old version still running).

2. **Second log line must show True:**
   ```
   [human_feedback_node] ENTERED - coder_just_completed=True  ✓
   ```
   If this shows `False`, the State field isn't persisting despite being declared.

3. **Third log line must appear:**
   ```
   [human_feedback_node] Calling interrupt() with prompt...
   ```
   If this appears, the prompt should show in frontend.

## Troubleshooting

### If Still Shows False After Complete Restart

1. **Verify the State field is actually declared:**
   ```bash
   grep -n "coder_just_completed" backend/deer_flow/graph/types.py
   ```
   Should show line 49 with the field declaration.

2. **Check if backend actually restarted:**
   - Note the backend process PID before killing
   - After restart, note new PID
   - They should be different

3. **Verify no old processes:**
   ```bash
   ps aux | grep uvicorn
   ps aux | grep "python.*backend"
   ```
   Should only show ONE backend process.

### If State Field Doesn't Persist

If after complete restart with verified cache clear, the field still shows False:

**This indicates a LangGraph State persistence issue:**
- TypedDict fields with defaults may not work as expected
- May need to use `field(default=False)` with dataclass instead
- May need to explicitly initialize in graph builder
- May need alternative State management approach

**Alternative Approaches to Try:**

1. **Use messages instead of State field**
2. **Store in separate persistence mechanism**
3. **Use graph builder State initialization**
4. **Switch to dataclass with field() defaults**

## Expected Behavior After Fix

1. ✅ Coder completes and sets `coder_just_completed=True`
2. ✅ State transitions to human_feedback_node with flag intact
3. ✅ human_feedback_node detects flag and shows prompt: "Kodningen är klar! Vill du att jag testar koden?"
4. ✅ User can respond:
   - `[TEST]` or `ja` → Routes to tester_node
   - `[SKIP]` or `nej` → Routes to research_team
5. ✅ Flag is cleared after human response

## Frontend Display Issues (Separate Issue)

The user also reported frontend showing limited information:
- "Filåtgärd: unknown" instead of tool names
- Empty "Kör Python-kod" section
- Only "Utdata" shown
- Empty "Filer" tab

### What's Working

The fact that "Filåtgärd: unknown" and "Utdata" ARE showing means:
- SSE streaming is working
- Tool actions are being sent
- Frontend is receiving and displaying SOME data

### Investigation Approach

1. **Reverse-engineer the successful pattern:**
   - What makes "Utdata" successfully stream?
   - How is tool_action structured for successful display?
   - What fields are present vs missing?

2. **Apply same pattern to missing data:**
   - Tool names (currently "unknown")
   - Tool inputs (currently empty)
   - Intermediate steps (currently hidden)
   - Files tab data (currently not reaching frontend)

### Analysis Required

Need to analyze fort.yaml logs to see:
- What tool_action data is being sent
- What's in the SSE stream
- What frontend is receiving vs displaying
- Where the disconnect happens

## User Action Required

1. **Do complete backend restart** (kill + cache clear)
2. **Run coding task**
3. **Check logs** for the three expected log lines
4. **Report results:**
   - Does `[coder_node] Setting...` line appear?
   - Does `[human_feedback_node] ENTERED...` show True or False?
   - Does prompt appear in frontend?
5. **If still False**, confirm:
   - All processes killed
   - Cache cleared
   - New process PID is different
   - State field exists in types.py line 49

## Summary

- ✅ **Fix applied:** State field declared (commit 0805504)
- ⏳ **Awaiting verification:** User must do complete restart
- ❓ **If doesn't work:** May need alternative State approach
- 📋 **Frontend display:** Separate issue, requires investigation

**Status:** Waiting for user verification with complete backend restart and cache clear.
