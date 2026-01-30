# Iteration Tracking and Tool Display Fix

## Overview

This document describes the fixes implemented to address issues with agent iteration/round progression and real-time tool action display in the OneSeek.ai application.

## Issues Addressed

### Issue 1: Round/Iteration Not Progressing

**Problem**: The agent's iteration counter was resetting to 1 on every chat turn instead of progressing through rounds (1, 2, 3, etc.) within a single execution.

**Root Cause**: The `iteration` variable in `agent_graph.py` was declared as a local variable within the `run_with_streaming()` and `run_with_streaming_realtime()` methods. Each time these methods were called, the iteration counter reset to 0.

**Solution**: 
- Added a `current_iteration` field to the `AgentState` TypedDict to persist the iteration count within the agent's state
- Modified all state initializations to include `current_iteration: 0`
- Updated the iteration loop to use state-based tracking: `current_state["current_iteration"]`
- Enhanced logging to display "Round X" for better clarity

**Files Modified**:
- `backend/agent_graph.py`:
  - Line 31: Added `current_iteration: Optional[int]` to `AgentState`
  - Line 329: Initialize `current_iteration: 0` in `run()` method
  - Line 401: Initialize `current_iteration: 0` in `run_with_streaming()` method
  - Lines 407-410: Use state-based iteration tracking
  - Line 578: Initialize `current_iteration: 0` in `run_with_streaming_realtime()` method
  - Lines 583-586: Use state-based iteration tracking

**Benefits**:
- Rounds now progress correctly within a single agent execution (Round 1 → Round 2 → Round 3, etc.)
- Tool actions correctly display which round they belong to via the `iteration` field
- Clearer logging with "Round X (state-based iteration tracking)" messages

### Issue 2: Tool Actions Not Displaying in Real-Time

**Problem**: Tool actions (like web search, browse_page) were not appearing in the sidebar/ActionBlock in real-time during agent execution.

**Root Cause**: The ActionBlock component used `useState(live)` to initialize its open state, but did not respond to changes in the `live` prop. When tool actions started streaming and `live` changed to `true`, the component remained closed.

**Solution**:
- Added a `useEffect` hook in ActionBlock that monitors the `live` prop and updates the internal `open` state when `live` becomes `true`
- Added comprehensive logging at multiple levels to track tool action lifecycle:
  - Backend: Log when tool actions START and COMPLETE with round number and duration
  - Frontend: Log when ActionBlock receives action updates with status and iteration info

**Files Modified**:
- `frontend/src/components/action-block.tsx`:
  - Lines 14-19: Added `useEffect` to update `open` when `live` changes to `true`
  - Lines 21-35: Added conditional console logging (development only) to track action updates

- `backend/agent_graph.py`:
  - Lines 369-386: Updated callback to prevent duplicate tool actions
  - Line 469: Added log message when tool action STARTED
  - Line 507: Added log message when tool action COMPLETED (run_with_streaming)
  - Lines 549-566: Updated callback to prevent duplicate tool actions (realtime)
  - Line 647: Added log message when tool action STARTED (run_with_streaming_realtime)
  - Line 685: Added log message when tool action COMPLETED (run_with_streaming_realtime)

**Benefits**:
- ActionBlock automatically expands when tool actions start streaming
- Once opened by live mode, ActionBlock stays open for user convenience (intentional behavior)
- Real-time visibility of tool execution status (running/completed)
- Comprehensive logging (development only) enables easier debugging of tool action flow
- Duplicate tool actions are prevented via tool_call_id tracking
- Better user experience with immediate feedback on agent actions

## Technical Details

### State-Based Iteration Tracking

The `AgentState` now includes a `current_iteration` field that persists across node executions within the same workflow run:

```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    retrieved_docs: List[Dict[str, Any]]
    steps: List[str]
    tool_actions: List[Dict[str, Any]]
    system_prompt: Optional[str]
    enable_thinking: Optional[bool]
    current_iteration: Optional[int]  # NEW: Track current round/iteration
```

The iteration loop now uses state-based tracking:

```python
# Initialize state with current_iteration
current_state: AgentState = {
    # ... other fields ...
    "current_iteration": 0
}

# Use state-based iteration
while current_state.get("current_iteration", 0) < max_iterations:
    current_state["current_iteration"] = current_state.get("current_iteration", 0) + 1
    iteration = current_state["current_iteration"]
    logger.info(f"Round {iteration} (state-based iteration tracking)")
```

### Tool Action Lifecycle Logging

Tool actions now have enhanced logging throughout their lifecycle:

1. **START**: When a tool is invoked
   ```
   Tool action STARTED - Round 1: web_search (id: tavily_search_12345)
   ```

