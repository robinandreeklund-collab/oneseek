# Tool Actions Sidebar Fix - Implementation Plan

## Problem Summary

**Issue**: Sidebar inte visas + F12 error "Tool call result without matching message"

**Root Cause**: Backend och frontend använder olika format för tool execution data:
- **Backend**: Emitterar `tool_calls` och `tool_call_result` events (separata events)
- **Frontend**: Förväntar sig `tool_actions` array i data stream (aggregerat format)
- **Result**: Ingen konvertering sker, frontend kan inte bygga tool_actions, sidebar visas inte

## Current Architecture

### Backend (app.py)

```python
# Line ~569: Tool calls emittas
yield _make_event("tool_calls", event_stream_message)

# Line ~556: Tool results emittas  
yield _make_event("tool_call_result", event_stream_message)
```

**Format**:
```python
{
  "event": "tool_calls",
  "data": {
    "tool_calls": [
      {"name": "web_search", "args": "{...}", "id": "call-123"}
    ]
  }
}

{
  "event": "tool_call_result",
  "data": {
    "tool_call_id": "call-123",
    "content": "Search results..."
  }
}
```

### Frontend (chat-page.tsx)

```typescript
// Line 139: Frontend letar efter tool_actions
if ('tool_actions' in item && Array.isArray(item.tool_actions)) {
  const toolActions = item.tool_actions as any[];
  // ... update state
}
```

**Expected Format**:
```typescript
{
  tool_actions: [
    {
      tool_name: "web_search",
      tool_input: '{"query": "..."}',
      tool_output: "Search results...",
      tool_call_id: "call-123",
      status: "complete" | "running" | "error"
    }
  ],
  live_update: true  // För streaming updates
}
```

## Solution: Add Tool Actions Tracker

### Implementation Steps

#### 1. Create ToolActionTracker Class

Add to `app.py` (around line 300):

```python
class ToolActionTracker:
    """
    Tracks tool calls and results, converts them to tool_actions format
    expected by frontend.
    """
    
    def __init__(self):
        self.tool_calls = {}  # {tool_call_id: {name, input, timestamp}}
        self.tool_actions = []  # [{tool_name, tool_input, tool_output, tool_call_id, status}]
    
    def add_tool_call(self, tool_call_id: str, tool_name: str, tool_input: str):
        """Register a new tool call."""
        self.tool_calls[tool_call_id] = {
            "name": tool_name,
            "input": tool_input,
            "timestamp": time.time()
        }
        
        # Add to tool_actions with "running" status
        self.tool_actions.append({
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_output": None,
            "tool_call_id": tool_call_id,
            "status": "running"
        })
    
    def add_tool_result(self, tool_call_id: str, tool_output: str, error: bool = False):
        """Add result for a tool call."""
        if tool_call_id not in self.tool_calls:
            logger.warning(f"Tool result for unknown call_id: {tool_call_id}")
            return
        
        # Find and update the matching tool_action
        for action in self.tool_actions:
            if action["tool_call_id"] == tool_call_id:
                action["tool_output"] = tool_output
                action["status"] = "error" if error else "complete"
                break
    
    def get_tool_actions(self):
        """Get current tool_actions array for frontend."""
        return self.tool_actions
    
    def has_pending_tools(self):
        """Check if there are tools still running."""
        return any(action["status"] == "running" for action in self.tool_actions)
```

#### 2. Integrate Tracker into _stream_graph_events

Modify `_stream_graph_events` function (line ~690):

```python
async def _stream_graph_events(
    graph_instance, workflow_input, workflow_config, thread_id
):
    """Stream events from the graph and process them."""
    safe_thread_id = sanitize_thread_id(thread_id)
    logger.debug(f"[{safe_thread_id}] Starting graph event stream with agent nodes")
    
    # Track citations collected during research
    collected_citations = []
    
    # ADD: Initialize tool action tracker
    tool_tracker = ToolActionTracker()
    
    try:
        # ... existing code ...
        
        async for agent, _, event_data in graph_instance.astream(...):
            # ... existing processing ...
            
            # ADD: Process events and yield tool_actions
            async for event in _process_message_chunk(
                message_chunk, message_metadata, thread_id, agent, tool_tracker  # Pass tracker
            ):
                yield event
                
                # After each event, check if we should emit tool_actions
                if tool_tracker.tool_actions:
                    yield _make_event("data", {
                        "tool_actions": tool_tracker.get_tool_actions(),
                        "live_update": True
                    })
        
        # After stream completes, send final tool_actions
        if tool_tracker.tool_actions:
            yield _make_event("data", {
                "tool_actions": tool_tracker.get_tool_actions(),
                "live_update": False  # Final update
            })
```

#### 3. Update _process_message_chunk to Use Tracker

Modify function signature and add tracking (line ~528):

