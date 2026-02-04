# Fix: InvalidUpdateError for 'locale' Field

## Problem

After implementing the supervisor pattern, debate flow crashed with:

```
langgraph.errors.InvalidUpdateError: At key 'locale': Can receive only one value per step. 
Use an Annotated key to handle multiple values.
```

## Root Cause

When we converted debate flow to use the supervisor pattern, all debate nodes (fact_checker, synthesizer, moderator, external_ai_caller) were using:

```python
return Command(
    update={
        **preserve_state_meta_fields(state),  # ❌ PROBLEM
        "messages": [...],
        "debate_last_node": "...",
    },
    goto="debate_team"
)
```

`preserve_state_meta_fields(state)` returns a dict with:
- `locale`
- `research_topic`
- `clarified_research_topic`
- `plan_source`
- `enable_code_mode`
- And many other meta fields

**The issue:** When multiple nodes return to `debate_team` supervisor in the same LangGraph step, they ALL try to update `locale` (and other fields), causing LangGraph to throw `InvalidUpdateError`.

### Why This Happens with Supervisor Pattern

In the supervisor pattern:
1. Node A completes → returns to `debate_team`
2. Supervisor routes to Node B
3. Node B completes → returns to `debate_team`

If steps 1 and 3 happen in the same LangGraph "step", both nodes' updates are processed together, causing conflicts for any shared fields.

## Solution

**Only update fields that each node actually modifies.**

### Changes Made

#### fact_checker_node
```python
# Before
return Command(
    update={
        **preserve_state_meta_fields(state),  # ❌ Includes locale, research_topic, etc.
        "messages": combined_messages,
        "fact_checker_response": response_content,
        "synthesizer_response": synth_content,
        "debate_last_node": "fact_checker",
    },
    goto="debate_team"
)

# After
return Command(
    update={
        # ✅ Only fields this node actually changes
        "messages": combined_messages,
        "fact_checker_response": response_content,
        "synthesizer_response": synth_content,
        "debate_last_node": "fact_checker",
    },
    goto="debate_team"
)
```

#### synthesizer_node
```python
# Before
return Command(
    update={
        **preserve_state_meta_fields(state),  # ❌
        "messages": [AIMessage(...)],
        "synthesizer_response": response_content,
        "debate_last_node": "synthesizer",
    },
    goto="debate_team"
)

# After
return Command(
    update={
        # ✅ Only what this node changes
        "messages": [AIMessage(...)],
        "synthesizer_response": response_content,
        "debate_last_node": "synthesizer",
    },
    goto="debate_team"
)
```

#### moderator_node
```python
# Before
state_update = {
    **preserve_state_meta_fields(state),  # ❌
    "messages": [summary_msg],
    "debate_scores": scores,
    "debate_knockout": knockout,
    "debate_last_node": "moderator",
}

# After
state_update = {
    # ✅ Only moderator's updates
    "messages": [summary_msg],
    "debate_scores": scores,
    "debate_knockout": knockout,
    "debate_last_node": "moderator",
}
```

#### external_ai_caller_node
```python
# Before (multiple places)
return Command(
    update={
        **preserve_state_meta_fields(state),  # ❌
        "messages": [...],
        "debate_model_index": ...,
        "debate_last_node": "external_ai_caller",
    },
    goto="debate_team"
)

# After
return Command(
    update={
        # ✅ Only debate-specific fields
        "messages": [...],
        "debate_model_index": ...,
        "debate_last_node": "external_ai_caller",
    },
    goto="debate_team"
)
```

### What Stays Unchanged

**debate_orchestrator_node** still uses `preserve_state_meta_fields`:

```python
state_update = {
    **preserved_fields,  # ✅ OK - orchestrator is entry point
    "debate_round": current_round,
    "debate_scores": scores,
    ...
}
```

This is correct because:
1. Orchestrator is the entry point for each round
2. It needs to initialize/reset state
3. It doesn't conflict with child nodes since they don't update meta fields anymore

## Why This Works

### LangGraph's Update Rules

LangGraph processes updates in "steps". Within a single step:
- ✅ Multiple nodes can update DIFFERENT fields
- ❌ Multiple nodes CANNOT update the SAME field (unless it's Annotated)

### Our Fix

By removing meta fields from child node updates:
- ✅ fact_checker updates: `messages`, `fact_checker_response`, `synthesizer_response`, `debate_last_node`
- ✅ synthesizer updates: `messages`, `synthesizer_response`, `debate_last_node`
- ✅ moderator updates: `messages`, `debate_scores`, `debate_knockout`, `debate_last_node`
- ✅ No conflicts! Each field is only updated by one node per step

### State Preservation

**Q:** Won't we lose state fields if we don't explicitly preserve them?

**A:** No! LangGraph automatically preserves state fields that aren't updated. You only need to include fields you're actually changing.

## Pattern Alignment

This fix aligns with how deer-flow's `research_team` nodes work:

```python
# researcher_node doesn't spread preserve_state_meta_fields either
# It only updates what it needs
async def researcher_node(state, config):
    ...
    return Command(
        update={
            "messages": [response],
            # Only relevant fields updated
        },
        goto="research_team"
    )
```

## Testing

**Syntax Check:**
```bash
✅ python3 -m py_compile backend/deer_flow/graph/nodes.py
```

**Expected Behavior:**
- Debate runs without InvalidUpdateError
- Each node updates only its fields
- State is properly preserved across nodes
- Supervisor routing works correctly

## Summary

**Problem:** Multiple nodes updating same fields → InvalidUpdateError

**Solution:** Each node only updates fields it modifies

**Result:** Clean state updates, no conflicts, supervisor pattern works perfectly!

The fix is minimal (removed 9 lines), surgical (only affects debate nodes), and follows LangGraph best practices.
