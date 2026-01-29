# Debate Mode: Correct Fix Understanding

## The Mistake (Commit 57f1309 - REVERTED)

I incorrectly assumed that the researcher agent should be skipped in debate mode. This was wrong and caused infinite recursion.

### Why It Was Wrong

The debate mode in OneSeek is implemented as **a set of tools** that the researcher agent uses:

1. `start_debate_round(round_number)` - Initializes a debate round
2. `query_model_in_debate(model_key, query)` - Queries a specific AI model
3. `run_internal_analysis(query)` - Runs OneSeek's internal analysis
4. `debater_web_search(query)` - Performs web search for the debate
5. `collect_votes(query)` - Collects votes after round 3
6. `get_debate_summary()` - Gets debate summary

The researcher agent is supposed to:
- Receive the debate prompt (which tells it how to conduct a debate)
- Have access to these debate tools
- Use the tools to orchestrate the debate (start round, query each model, analyze, etc.)

### What Happened When I Skipped The Agent

```python
if enable_debate_mode:
    # My incorrect fix
    return Command(goto="research_team", update={"messages": []})
    # ❌ No agent runs, no tools used, just returns to research_team
```

**Result**: Infinite loop
1. research_team calls researcher_node
2. researcher_node returns to research_team (no work done)
3. research_team calls researcher_node again
4. Loop continues until recursion limit (25)

## The Correct Approach (Restored)

The researcher agent MUST execute with debate tools:

```python
if enable_debate_mode:
    # Correct approach
    debate_tools = get_debate_tools()
    return await _setup_and_execute_agent_step_with_custom_prompt(
        state, config, "researcher", "debate", debate_tools
    )
    # ✅ Agent executes, uses tools to conduct debate
```

**What happens**:
1. researcher_node creates agent with debate prompt + debate tools
2. Agent reads prompt: "You are conducting a multi-round debate..."
3. Agent uses tools to execute debate:
   - `start_debate_round(1)`
   - `query_model_in_debate("gemini-2.5-flash", query)`
   - `query_model_in_debate("claude-3.5-sonnet", query)`
   - `query_model_in_debate("grok-4-fast-reasoning", query)`
   - `query_model_in_debate("oneseek-local", query)`
   - `run_internal_analysis(query)`
4. Agent generates response/report for the step
5. Returns to research_team with results
6. research_team moves to next step (Round 2)

## Why VLLM Was Crashing (Now Fixed)

The VLLM crashes in the user's logs were **NOT** because the agent should be skipped. They were because:

### Issue 1: Token Limits Too Low (30K)
**Log evidence**: `Message compression: 37108 -> 6109 tokens (limit: 30000)`

**Cause**: Qwen default was 30,000 tokens
**Fix**: Updated to 128,000 tokens (commit 3650957)

### Issue 2: Context Explosion from Search Results
**Log evidence**: `Context for oneseek-local round 1: 1270 tokens` → `36797 tokens`

**Cause**: Search results weren't being truncated properly
**Fix**: Aggressive truncation with max_chars limits (commit 666f0a6)

### Issue 3: Web Search Async Pattern
**Cause**: Using `asyncio.to_thread(tool.invoke)` instead of `tool.ainvoke()`
**Fix**: Changed to native async (commit 656317c)

## The Complete Solution

Three actual fixes (not four):

1. **Dynamic Token Limits** (commit 3650957)
   - Read actual 128K limit from config
   - Max context: 76.8K (60% of 128K)

2. **Updated Qwen/Llama Defaults** (commit 3650957)
   - Qwen: 30K → 128K
   - Llama: 4K → 128K

3. **Web Search Async Fix** (commit 656317c)
   - Use `ainvoke()` instead of `asyncio.to_thread(invoke())`

4. ~~Skip Researcher Agent~~ **REVERTED** (commit ab82e8d)
   - This was a mistake based on misunderstanding the architecture
   - Agent must run to use debate tools

## Architecture Understanding

```
User asks for debate
    ↓
coordinator_node creates debate steps:
    - Step 1: "Runda 1: Initiala argument"
    - Step 2: "Runda 2: Utveckling och motargument"  
    - Step 3: "Runda 3: Slutliga positioner och syntes"
    ↓
research_team (loops over steps)
    ↓ for each step
researcher_node
    ├─ In debate mode:
    │  ├─ Create agent with debate prompt
    │  ├─ Give agent debate tools
    │  └─ Agent orchestrates debate using tools
    └─ In research mode:
       └─ Agent does research with search tools
```

## What The User Needs To Do

**Restart the server** for the new token limits to take effect:

```bash
# Stop current OneSeek server
# Restart it
```

The server caches LLM configurations at startup. The new Qwen/Llama 128K limits won't apply until restart.

## Expected Behavior After Fix + Restart

```
✅ DebateFlow initialized with token limit: 128000, max context: 76800
✅ researcher_node: Debate mode enabled - using debate agent with debate tools
✅ Agent starts Round 1
✅ Gemini responds (context: ~2K tokens, limit: 128K)
✅ Claude responds (context: ~4K tokens, limit: 128K)
✅ Grok responds (context: ~6K tokens, limit: 128K)
✅ OneSeek web search (500 chars, ~125 tokens)
✅ OneSeek responds (context: ~8K tokens, limit: 128K)
✅ Round 1 complete
✅ Agent moves to Round 2
✅ [Same pattern for Round 2 and 3]
✅ Debate complete, no crashes
```

## Lessons Learned

1. **Understand the architecture before "fixing"**: The debate tools are meant to be used BY the agent, not instead of it.

2. **VLLM crashes can have multiple causes**: Token limits, context explosion, async patterns - all needed fixing.

3. **Agent execution is not the problem**: The agent is supposed to run - it's the orchestrator of the debate.

4. **Server restarts matter**: Configuration changes don't apply to already-running servers.

## Summary

The correct fix is:
- ✅ Raise token limits to 128K
- ✅ Fix context explosion from search results
- ✅ Fix web search async pattern
- ✅ Let agent execute with debate tools
- ⚠️ Restart server for limits to apply

The incorrect fix was:
- ❌ Skip agent execution (causes recursion)
