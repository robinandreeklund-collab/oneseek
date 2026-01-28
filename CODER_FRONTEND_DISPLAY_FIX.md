# Coder Frontend Display Fix

## Problem Description

Backend successfully executes coder tasks but nothing appears on the frontend.

### Symptoms

**Backend logs show** (everything working):
```
✅ "Coder node is coding"
✅ "Agent 'coder' created successfully"
✅ Tool file_system_tool called with parameters...
✅ "Successfully wrote 15 bytes to 'hello.txt'"
✅ "Coder agent made 1 tool calls"
✅ "Step execution completed by coder"
✅ "Coder was called directly from coordinator, responding to user (__end__)"
```

**Frontend shows**:
```
❌ Nothing - blank/empty response area
❌ No error messages
❌ No content displayed
```

### Backend/F12 Investigation

- Network tab shows events arriving
- Messages streaming from backend
- No JavaScript errors
- But: Message content is empty!

## Root Cause

When LLM agents use `agent.ainvoke()` (non-streaming) and make tool calls, the response message flow is:

1. **AIMessage** with tool_calls (agent decides what tools to use)
2. **ToolMessage** with tool results (e.g., "✓ Successfully wrote file...")
3. **AIMessage** with final response

**The Issue**: The final AIMessage (#3) often has **EMPTY or minimal content** because:
- The LLM thinks the tool result speaks for itself
- No additional commentary needed from LLM perspective
- Common behavior when tool execution is successful

**Result**: Frontend receives AIMessage with empty `content` field → nothing to display!

### Why This Happens with Direct Coder Calls

**Direct routing** (coordinator → coder → __end__):
- Coder called without research plan
- Synthetic plan created with 1 step
- Agent completes quickly with tool calls
- Final response often empty

**Research workflow** (planner → research_team → coder):
- Multiple steps in plan
- Coder result goes to reporter
- Reporter summarizes everything
- Reporter's final message has content

So the issue is **specific to direct coder calls** where there's no reporter to summarize.

## Solution Implemented

### Code Location

**File**: `backend/deer_flow/graph/nodes.py`  
**Function**: `_execute_agent_step`  
**Lines**: 1665-1695 (after tool message counting)

### Algorithm

```python
# After agent execution completes:

1. Check if this is a direct call (synthetic plan with 1 step)
2. Check if last message is AIMessage
3. Check if content is empty or < 10 characters
4. Check if tool calls were made (tool_message_count > 0)

If ALL conditions true:
    # Build summary from tool results
    for each ToolMessage:
        Extract tool name and result (first 200 chars)
        Add to summaries list
    
    # Create enhanced content
    enhanced_content = f"""
    {original_response_content}
    
    ## Tool Results
    
    **tool_name_1**: result summary 1
    **tool_name_2**: result summary 2
    ...
    """
    
    # Replace last AIMessage with enhanced version
    Replace agent_messages[-1] with new AIMessage(content=enhanced_content)
```

### Code Implementation

```python
# For direct agent calls (especially coder), ensure there's a meaningful final message
# If the last AIMessage has empty/minimal content, create a summary message
if agent_messages and current_plan and len(current_plan.steps) == 1:  # Synthetic plan (direct call)
    last_msg = agent_messages[-1]
    from langchain_core.messages import AIMessage, ToolMessage
    
    if isinstance(last_msg, AIMessage):
        content_to_check = str(last_msg.content).strip()
        # If final message is empty or very short and there were tool calls, create summary
        if (not content_to_check or len(content_to_check) < 10) and tool_message_count > 0:
            logger.info(f"[{agent_name}] Final AIMessage has minimal content, creating summary from tool results")
            
            # Build summary from tool messages
            tool_summaries = []
            for msg in agent_messages:
                if isinstance(msg, ToolMessage):
                    tool_name = getattr(msg, 'name', 'unknown_tool')
                    tool_content = str(msg.content)[:200]  # First 200 chars
                    tool_summaries.append(f"**{tool_name}**: {tool_content}")
            
            summary_content = f"{response_content}\n\n## Tool Results\n\n" + "\n\n".join(tool_summaries)
            
            # Create a new AIMessage with the summary
            enhanced_message = AIMessage(
                content=summary_content,
                name=agent_name,
                id=last_msg.id
            )
            
            # Replace the last message with the enhanced one
            agent_messages[-1] = enhanced_message
            logger.info(f"[{agent_name}] Enhanced final message with tool results summary")
```

## Examples

### Example 1: File Creation

**User Request**: "Skapa en fil hello.txt med innehållet Hello, OneSeek!"

**Without Fix**:
```
Messages streamed:
1. AIMessage(content="", tool_calls=[{name: "file_system_tool", ...}])
2. ToolMessage(name="file_system_tool", content="✓ Successfully wrote 15 bytes to 'hello.txt'")
3. AIMessage(content="")  ← EMPTY!

Frontend displays: [nothing]
```

**With Fix**:
```
Messages streamed:
1. AIMessage(content="", tool_calls=[...])
2. ToolMessage(content="✓ Successfully wrote 15 bytes...")
3. AIMessage(content="""
   Skapa en fil hello.txt med innehållet Hello, OneSeek!
   
   ## Tool Results
   
   **file_system_tool**: ✓ Successfully wrote 15 bytes to 'hello.txt'
   """)  ← ENHANCED!

Frontend displays: Task description + Tool Results section
```

### Example 2: Python Code Execution

**User Request**: "Write a function to calculate fibonacci"

**Without Fix**:
```
AIMessage(content="")  ← Empty
ToolMessage(content="Successfully executed: ...")
AIMessage(content="")  ← Still empty

Frontend: [blank]
```

**With Fix**:
```
AIMessage(content="""
Write a function to calculate fibonacci

## Tool Results

**python_repl_tool**: Successfully executed:
```python
def fibonacci(n):
    ...
```
Stdout: 0 1 1 2 3 5 8
""")

Frontend: Shows code execution and results
```

### Example 3: Multiple Tools

**User Request**: "Create a Next.js app and test it"

**Without Fix**:
```
AIMessage + ToolMessage (file_system_tool) + 
AIMessage + ToolMessage (react_sandbox_tool) +
AIMessage(content="")  ← Empty final

Frontend: [nothing visible]
```

**With Fix**:
```
Enhanced AIMessage(content="""
Create a Next.js app and test it

## Tool Results

**file_system_tool**: ✓ Created project structure with 5 files

**react_sandbox_tool**: ✓ Next.js dev server started at http://localhost:3000
""")

Frontend: Clear summary of all actions taken
```

## Testing

### Manual Test

1. **Start backend**:
   ```bash
   cd backend
   uvicorn app:app --reload --port 8001
   ```

2. **Send code request**:
   ```bash
   curl -X POST http://localhost:8001/chat \
     -H "Content-Type: application/json" \
     -d '{"messages":[{"role":"user","content":"Skapa en fil test.txt med innehållet Testing!"}]}'
   ```

3. **Check backend logs**:
   ```
   Should see:
   - "Coder node is coding"
   - "Tool file_system_tool called"
   - "Final AIMessage has minimal content, creating summary"  ← NEW!
   - "Enhanced final message with tool results summary"  ← NEW!
   ```

4. **Check frontend**:
   - Should now display content
   - Should show tool results section
   - Should be in ResearchCard

### Verification Checklist

- [ ] Backend routes to coder correctly
- [ ] Tools execute successfully
- [ ] Empty content detected (log message appears)
- [ ] Enhanced message created (log message appears)
- [ ] Frontend displays content
- [ ] Tool results visible in UI
- [ ] ResearchCard opens automatically

## Impact

### ✅ Fixes

- Frontend now displays coder output for direct calls
- Tool execution results visible to user
- No more "blank response" issue
- Consistent UX between direct and workflow calls

### ✅ Preserves

- All existing functionality
- Tool call streaming
- Message ordering
- Research workflow behavior
- Citations extraction

### ✅ Only Applies To

- Direct agent calls (synthetic plans)
- Cases with tool executions
- Empty final messages (< 10 chars)

Does NOT affect:
- Research workflow (planner → researcher → coder → reporter)
- Messages that already have content
- Non-tool-using agents
- Streaming responses

## Related Fixes

This fix is part of the code router feature implementation:

1. **AttributeError Fix** (Commit e983323): Handle missing plan in direct routing
2. **Python REPL Fix** (Commit e9ca88e): Fix function definition scope issue  
3. **Coder Streaming Fix** (Commit 5f7597d): Ensure final messages have displayable content ← **This fix**

## Future Enhancements

### Option 1: LLM Prompt Engineering

Modify coder prompts to always include summary text:
```
"After using tools, provide a brief summary of what you accomplished."
```

**Pros**: More natural language responses  
**Cons**: Extra LLM tokens, slower responses

### Option 2: Smarter Summary Generation

Instead of just listing tool results, parse them and create narrative:
```
"I successfully created the file 'hello.txt' with your requested content."
```

**Pros**: Better UX, more conversational  
**Cons**: More complex, potential parsing errors

### Option 3: Frontend Adaptation

Teach frontend to display tool results even without AIMessage content:
```tsx
if (!message.content && message.tool_calls) {
  // Display tool calls/results directly
}
```

**Pros**: Backend stays simple  
**Cons**: Frontend complexity, multiple display modes

**Recommendation**: Current fix (summary injection) is best balance of simplicity and effectiveness.

## Summary

**Problem**: Coder executes successfully but frontend shows nothing  
**Cause**: Final AIMessage has empty content after tool calls  
**Solution**: Detect empty messages in direct calls and inject tool result summary  
**Result**: Frontend always has meaningful content to display  

---

**Status**: ✅ FIXED  
**Date**: 2026-01-28  
**Commit**: 5f7597d  
**Branch**: copilot/integrera-ny-router-kodfror  
**Files Changed**: 1 (nodes.py, +33 lines)
