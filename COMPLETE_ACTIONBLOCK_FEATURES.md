# Complete ActionBlock Implementation - Feature Documentation

## New Features Implemented

### 1. Complete Data Tracking

Every tool invocation now captures:

```json
{
  "tool_call_id": "call_abc123",
  "tool_name": "smhi_weather_forecast",
  "display_name": "smhi_api",
  "icon": "🌤️",
  "color": "purple",
  "iteration": 1,
  "status": "completed",
  "duration": 0.56,
  "reasoning": "User asked for weather in Tibro. I need to call the SMHI API to get real-time forecast data.",
  "input": {
    "location": "Tibro"
  },
  "raw_request": {
    "tool": "smhi_weather_forecast",
    "arguments": {"location": "Tibro"},
    "call_id": "call_abc123"
  },
  "output": {...},
  "raw_response": {
    "content": "...",
    "tool_call_id": "call_abc123",
    "parsed": {...}
  }
}
```

### 2. Real-Time Streaming

**Before:** All tools appeared at once at the end
**After:** Tools stream in real-time as they execute

```
User: Hur är vädret i Tibro?

[Immediately shown]
┌────────────────────────────────────┐
│ ∨ Actions  1 tool(s) invoked      │
├────────────────────────────────────┤
│  🌤️  smhi_api #1  ⟳ Running...    │
│      Click for complete details    │
│      Input: location="Tibro"       │
└────────────────────────────────────┘

[Updates to completed]
┌────────────────────────────────────┐
│ ∨ Actions  1 tool(s) used         │
├────────────────────────────────────┤
│  🌤️  smhi_api #1         0.56s    │
│      Click for complete details    │
│      Input: location="Tibro"       │
│      Output: 1 result              │
└────────────────────────────────────┘
```

### 3. Clickable Tool Details

Click any tool card to open detailed sidebar:

```
┌─────────────────────────────────────┐
│ 🌤️  smhi_api              × Close  │
│     Complete tool invocation details│
├─────────────────────────────────────┤
│                                     │
│ ┌─ Status & Timing ────────────┐  │
│ │ ✓ Status: completed           │  │
│ │ ⏱ Duration: 0.560s            │  │
│ │   Iteration: 1                │  │
│ │   Call ID: call_abc123        │  │
│ └───────────────────────────────┘  │
│                                     │
│ ┌─ Model Reasoning ────────────┐  │
│ │ User asked for weather in      │  │
│ │ Tibro. I need to call the SMHI │  │
│ │ API to get real-time forecast  │  │
│ │ data for Swedish locations.    │  │
│ └───────────────────────────────┘  │
│                                     │
│ ┌─ Raw Request ────────────────┐  │
│ │ {                              │  │
│ │   "tool": "smhi_weather...",   │  │
│ │   "arguments": {               │  │
│ │     "location": "Tibro"        │  │
│ │   },                           │  │
│ │   "call_id": "call_abc123"     │  │
│ │ }                              │  │
│ └───────────────────────────────┘  │
│                                     │
│ ┌─ Input Parameters ───────────┐  │
│ │ {                              │  │
│ │   "location": "Tibro"          │  │
│ │ }                              │  │
│ └───────────────────────────────┘  │
│                                     │
│ ┌─ Raw Response ───────────────┐  │
│ │ {                              │  │
│ │   "content": "{\"title\":...", │  │
│ │   "tool_call_id": "call_...",  │  │
│ │   "parsed": { ... }            │  │
│ │ }                              │  │
│ └───────────────────────────────┘  │
│                                     │
│ ┌─ Parsed Output ──────────────┐  │
│ │ {                              │  │
│ │   "title": "SMHI Väderp...",   │  │
│ │   "content": "Väderprogn...",  │  │
│ │   "url": "https://...",        │  │
│ │   "error": false               │  │
│ │ }                              │  │
│ └───────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

### 4. Multiple Tool Invocations

When agent calls same tool multiple times (or different tools), each is tracked separately:

```
┌────────────────────────────────────────┐
│ ∨ Actions  3 tool(s) used             │
├────────────────────────────────────────┤
│  🔍  web_search #1          2.34s     │
│      Click for complete details        │
│                                        │
│  🌐  browse_page #1         1.87s     │
│      Click for complete details        │
│                                        │
│  🌤️  smhi_api #1            0.56s     │
│      Click for complete details        │
└────────────────────────────────────────┘
```

Each has unique `tool_call_id` and `iteration` number to distinguish them.

## Technical Architecture

### Backend Real-Time Streaming

```python
# app.py - Queue-based real-time streaming
def queue_callback(event_type, content):
    update_queue.put((event_type, content))

