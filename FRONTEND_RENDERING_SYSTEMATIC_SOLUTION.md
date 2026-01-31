# Frontend Rendering: Systematic Solution

## Problem Statement

"Vi måste komma till botten med detta. vi kan inte hålla på såhär varje gång vi ska lägga till en ny funktion i frontend"

Every time we add a new agent, we face the same issue:
- ✅ Backend works perfectly
- ✅ Tools execute successfully  
- ✅ F12 shows messages streaming
- ❌ Frontend shows nothing

## Root Cause Analysis

### The Complete Rendering Pipeline

```
Backend → LangGraph → Streaming → Frontend Store → Message List → Render
```

Each step has specific requirements that MUST be met:

### 1. Backend Message Creation ✅
**Location**: `backend/deer_flow/graph/nodes.py`

Messages must have:
- ✅ `content` field (string, not empty)
- ✅ `agent` field (string, agent name)
- ✅ Proper message type (AIMessage, ToolMessage, etc.)

**Common Issue**: Agent returns AIMessage with empty content after tool calls.

**Solution**: Message enhancement - add tool results summary to content.

### 2. Message Streaming ✅
**Location**: `backend/deer_flow/server/app.py`

Messages must be:
- ✅ Serialized correctly
- ✅ Sent via SSE (Server-Sent Events)
- ✅ Include agent metadata

**Common Issue**: Message structure doesn't match expected format.

**Solution**: Follow existing patterns for message serialization.

### 3. Frontend Store Processing ✅
**Location**: `web/src/core/store/store.ts`

Messages must be:
- ✅ Recognized agent type
- ✅ Added to correct category (research/main chat)

**Code** (lines 286-295):
```typescript
if (
  message.agent === "coder" ||
  message.agent === "reporter" ||
  message.agent === "researcher" ||
  message.agent === "analyst" ||
  message.agent === "ai_comparison"
) {
  if (!getOngoingResearchId()) {
    const id = message.id;
    appendResearch(id);
    openResearch(id);
  }
}
```

**Common Issue**: New agent not in the list.

**Solution**: Add agent to appropriate category.

### 4. Message List Rendering ❌ **CRITICAL FAILURE POINT**
**Location**: `web/src/app/chat/components/message-list-view.tsx`

**Step 4a: Whitelist Check** (lines 146-153)
```tsx
if (
  message.role === "user" ||
  message.agent === "coordinator" ||
  isPlannerAgent(message.agent) ||
  message.agent === "podcast" ||
  message.agent === "coder" ||  // ← Must add new agents here!
  startOfResearch
) {
  // Proceed to render
}
return null; // ← Silently filtered out if not in list!
```

**Step 4b: Content Check** (lines 183-204)
```tsx
content = message.content ? (
  <MessageBubble>
    <Markdown>{message.content}</Markdown>
  </MessageBubble>
) : null;  // ← Returns null if no content!
```

**Common Issues**:
1. New agent not in whitelist → Message filtered out
2. Message has no content → Returns null

### 5. ResearchCard Rendering ❌ **SECOND FAILURE POINT**
**Location**: `web/src/app/chat/components/research-activities-block.tsx`

**Activity Message Rendering** (line 104):
```tsx
if (message.agent !== "reporter" && message.content) {
  return (
    <Markdown animated checkLinkCredibility>
      {message.content}
    </Markdown>
  );
}
return null;  // ← Returns null if no content!
```

**Common Issue**: Message has no content → Returns null.

## The Systematic Solution

### Checklist for Adding New Agents

When adding a new agent that should display in frontend:

#### Backend Tasks

- [ ] **Create agent node** in `nodes.py`
- [ ] **Ensure message has content**:
  - If agent uses tools, implement message enhancement
  - Add tool results summary to final AIMessage.content
  - Verify content is not empty string
- [ ] **Add comprehensive logging**:
  ```python
  logger.info(f"[{agent_name}] Final message content length: {len(content)}")
  logger.info(f"[{agent_name}] Content preview: {content[:200]}...")
  ```
- [ ] **Test backend execution**:
  - Check logs show content exists
  - Verify content has meaningful information

#### Frontend Tasks

- [ ] **Add agent to AgentName type** in `web/src/core/messages/types.ts`:
  ```typescript
  export type AgentName = 
    | "coordinator"
    | "researcher"
    | "coder"      // ← Add here
    | "your_new_agent"  // ← And here
    | ...;
  ```

- [ ] **Add agent to store processing** in `web/src/core/store/store.ts`:
  - If research agent, add to research category (lines 286-295)
  - If main chat agent, no action needed

