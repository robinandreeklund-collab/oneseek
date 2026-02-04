# Applying Deer-Flow's Supervisor Pattern to OneSeek Debate

## Problem Statement

Användaren påpekar att i deer-flow är **researcher en node inom research_team** (supervisor pattern). På samma sätt har OneSeek **ett debate team med en fact_checker node**. Frågan är: **Hur kan vi få OneSeek's debate LangGraph chain att fungera för faktakontroll?**

## Current Architecture Analysis

### Deer-Flow's Research Team (Original)

```
research_team_node (Supervisor)
    ├── continue_to_running_research_team() (Router function)
    │
    ├─→ researcher_node (for RESEARCH steps)
    ├─→ analyst_node (for ANALYSIS steps)
    └─→ coder_node (for PROCESSING steps)
```

**How it works:**
1. `research_team_node` is a pass-through node (no logic)
2. `continue_to_running_research_team()` reads the plan and routes to the right agent
3. Each agent (researcher/analyst/coder) executes ONE step
4. After execution, returns to `research_team` via Command
5. `continue_to_running_research_team()` routes to next step or exits

**Key insight:** The supervisor DOESN'T execute logic - it just routes!

### OneSeek's Current Debate Flow

```
debate_orchestrator_node
    ↓
external_ai_caller_node (calls AI models one by one)
    ↓
fact_checker_node (verifies ALL responses)
    ↓
synthesizer_node (synthesizes findings)
    ↓
moderator_node (scores and decides)
    ↓
debate_orchestrator_node (next round or exit)
```

**Current issue:**
- Flow is SEQUENTIAL and FIXED
- fact_checker runs AFTER all AI models are called
- No supervisor pattern - nodes are chained with static edges
- fact_checker is an agent that can loop internally (tool calls)

## The Discrepancy

**What's different:**

| Deer-Flow Research | OneSeek Debate |
|-------------------|----------------|
| Supervisor routes to discrete tasks | Orchestrator chains sequential nodes |
| Each task is ONE step from a plan | Each node runs full logic (no discrete steps) |
| researcher does ONE search task | fact_checker verifies ALL claims at once |
| Routes back to supervisor after each step | Chains through all nodes before returning |

**The key issue:** OneSeek's debate doesn't have a **plan with discrete steps** like deer-flow's research mode. Instead, it has a **fixed pipeline**: AI models → fact_check → synth → moderate.

## Solution: Apply Supervisor Pattern to Debate

### Option 1: Full Supervisor Pattern (Mirrors Deer-Flow)

**Create a debate "plan" with steps:**

```python
# In debate_planner_node, create a plan:
DebatePlan:
  Step 1: AI_QUERY (call external models)
  Step 2: FACT_CHECK (verify claims)
  Step 3: SYNTHESIS (combine findings)
  Step 4: MODERATION (score and decide)
```

**Implement debate_team supervisor:**

```python
def continue_to_running_debate_team(state: State):
    """Route to the next debate step based on completion."""
    current_plan = state.get("debate_plan")
    
    if not current_plan or not current_plan.steps:
        return "debate_orchestrator"  # Back to orchestrator
    
    # Find first incomplete step
    for step in current_plan.steps:
        if not step.execution_res:
            if step.step_type == "AI_QUERY":
                return "external_ai_caller"
            elif step.step_type == "FACT_CHECK":
                return "fact_checker"
            elif step.step_type == "SYNTHESIS":
                return "synthesizer"
            elif step.step_type == "MODERATION":
                return "moderator"
    
    # All steps complete - back to orchestrator
    return "debate_orchestrator"
```

**Graph structure:**

```
debate_orchestrator
    ↓
debate_team (supervisor)
    ├─→ external_ai_caller (step 1) → debate_team
    ├─→ fact_checker (step 2) → debate_team
    ├─→ synthesizer (step 3) → debate_team
    └─→ moderator (step 4) → debate_orchestrator
```

**Pros:**
- ✅ Mirrors deer-flow's proven pattern
- ✅ Each node is discrete and focused
- ✅ Easy to add/remove steps
- ✅ Natural stopping points (no internal loops)

**Cons:**
- ❌ Requires creating a "debate plan" structure
- ❌ More refactoring needed
- ❌ May be overkill for a fixed 4-step pipeline

### Option 2: Simplified Supervisor (Pragmatic)

**Keep current flow but add supervisor routing:**

Instead of static edges between nodes, use a debate_team supervisor to route:

```python
def continue_to_running_debate_team(state: State):
    """Simple router for debate pipeline."""
    
    # Check which step was just completed
    last_node = state.get("debate_last_node", "")
    
    if not last_node or last_node == "debate_orchestrator":
        return "external_ai_caller"
    elif last_node == "external_ai_caller":
        return "fact_checker"
    elif last_node == "fact_checker":
        return "synthesizer"
    elif last_node == "synthesizer":
        return "moderator"
    elif last_node == "moderator":
        return "debate_orchestrator"
    
    # Default: back to orchestrator
    return "debate_orchestrator"
```