2. **COMPLETE**: When a tool finishes execution
   ```
   Tool action COMPLETED - Round 1: web_search (duration: 1.23s)
   ```

3. **FRONTEND**: When ActionBlock receives updates
   ```javascript
   [ActionBlock] Actions updated: {
     count: 1,
     live: true,
     isOpen: true,
     actions: [{ tool: 'web_search', status: 'running', iteration: 1 }]
   }
   ```

### Data Flow

```
Backend (agent_graph.py)
  ↓ Tool action created with status="running", iteration=X
  ↓ callback("tool_action", tool_action)
  ↓
Backend (app.py)
  ↓ update_queue.put(("tool_action", content))
  ↓ Streamed via SSE: 2:[{"tool_actions": [...], "live_update": true}]
  ↓
Frontend (chat-page.tsx)
  ↓ useChat hook receives data
  ↓ setMessageToolActions updates state
  ↓
Frontend (chat-list.tsx)
  ↓ Passes messageToolActions[message.id] to ActionBlock
  ↓
Frontend (action-block.tsx)
  ↓ useEffect detects live=true, sets open=true
  ↓ Component re-renders with actions visible
  ✓ User sees tool actions in real-time
```

### Duplicate Tool Action Prevention

The callback function now checks if a tool action with the same `tool_call_id` already exists before adding it to the list:

```python
def callback(event_type: str, content: Any):
    # ... other event types ...
    elif event_type == "tool_action":
        # Check if this tool action already exists (by tool_call_id) to avoid duplicates
        tool_call_id = content.get("tool_call_id")
        existing_index = next((i for i, action in enumerate(tool_actions_list) 
                              if action.get("tool_call_id") == tool_call_id), None)
        if existing_index is not None:
            # Update existing tool action in place
            tool_actions_list[existing_index] = content
        else:
            # Add new tool action
            tool_actions_list.append(content)
```

This prevents the same tool action from being added twice when it transitions from "running" to "completed" status.

## Testing

To verify these fixes:

1. **Round Progression**:
   - Start a chat that requires multiple tool calls
   - Check backend logs for "Round 1", "Round 2", etc.
   - Verify tool actions have different iteration numbers

2. **Real-Time Display**:
   - Start a new chat with a search query
   - ActionBlock should automatically expand when tools start
   - Watch browser console for "[ActionBlock] Actions updated" logs
   - Verify tools show "running" status, then "completed"

3. **Backend Logs**:
   ```bash
   # In backend directory
   tail -f logs/app.log | grep "Tool action"
   ```
   
   Expected output:
   ```
   Tool action STARTED - Round 1: web_search (id: ...)
   Tool action COMPLETED - Round 1: web_search (duration: 1.23s)
   Tool action STARTED - Round 2: browse_page (id: ...)
   Tool action COMPLETED - Round 2: browse_page (duration: 0.89s)
   ```

4. **Frontend Console**:
   Open browser DevTools → Console, look for:
   ```
   [ActionBlock] Actions updated: { count: 1, live: true, ... }
   Updated tool actions for message abc123: 1 actions (live)
   Tool action STARTED - Round 1: web_search ...
   ```

## Related Files

### Backend
- `backend/agent_graph.py` - Agent workflow with iteration tracking
- `backend/app.py` - Streaming endpoint that forwards tool actions

### Frontend
- `frontend/src/components/action-block.tsx` - Tool action display component
- `frontend/src/components/chat/chat-page.tsx` - Tool action state management
- `frontend/src/components/chat/chat-list.tsx` - Passes tool actions to ActionBlock
- `frontend/src/types/tool-action.ts` - ToolAction type definition

## Future Improvements

1. **Persistent Iteration Across Chat Turns**: Currently, iteration resets when a new user message is sent. To maintain iteration across the entire chat session, store `current_iteration` in chat history or session state.

2. **Visual Round Indicators**: Display the current round number in the UI to help users understand agent progress.

3. **Tool Action Grouping**: Group tool actions by round/iteration in the sidebar for better organization.

4. **Performance Metrics**: Track and display average tool execution time per round.

## Changelog

### 2026-01-30
- ✅ Added `current_iteration` to `AgentState` for persistent iteration tracking
- ✅ Fixed ActionBlock to respond to `live` prop changes
- ✅ Added comprehensive logging for tool action lifecycle
- ✅ Enhanced log messages with round numbers and durations
- 📝 Created this documentation file

## Conclusion

These fixes ensure that:
1. Agent rounds progress correctly within a single execution
2. Tool actions are visible in real-time as they execute
3. Comprehensive logging enables easier debugging and monitoring
4. Users have better visibility into agent actions and progress

The implementation follows best practices for React state management and LangGraph state persistence, providing a solid foundation for future enhancements.