```python
async def _process_message_chunk(
    message_chunk, message_metadata, thread_id, agent, tool_tracker: ToolActionTracker
):
    """Process a single message chunk and yield appropriate events."""
    
    # ... existing code ...
    
    if isinstance(message_chunk, ToolMessage):
        # Tool Message - Return the result of the tool call
        tool_call_id = message_chunk.tool_call_id
        tool_output = message_chunk.content
        
        # ADD: Track tool result
        tool_tracker.add_tool_result(tool_call_id, tool_output)
        
        # ... existing event emission ...
        
    elif isinstance(message_chunk, AIMessage):
        # AI Message - Non-streaming full content
        if message_chunk.tool_calls:
            # ADD: Track tool calls
            for tool_call in message_chunk.tool_calls:
                tool_tracker.add_tool_call(
                    tool_call_id=tool_call.get("id"),
                    tool_name=tool_call.get("name"),
                    tool_input=json.dumps(tool_call.get("args", {}))
                )
            
            # ... existing event emission ...
            
    elif isinstance(message_chunk, AIMessageChunk):
        if message_chunk.tool_calls:
            # ADD: Track tool calls
            for tool_call in message_chunk.tool_calls:
                tool_tracker.add_tool_call(
                    tool_call_id=tool_call.get("id"),
                    tool_name=tool_call.get("name"),
                    tool_input=json.dumps(tool_call.get("args", {}))
                )
            
            # ... existing event emission ...
```

#### 4. Update _make_event to Handle Data Events

Current `_make_event` function (line ~234) should already support "data" events,
but verify it properly handles the tool_actions format:

```python
def _make_event(event: str, data: dict):
    """Create a server-sent event."""
    if event == "data":
        # For data events, send the data object directly
        json_data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    else:
        json_data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    
    return f"event: {event}\ndata: {json_data}\n\n"
```

#### 5. Fix Tool Call ID Mismatch

The F12 error "Tool call result without matching message" suggests IDs don't match.
Ensure tool_call_id is preserved correctly:

```python
# When creating tool call:
tool_call_id = f"call-{uuid.uuid4()}"  # Or use LLM-provided ID

# When processing result:
# Make sure ToolMessage.tool_call_id matches the original call ID
```

## Testing Plan

### 1. Test Sequential Debate Flow
```bash
# Start debate with sequential external AI calls
# Monitor backend logs for tool_calls and tool_call_result
# Check that tool_actions are emitted after each tool completion
```

### 2. Verify Frontend Receives tool_actions
```javascript
// In browser F12 console:
// Should see tool_actions in data stream
{
  tool_actions: [
    {tool_name: "start_debate_round", status: "complete", ...},
    {tool_name: "query_model_in_round", status: "complete", ...},
    ...
  ],
  live_update: true
}
```

### 3. Verify Sidebar Opens
- Sidebar should open automatically when first tool executes
- Should show tool execution details in real-time
- Should update as tools complete

### 4. Check for Errors
- No "Tool call result without matching message" in F12
- All tool_call_ids should match between call and result
- Tool actions should appear for debate tools

## Expected Behavior After Fix

1. **Backend**: 
   - Tracks tool calls and results
   - Emits `tool_actions` data events
   - Format matches frontend expectations

2. **Frontend**:
   - Receives `tool_actions` array
   - Builds messageToolActions state
   - Auto-opens sidebar (via useEffect in chat-list.tsx)
   - Shows real-time tool execution

3. **Sidebar**:
   - Opens automatically when debate starts
   - Shows sequential tool calls:
     - start_debate_round
     - query_model_in_round (5 times for 5 models)
     - collect_debate_votes
     - get_debate_summary
   - Updates in real-time as tools complete

## Files to Modify

1. **backend/deer_flow/server/app.py** (main changes)
   - Add `ToolActionTracker` class (~300)
   - Update `_stream_graph_events` to use tracker (~690)
   - Update `_process_message_chunk` to track tools (~528)
   - Emit `tool_actions` data events

2. **No frontend changes needed** (already expects tool_actions format)

## Alternative: Frontend-Only Solution

If backend changes are too complex, frontend could convert events:

```typescript
// In chat-page.tsx, add converter:
const toolCallsMap = new Map(); // Track calls

// When receiving tool_calls event:
data.forEach(item => {
  if (item.event === 'tool_calls' && item.data.tool_calls) {
    item.data.tool_calls.forEach(call => {
      toolCallsMap.set(call.id, {
        tool_name: call.name,
        tool_input: JSON.stringify(call.args),
        tool_call_id: call.id,
        status: 'running'
      });
    });
  }
  
  // When receiving tool_call_result:
  if (item.event === 'tool_call_result' && item.data.tool_call_id) {
    const action = toolCallsMap.get(item.data.tool_call_id);
    if (action) {
      action.tool_output = item.data.content;
      action.status = 'complete';
    }
  }
  
  // Convert Map to array and set as tool_actions:
  setMessageToolActions(prev => ({
    ...prev,
    [currentMessageId]: Array.from(toolCallsMap.values())
  }));
});
```

**Pros**: Easier, no backend changes
**Cons**: More complex frontend logic, doesn't fix ID mismatch

## Recommendation

**Implement backend solution** - it's cleaner and fixes the root cause. The frontend
already has the right architecture, it just needs the right data format.

## Timeline

1. Implement ToolActionTracker: ~1 hour
2. Integrate into streaming: ~2 hours  
3. Testing and debugging: ~2 hours
4. Total: ~5 hours

## References

- Frontend expects: `frontend/src/components/chat/chat-page.tsx` line 139
- Backend emits: `backend/deer_flow/server/app.py` lines 556, 569
- Sidebar auto-open: `frontend/src/components/chat/chat-list.tsx` lines 120-135
- Tool action type: `frontend/src/types/tool-action.ts`