- [ ] **Add agent to message-list-view whitelist** in `message-list-view.tsx`:
  ```tsx
  if (
    message.role === "user" ||
    message.agent === "coordinator" ||
    message.agent === "your_new_agent" ||  // ← Add here!
    ...
  ) {
  ```

- [ ] **Verify content rendering**:
  - Main chat: Check MessageBubble renders with content
  - Research: Check ActivityMessage renders with content

#### Testing Tasks

- [ ] **End-to-end test**:
  1. Send request to new agent
  2. Check backend logs for content
  3. Check F12 Network tab for message with content
  4. Check frontend displays message
  5. Verify content is readable and formatted

- [ ] **Edge case testing**:
  - Empty responses
  - Tool-only responses
  - Long content
  - Multiple messages

## Lessons from Previous PRs

### PR #15: Planner Integration
**Issue**: Planner messages not rendering  
**Solution**: 
- Added to AgentName type
- Added to message-list-view whitelist
- Created dedicated PlanCard component

### PR #19: Debate Planner Integration
**Issue**: debate_planner not rendering  
**Solution**:
- Added isPlannerAgent() helper
- Extended AgentName to include *_planner variants
- Mapped backend agent names to frontend types

### PR #22: Podcast Integration
**Issue**: Podcast not rendering  
**Solution**:
- Added "podcast" to AgentName type
- Added to message-list-view whitelist
- Created dedicated PodcastCard component

### Current Issue: Coder Integration
**Issue**: Coder not rendering despite backend working  
**Root Cause**: Message has no/insufficient content
**Solution**:
1. ✅ Added to AgentName type (already done)
2. ✅ Added to store processing (already done)
3. ✅ Added to message-list-view whitelist (already done)
4. ⚠️ **Need to verify**: Message content enhancement working

## Debug Strategy

When new agent doesn't render, check in order:

### 1. Backend Logs
Look for:
```
[agent_name] Final message content length: X
[agent_name] Content preview: ...
[agent_name] Sending N messages to frontend, last message content length: X
```

**If content length is 0**: Backend issue - fix message enhancement  
**If content length > 0**: Proceed to step 2

### 2. F12 Network Tab
Filter for SSE/EventSource connections, look for:
```json
{
  "type": "message_chunk",
  "agent": "your_agent",
  "content": "..."
}
```

**If no events**: Streaming issue - check serialization  
**If events but no content**: Backend sends empty - go back to step 1  
**If events with content**: Proceed to step 3

### 3. Frontend Store
Open React DevTools, check store state:
```javascript
messages: [
  {
    id: "...",
    agent: "your_agent",
    content: "..."  // ← Should exist and not be empty
  }
]
```

**If message not in store**: Store processing issue - check agent handling  
**If message in store without content**: Backend issue - go back to step 1  
**If message in store with content**: Proceed to step 4

### 4. Rendering Components
Check React DevTools component tree:
- Is message in messageIds list?
- Is MessageListItem being rendered?
- Is content variable set?
- Is component returning null?

**If returning null**: Check whitelist and content conditions  
**If component rendered but invisible**: Check CSS/styling

## Future Prevention

### Create Integration Template

**File**: `docs/NEW_AGENT_INTEGRATION.md`

Template checklist for any new agent:
1. Backend implementation with content verification
2. Frontend type definitions
3. Store processing rules
4. Rendering component updates
5. Testing checklist

### Automated Checks

Consider adding:
1. **Backend test**: Verify agent messages have content
2. **Frontend test**: Verify agent in whitelist
3. **E2E test**: Verify message renders

### Documentation

Update this document whenever:
- New rendering path added
- New agent type created
- Rendering logic changes

## Current Status: Coder Agent

### Completed
✅ Backend routing (coordinator → coder)  
✅ Tool execution  
✅ Message enhancement logic  
✅ AgentName type updated  
✅ Store processing updated  
✅ message-list-view whitelist updated  
✅ Comprehensive logging added  

### Testing Required
⚠️ Verify message content reaches frontend  
⚠️ Verify ResearchCard displays coder activities  
⚠️ Verify tool results are readable  

### Action Items
1. User tests with latest code
2. Check all 7 log points show content
3. Check F12 shows content in messages
4. Verify frontend displays content
5. If any step fails, we know exactly where to fix

## Conclusion

The recurring issue stems from **content requirements** at multiple rendering layers. The systematic solution is:

1. **Always ensure messages have content** (backend)
2. **Always add agents to whitelists** (frontend)
3. **Always verify content at each step** (testing)
4. **Use comprehensive logging** (debugging)

By following this checklist for every new agent, we prevent the recurring rendering issues.
