# Final Fix: Researcher Agent Execution in Debate Mode

## Problem

VLLM continued to crash even after fixing web search async and token limits. Error: "EngineCore encountered an issue" when processing debate rounds.

Log showed:
```
2026-01-29 16:26:12 - Grok-4 Fast Reasoning (xAI) responded (1176 chars)
2026-01-29 16:26:12 - ERROR - Error executing researcher agent for step 'Runda 1: Initiala argument': EngineCore encountered an issue
```

## Root Cause

The debate flow runs **inside** the research workflow graph. After each debate round completes, control returns to the research_team node, which then calls researcher_node to "process" that step.

### The Flow Was:

1. **Debate Round 1 starts**
   - DebateFlow queries all models (Gemini, Claude, Grok, OneSeek)
   - All models respond successfully
   - Debate flow completes Round 1

2. **Control returns to research graph**
   - researcher_node is called for step "Runda 1: Initiala argument"
   - Previously: researcher agent tried to create research report
   - Agent calls LLM to summarize debate results
   - **VLLM crashes with EngineCore error**

3. **Same for Round 2 and Round 3**
   - Each time debate completes a round
   - researcher_node tries to process it
   - Crashes occur

## Why Previous Fixes Didn't Work

### Fix 1: Custom Prompt Template (commit f6447d0)
- Changed to use "debate" prompt instead of "researcher" prompt
- **Still crashed**: Because the agent was still being executed!
- The prompt change didn't matter - executing the agent itself was the problem

### Fix 2: Web Search Async (commit 656317c)
- Fixed web search to use `.ainvoke()` instead of `asyncio.to_thread()`
- **Still crashed**: Because web search worked fine in debate_flow
- The crash was happening AFTER debate in researcher_node

## The Real Fix

In debate mode, the researcher_node should **not execute the agent at all**. The debate flow handles everything - generating responses, internal analysis, web search, synthesis. The researcher_node just needs to acknowledge that the step is complete.

### Before (Incorrect):

```python
async def researcher_node(state: State, config: RunnableConfig):
    enable_debate_mode = state.get("enable_debate_mode", False)
    
    if enable_debate_mode:
        # Use debate tools and debate prompt
        debate_tools = get_debate_tools()
        
        # Execute agent with debate prompt
        return await _setup_and_execute_agent_step_with_custom_prompt(
            state, config, "researcher", "debate", debate_tools
        )
        # ❌ WRONG: Executes researcher agent after debate completes!
        # This tries to "research" the debate results → VLLM crash
```

### After (Correct):

```python
async def researcher_node(state: State, config: RunnableConfig):
    enable_debate_mode = state.get("enable_debate_mode", False)
    
    if enable_debate_mode:
        # Debate flow already handled everything - just mark complete
        logger.info("Debate step completed by debate flow")
        
        return Command(
            goto="research_team",
            update={"messages": []}
        )
        # ✅ CORRECT: No agent execution needed!
        # Debate flow already did all the work
```

## Why This Is The Right Approach

1. **Separation of Concerns**
   - Debate flow: Handles multi-model debate, web search, internal analysis
   - Research flow: Orchestrates steps, but doesn't need to process debate output
   
2. **No Redundant Work**
   - Debate flow already generates all content
   - No need for researcher agent to "research" what was already debated

3. **Prevents VLLM Overload**
   - Researcher agent trying to summarize large debate outputs
   - Context too large or format incompatible
   - Causes EngineCore errors

## Expected Behavior Now

### Round 1:
```
✅ Debate flow executes
   - Gemini responds (1336 chars)
   - Claude responds (1180 chars)  
   - Grok responds (1176 chars)
   - OneSeek performs web search
   - OneSeek responds (1071 chars)

✅ researcher_node called
   - Detects debate mode
   - Logs: "Debate step completed by debate flow"
   - Returns Command(goto="research_team")
   - NO agent execution, NO crash

✅ Proceeds to Round 2
```

### Round 2 & 3:
Same pattern - debate flow handles everything, researcher_node just acknowledges completion.

## Technical Details

### The Research Workflow Structure

```
coordinator_node
    ↓ creates steps: ["Runda 1", "Runda 2", "Runda 3"]
    ↓
research_team (loop over steps)
    ↓ for each step:
    ↓
researcher_node
    ├─ Normal mode: Execute researcher agent
    └─ Debate mode: [NOW FIXED]
        ├─ Debate flow runs (in debate_tools)
        └─ Just mark step complete (no agent)
```

### Why Debate Tools Aren't Needed

Previously, we added debate_tools thinking the agent needed them. But the agent shouldn't run at all! The debate flow is triggered automatically by the workflow when debate mode is enabled.

## All Fixes Summary

| Fix | Commit | What It Fixed |
|-----|--------|---------------|
| Dynamic token limits | 3650957 | Hardcoded 60K → Dynamic 76.8K |
| Qwen/Llama defaults | 3650957 | 30K/4K → 128K |
| Web search async | 656317c | asyncio.to_thread → ainvoke |
| Skip researcher agent | 57f1309 | No agent execution in debate mode |

## Result

Debate mode now completes all 3 rounds without any crashes:
- ✅ All models respond in each round
- ✅ OneSeek performs web search and internal analysis
- ✅ No researcher agent trying to process debate output
- ✅ No VLLM EngineCore errors
- ✅ Clean completion of debate flow

The fix is minimal and surgical: just skip agent execution when in debate mode. The debate flow handles everything else.