**Graph structure:**

```python
# In builder.py
builder.add_node("debate_team", debate_team_node)  # Supervisor (pass-through)
builder.add_node("external_ai_caller", external_ai_caller_node)
builder.add_node("fact_checker", fact_checker_node)
builder.add_node("synthesizer", synthesizer_node)
builder.add_node("moderator", moderator_node)

# Add conditional edges from debate_team
builder.add_conditional_edges(
    "debate_team",
    continue_to_running_debate_team,
    [
        "external_ai_caller",
        "fact_checker",
        "synthesizer",
        "moderator",
        "debate_orchestrator",
    ]
)

# Each node returns to debate_team
builder.add_edge("external_ai_caller", "debate_team")
builder.add_edge("fact_checker", "debate_team")
builder.add_edge("synthesizer", "debate_team")
builder.add_edge("moderator", "debate_team")
```

**Pros:**
- ✅ Minimal refactoring
- ✅ Applies supervisor pattern
- ✅ Maintains current flow logic
- ✅ Each node becomes discrete (no internal routing)

**Cons:**
- ❌ Not as flexible as full plan-based approach
- ❌ Still a fixed pipeline (not step-based)

### Option 3: Hybrid - Keep Current but Fix fact_checker

**Minimal change: Keep current architecture but fix the fact_checker loop issue**

The REAL problem isn't the architecture - it's that fact_checker internally loops with tools. Solution:

```python
# In fact_checker_node:
# 1. Remove agent architecture (no tools)
# 2. Make it a simple LLM call with pre-searched data
# 3. All searches happen BEFORE fact_checker is called

# Pseudocode:
async def fact_checker_node(state, config):
    # Get pre-searched data from debate_flow
    search_results = debate_flow.get_all_search_results_for_round(current_round)
    
    # Build prompt with all data
    messages = [
        SystemMessage("You are a fact checker. Here are search results..."),
        HumanMessage(f"Verify these claims: {external_ai_responses}")
    ]
    
    # Simple LLM call (NO TOOLS, NO LOOP)
    llm = get_llm_by_type("fact_checker")
    response = await llm.ainvoke(messages)
    
    # Return result
    return Command(
        update={"messages": [response]},
        goto="synthesizer"
    )
```

**Pros:**
- ✅ Minimal code change
- ✅ Keeps current architecture
- ✅ Fixes the loop issue
- ✅ Fast to implement

**Cons:**
- ❌ Doesn't apply deer-flow's pattern
- ❌ Less flexible for future changes

## Recommended Solution: Option 2 (Simplified Supervisor)

**Why Option 2 is best:**

1. **Applies deer-flow's pattern** without over-engineering
2. **Minimal refactoring** required
3. **Fixes the architecture** to be more maintainable
4. **Each node becomes discrete** (like researcher in research_team)
5. **Easy to debug** - supervisor routing is explicit

## Implementation Steps

### Step 1: Update builder.py

```python
def continue_to_running_debate_team(state: State):
    """
    Route to the next debate step in the pipeline.
    Mirrors research_team supervisor pattern but for debate flow.
    """
    last_node = state.get("debate_last_node", "")
    
    logger.debug(f"[debate_team] Routing from last_node={last_node}")
    
    # Pipeline: external_ai_caller → fact_checker → synthesizer → moderator → orchestrator
    if not last_node or last_node == "debate_orchestrator":
        return "external_ai_caller"
    elif last_node == "external_ai_caller":
        return "fact_checker"
    elif last_node == "fact_checker":
        return "synthesizer"
    elif last_node == "synthesizer":
        return "moderator"
    elif last_node == "moderator":
        return "debate_orchestrator"
    
    # Fallback
    logger.warning(f"[debate_team] Unknown last_node={last_node}, routing to orchestrator")
    return "debate_orchestrator"


def _build_base_graph():
    # ... existing code ...
    
    # Add debate_team supervisor node
    builder.add_node("debate_team", debate_team_node)  # Supervisor
    
    # Add debate nodes
    builder.add_node("external_ai_caller", external_ai_caller_node)
    builder.add_node("fact_checker", fact_checker_node)
    builder.add_node("synthesizer", synthesizer_node)
    builder.add_node("moderator", moderator_node)
    
    # debate_orchestrator routes to debate_team to start the pipeline
    # (update debate_orchestrator_node to route to "debate_team" instead of "external_ai_caller")
    
    # Add conditional edges from debate_team supervisor
    builder.add_conditional_edges(
        "debate_team",
        continue_to_running_debate_team,
        [
            "external_ai_caller",
            "fact_checker",
            "synthesizer",
            "moderator",
            "debate_orchestrator",
        ]
    )
    
    # Each node returns to debate_team supervisor
    builder.add_edge("external_ai_caller", "debate_team")
    builder.add_edge("fact_checker", "debate_team")
    builder.add_edge("synthesizer", "debate_team")
    builder.add_edge("moderator", "debate_team")
```

