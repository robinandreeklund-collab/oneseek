# Coder Rendering Debug Guide

## Problem Status
Backend works perfectly, F12 shows streaming, but nothing renders on frontend.

## What We Know

### ✅ Working
1. Backend routing (coordinator → coder)
2. Tool execution (files created successfully)
3. Message streaming (F12 shows events)
4. Frontend receives messages
5. Store processes coder messages
6. ResearchCard created

### ❌ Not Working
Frontend displays nothing

## Root Cause Analysis

### Frontend Rendering Requirements

Frontend has TWO places where coder messages can render:

#### 1. Main Chat (`message-list-view.tsx`)
```tsx
// Line 146-153: Coder IS in whitelist ✅
if (
  message.role === "user" ||
  message.agent === "coordinator" ||
  isPlannerAgent(message.agent) ||
  message.agent === "podcast" ||
  message.agent === "coder" ||  // ✅ ADDED
  startOfResearch
) {
  // ... render message
}

// Line 182-204: Falls into else block
else {
  content = message.content ? (
    <MessageBubble>...</MessageBubble>
  ) : null;  // ❌ Returns null if no content!
}
```

#### 2. ResearchCard Activities (`research-activities-block.tsx`)
```tsx
// Line 98-114: ActivityMessage component
if (message?.agent) {
  if (isPlannerAgent(message.agent)) {
    return <PlanCard message={message} />;
  }
  // Skip reporter, show others IF they have content
  if (message.agent !== "reporter" && message.content) {
    return <Markdown>{message.content}</Markdown>;
  }
}
return null;  // ❌ Returns null if no content!
```

### Conclusion
**Both rendering paths require message.content to be non-empty!**

## Backend Message Enhancement

The enhancement code (lines 1665-1710) SHOULD be fixing this:

```python
# For direct calls with tools, enhance the message
if agent_messages and current_plan and len(current_plan.steps) == 1 and tool_message_count > 0:
    last_msg = agent_messages[-1]
    if isinstance(last_msg, AIMessage):
        # Build tool summaries
        tool_summaries = []
        for msg in agent_messages:
            if isinstance(msg, ToolMessage):
                tool_name = getattr(msg, 'name', 'unknown_tool')
                tool_content = str(msg.content)[:200]
                tool_summaries.append(f"**{tool_name}**: {tool_content}")
        
        # Create enhanced content
        summary_content = f"{response_content}\n\n## Tool Results\n\n" + "\n\n".join(tool_summaries)
        
        # Replace with enhanced message
        enhanced_message = AIMessage(content=summary_content, name=agent_name, id=last_msg.id)
        agent_messages[-1] = enhanced_message
```

## Testing Instructions

### Step 1: Pull Latest Changes
```bash
git pull origin copilot/integrera-ny-router-kodfror
```

### Step 2: Restart Backend
Stop and restart the backend server to pick up new logging.

### Step 3: Test with Simple Request
Ask: "Create a file test.txt with content 'Hello World'"

### Step 4: Check Backend Logs

Look for these log messages in sequence:

#### A. Enhancement Check
```
[coder] Checking if message enhancement needed: agent_messages=6, current_plan=exists, steps=1
```
- ✅ Should see: steps=1 (synthetic plan)
- ❌ If steps != 1: Enhancement won't run

#### B. Message Type
```
[coder] Last message type: AIMessage, isinstance(AIMessage)=True
```
- ✅ Should be AIMessage
- ❌ If not: Wrong message type

#### C. Content Length
```
[coder] Last message content length: 0, tool_message_count: 1
```
- ✅ Should see tool_message_count > 0
- ❌ If 0: No tools executed

#### D. Enhancement Running
```
[coder] Direct call with tools detected - enhancing message for frontend visibility
```
- ✅ Should see this
- ❌ If not: Enhancement condition not met

#### E. Tool Summaries
```
[coder] Created enhanced content with 1 tool results, total length: 150
```
- ✅ Should see tool results count > 0
- ✅ Should see total length > 50
- ❌ If 0 or small: Tool summaries not created

#### F. **FINAL CONTENT** (NEW LOG)
```
[coder] FINAL ENHANCED MESSAGE CONTENT: Create a file test.txt with content 'Hello World'

## Tool Results

**file_system_tool**: ✓ Successfully wrote 11 bytes to 'test.txt'
```
- ✅ Should see actual content here
- ✅ Should include task description + tool results
- ❌ If empty: Enhancement failed

### Step 5: Check F12 Console

Open browser DevTools (F12) → Network tab → Filter by "stream"

Look for SSE events with content:
```json
{
  "message": {
    "agent": "coder",
    "content": "Create a file test.txt...\n\n## Tool Results\n\n...",
    "isStreaming": false
  }
}
```

- ✅ If content present: Backend → Frontend OK
- ❌ If content empty: Streaming issue

### Step 6: Check Frontend Console

F12 → Console tab

Look for any errors related to:
- Message parsing
- ResearchCard rendering
- Store updates

## Diagnosis

### Scenario A: Content in Backend Logs, Empty in F12
**Problem**: Streaming or serialization issue

**Fix**: Check how AIMessage.content is serialized in app.py

### Scenario B: Content in F12, Nothing Renders
**Problem**: Frontend filtering or rendering issue

**Possible Causes**:
1. Message not added to research activities
2. ResearchCard not opening
3. ActivityMessage filtering content
4. MessageBubble not rendering

**Fix**: Check browser console for frontend errors

### Scenario C: No Content in Backend Logs
**Problem**: Enhancement not running

**Possible Causes**:
1. current_plan.steps != 1
2. tool_message_count == 0
3. Last message not AIMessage
4. Tool summaries empty

**Fix**: Check each condition in logs

### Scenario D: Content Shows but is Wrong Format
**Problem**: Content structure issue

**Fix**: Verify markdown formatting is correct

## Expected Behavior

When working correctly:

1. **Backend logs show**:
   ```
   [coder] FINAL ENHANCED MESSAGE CONTENT: [task]

   ## Tool Results

   **file_system_tool**: ✓ Successfully wrote...
   ```

2. **F12 shows**:
   ```json
   {
     "message": {
       "agent": "coder",
       "content": "[same as backend]",
       "isStreaming": false
     }
   }
   ```

3. **Frontend displays**:
   - ResearchCard opens automatically
   - Coder activity shows with content
   - OR message appears in main chat
   - User sees tool execution results

## Next Steps

After testing, report back with:
1. Which logs appeared
2. Which logs were missing
3. What content (if any) appeared in F12
4. Any frontend console errors
5. Screenshot of F12 Network tab showing message

This will pinpoint exactly where the issue is!