# Stream updates immediately
while True:
    event_type, content = update_queue.get(timeout=30)
    if event_type == "tool_action":
        tool_actions_list.append(content)
        metadata = {
            "tool_actions": tool_actions_list,
            "live_update": True
        }
        yield f"2:{json.dumps([metadata])}\n"
```

### Frontend Live Updates

```typescript
// chat-page.tsx - Real-time state updates
useEffect(() => {
  if (data && Array.isArray(data)) {
    for (const item of data) {
      if ('tool_actions' in item) {
        setMessageToolActions((prev) => ({
          ...prev,
          [lastAssistantMessage.id]: item.tool_actions,
        }));
      }
    }
  }
}, [data]);

// action-block.tsx - Live mode detection
<ActionBlock
  actions={messageToolActions[message.id]}
  live={isLoading && isLastMessage}
  onToolClick={handleToolClick}
/>
```

## Problem Solutions

### Issue: "3 tool(s) used men dom är exakt samma"
**Solution:** Added `tool_call_id` and `iteration` number to distinguish each invocation

### Issue: "Jag vill ha komplett dataflöde med allt"
**Solution:** Added complete tracking:
- ✅ Raw API request
- ✅ Raw API response  
- ✅ Model reasoning
- ✅ Timing data
- ✅ All metadata

### Issue: "Jag ser heller aldrig live mode"
**Solution:** Implemented queue-based real-time streaming:
- ✅ Tools stream as they execute
- ✅ Not all at end
- ✅ Immediate status updates

### Issue: "klicka på varje tool och få en helt komplett data i sidebaren"
**Solution:** Created `ToolActionDetailSidebar`:
- ✅ Clickable tool cards
- ✅ Opens sidebar on right
- ✅ Shows ALL data in organized sections

## Usage Examples

### Example 1: Weather Query
```
User: Hur är vädret i Stockholm?

→ Agent calls smhi_api
→ Shows live: "🌤️ smhi_api #1 ⟳ Running..."
→ Completes: "🌤️ smhi_api #1 0.45s"
→ Click tool: See model reasoning, raw SMHI API request/response
```

### Example 2: Complex Query with Multiple Tools
```
User: Sök efter artiklar om AI och sammanfatta innehållet

→ Agent calls web_search #1 (live)
→ Agent calls browse_page #1 (live)
→ Agent calls browse_page #2 (live) [second article]
→ All show with unique IDs and iteration numbers
→ Click each to see complete execution flow
```

## Files Changed

**Backend:**
- `backend/agent_graph.py` - Added complete tracking & realtime method
- `backend/app.py` - Queue-based real-time streaming

**Frontend:**
- `frontend/src/types/tool-action.ts` - Extended interface
- `frontend/src/components/action-block.tsx` - Clickable cards
- `frontend/src/components/chat/tool-action-detail-sidebar.tsx` - NEW detailed view
- `frontend/src/components/chat/chat-list.tsx` - Integrated sidebar

## Summary

All requested features implemented:
✅ Complete data flow (raw requests/responses)
✅ Model reasoning for each step
✅ Real-time live mode (not all at end)
✅ Clickable tools with detailed sidebar
✅ No mockups - all real data
✅ Unique identification of duplicate tools