### Step 2: Update nodes to set debate_last_node

```python
# In external_ai_caller_node:
async def external_ai_caller_node(state, config):
    # ... existing logic ...
    
    return Command(
        update={
            **preserve_state_meta_fields(state),
            "messages": [...],
            "debate_last_node": "external_ai_caller",  # Track completion
            # ... other updates ...
        },
        goto="debate_team"  # Return to supervisor
    )

# Similarly for fact_checker_node, synthesizer_node, moderator_node
```

### Step 3: Update debate_orchestrator routing

```python
async def debate_orchestrator_node(state, config):
    # ... existing logic ...
    
    # Start new round by routing to debate_team supervisor
    return Command(
        update={
            **preserve_state_meta_fields(state),
            "debate_round": current_round,
            "debate_last_node": "debate_orchestrator",  # Reset for new round
            # ... other updates ...
        },
        goto="debate_team"  # Route to supervisor, not directly to external_ai_caller
    )
```

## Benefits of This Approach

### 1. Mirrors Deer-Flow's Pattern

```
Deer-Flow:                    OneSeek Debate:
research_team → researcher    debate_team → external_ai_caller
             ↓                            ↓
             research_team               debate_team
             ↓                            ↓
             analyst                      fact_checker
             ↓                            ↓
             research_team               debate_team
```

**Same pattern, different domain!**

### 2. Fixes fact_checker Loop Issue

- fact_checker no longer controls its own flow
- It's called BY the supervisor when it's time
- It executes, updates state, returns to supervisor
- Supervisor decides what's next

### 3. Makes Each Node Discrete

**Before:**
```
fact_checker_node (agent with tools)
    ├─ web_search (tool call 1)
    ├─ web_search (tool call 2)
    ├─ web_search (tool call 3) → LOOP!
    └─ routes to synthesizer
```

**After:**
```
fact_checker_node (discrete step)
    ├─ Execute fact-checking logic
    ├─ Use pre-searched data
    └─ Return to debate_team supervisor
    
debate_team supervisor
    ├─ Routes to next step (synthesizer)
```

### 4. Natural Control Flow

The supervisor acts as a **circuit breaker**:
- Each node can only run ONCE per round
- No internal loops within nodes
- Clear entry/exit points
- Easy to add logging and monitoring

## Comparison: Before vs After

### Before (Current - Static Edges)

```python
# builder.py
builder.add_edge("fact_checker", "synthesizer")  # Static!
builder.add_edge("synthesizer", "moderator")     # Static!
builder.add_edge("moderator", "debate_orchestrator")  # Static!

# fact_checker can internally loop with tool calls
# → GraphRecursionError
```

### After (Supervisor Pattern)

```python
# builder.py
builder.add_conditional_edges(
    "debate_team",
    continue_to_running_debate_team,  # Dynamic routing!
    ["external_ai_caller", "fact_checker", "synthesizer", "moderator", "debate_orchestrator"]
)

builder.add_edge("fact_checker", "debate_team")  # Return to supervisor

# fact_checker can't loop - it returns to supervisor after ONE execution
# → No GraphRecursionError
```

## Testing Strategy

1. **Unit test the router function:**
```python
def test_debate_team_router():
    state = {"debate_last_node": "external_ai_caller"}
    assert continue_to_running_debate_team(state) == "fact_checker"
    
    state = {"debate_last_node": "fact_checker"}
    assert continue_to_running_debate_team(state) == "synthesizer"
```

2. **Integration test the flow:**
```python
async def test_debate_flow():
    state = {
        "research_topic": "Test topic",
        "debate_round": 1,
        "debate_last_node": "debate_orchestrator"
    }
    
    # Start with orchestrator
    result = await debate_orchestrator_node(state, config)
    assert result.goto == "debate_team"
    
    # Supervisor routes to external_ai_caller
    assert continue_to_running_debate_team(result.update) == "external_ai_caller"
    
    # ... test full pipeline ...
```

3. **Verify no loops:**
```python
async def test_no_recursion():
    # Run a full debate round
    # Ensure fact_checker only runs ONCE
    # Ensure total iterations < 10 (not 100)
```

## Summary

**The key insight:** Deer-flow's research_team supervisor pattern can be applied to OneSeek's debate flow by:

1. Adding a `debate_team` supervisor node (pass-through)
2. Creating a `continue_to_running_debate_team()` router function
3. Using conditional edges instead of static edges
4. Having each node return to the supervisor instead of routing directly

This makes the debate flow **structured, predictable, and loop-free** - just like deer-flow's research mode!

**Result:** Faktakontroll fungerar eftersom fact_checker är en diskret step som körs EN gång per runda, kontrollerad av supervisor, precis som researcher i deer-flow's research_team.
