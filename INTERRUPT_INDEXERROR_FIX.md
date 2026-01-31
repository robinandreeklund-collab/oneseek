# IndexError Fix for Interrupt Event Handling

## Problem

After enabling `interrupt_before=["human_feedback"]` configuration, the application crashed with:

```python
IndexError: tuple index out of range
File "backend/deer_flow/server/app.py", line 488, in _create_interrupt_event
    interrupt = event_data["__interrupt__"][0]
                ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^
```

## Root Cause

When `interrupt_before` is configured in LangGraph, it creates an interrupt checkpoint **before** the node executes. At this checkpoint:
- `event_data["__interrupt__"]` key exists
- But the tuple is **empty** because `interrupt()` hasn't been called yet
- The graph is just pausing before node execution

The code assumed `__interrupt__` tuple always has content when the key exists, leading to IndexError when accessing `[0]`.

## Solution (Commit 88aa86f)

### Change 1: Added validation in `_stream_graph_events`

**Before:**
```python
if "__interrupt__" in event_data:
    yield _create_interrupt_event(thread_id, event_data)
```

**After:**
```python
if "__interrupt__" in event_data:
    # Check if __interrupt__ tuple is non-empty before processing
    if isinstance(event_data['__interrupt__'], (list, tuple)) and len(event_data['__interrupt__']) > 0:
        logger.debug(f"[{safe_thread_id}] Processing interrupt event...")
        yield _create_interrupt_event(thread_id, event_data)
    else:
        logger.debug(f"[{safe_thread_id}] Interrupt checkpoint detected but no interrupt data yet, skipping event")
```

### Change 2: Added defensive check in `_create_interrupt_event`

**Before:**
```python
def _create_interrupt_event(thread_id, event_data):
    """Create interrupt event."""
    interrupt = event_data["__interrupt__"][0]
    ...
```

**After:**
```python
def _create_interrupt_event(thread_id, event_data):
    """Create interrupt event."""
    # Defensive check: ensure __interrupt__ tuple is not empty
    if not isinstance(event_data.get("__interrupt__"), (list, tuple)) or len(event_data["__interrupt__"]) == 0:
        raise ValueError("Cannot create interrupt event: __interrupt__ tuple is empty")
    
    interrupt = event_data["__interrupt__"][0]
    ...
```

## How It Works Now

### Event Sequence

1. **Coder completes** → Sets `coder_just_completed=True`
2. **Routes to human_feedback_node**
3. **Graph pauses at interrupt_before checkpoint**
   - `__interrupt__` exists but is empty
   - No event sent to frontend (✓ no crash!)
4. **human_feedback_node starts executing**
   - Checks `coder_just_completed` flag
   - Calls `interrupt(prompt)` with message
5. **Graph creates new interrupt checkpoint**
   - `__interrupt__` now has data
   - Event sent to frontend with prompt
6. **Frontend displays prompt**
   - User sees: "Kodningen är klar! Vill du att jag testar koden?"
   - User responds [TEST] or [SKIP]

## Testing

### Backend Restart Required

```bash
cd backend
pkill -9 -f "uvicorn"
python -m uvicorn deer_flow.server.app:app --reload
```

### Verification Steps

1. Run a coding task in the application
2. Wait for coder to complete
3. Verify:
   - ✅ No IndexError in logs
   - ✅ Prompt appears in frontend
   - ✅ Can respond to prompt
   - ✅ Testing triggered/skipped based on response

### Expected Logs

```
[human_feedback_node] ENTERED - coder_just_completed=True
[human_feedback_node] Calling interrupt() with prompt...
[thread_id] Interrupt checkpoint detected but no interrupt data yet, skipping event
[thread_id] Processing interrupt event: id=..., value_len=...
```

## Related Commits

1. **Commit 0805504**: Added `coder_just_completed` to State class
   - Ensures flag persists between nodes
   
2. **Commit 9137077**: Enabled interrupt support with `interrupt_before=["human_feedback"]`
   - Allows graph to pause before human_feedback_node
   
3. **Commit 88aa86f**: Fixed IndexError when `__interrupt__` is empty *(this fix)*
   - Handles empty interrupt checkpoint gracefully

All three commits are required for the complete human feedback loop to work correctly.

## Technical Details

### Why Empty Interrupt Tuple?

LangGraph's `interrupt_before` creates a checkpoint that allows the graph to pause before executing a node. This checkpoint exists even before `interrupt()` is called, so:

- `interrupt_before` checkpoint → Empty `__interrupt__` tuple (pause point only)
- `interrupt()` call → Populated `__interrupt__` tuple (actual prompt data)

The fix distinguishes between these two cases and only sends events when there's actual data.

### Safety Measures

1. **Primary check** in `_stream_graph_events`: Prevents creating event with empty data
2. **Secondary check** in `_create_interrupt_event`: Catches any edge cases with clear error message
3. **Debug logging**: Helps diagnose interrupt flow in logs

## Conclusion

The IndexError is now fixed. The interrupt mechanism will work correctly:
- No crash when graph pauses at checkpoint
- Interrupt events only sent when there's actual prompt data
- User can interact with human feedback prompts as designed
