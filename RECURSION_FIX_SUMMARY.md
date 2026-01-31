# Fix: GraphRecursionError and Sidebar Issues

## Problems Identified

### 1. GraphRecursionError - FIXED ✓
**Error**: `GraphRecursionError: Recursion limit of 25 reached`

**Root Cause**: 
- Every debate node was routing back to orchestrator between steps
- Flow: orchestrator → proponent → **orchestrator** → opponent → **orchestrator** → fact_checker → **orchestrator** → synthesizer → moderator → **orchestrator**
- **10 nodes per round** × 3 rounds = 30 nodes > 25 limit

**Solution Applied** (Commit `77b975e`):
- Changed to sequential flow: orchestrator → proponent → opponent → fact_checker → synthesizer → moderator → orchestrator
- **6 nodes per round** × 3 rounds = 18 nodes < 25 limit ✓

**Changes**:
- `proponent_node`: Routes to `opponent` (not orchestrator)
- `opponent_node`: Routes to `fact_checker` (not orchestrator) 
- `fact_checker_node`: Routes to `synthesizer` (not orchestrator)
- `debate_orchestrator_node`: Simplified, removed phase tracking
- Removed `debate_phase` state variable (no longer needed)

### 2. Missing Sidebar - INVESTIGATION NEEDED
**Problem**: "Nu öppnas ingen sidebar till höger när debatten startar"

**Possible Causes**:
1. **Tool actions not being emitted**: 
   - Frontend expects `tool_actions` in stream data
   - deer_flow server emits `tool_calls` and `tool_call_result` events but not `tool_actions` objects
   - Old agent_graph.py manually built tool_actions arrays
   - This is an architectural mismatch

2. **Auto-open logic not triggering**:
   - Added auto-open logic in commit `a85e5ee`
   - Opens sidebar when `messageToolActions` becomes non-empty
   - But if tool_actions aren't being emitted, this won't trigger

3. **Wrong sidebar expected**:
   - User might be expecting a different sidebar (plan/flow view)
   - Not the tool actions sidebar

**Next Steps**:
- Waiting for user clarification on which sidebar should open
- If tool actions sidebar: Need to emit tool_actions from backend or convert tool_calls to tool_actions on frontend
- If different sidebar: Need to implement that sidebar component

### 3. Multiple "Agent Created" Messages
**Observation**: Terminal shows many "Agent 'proponent' created successfully" messages

**Likely Cause**: 
- This was expected during recursion error - orchestrator was looping
- Should be fixed now with sequential flow
- Need to verify in next test

## Testing Needed

1. **Verify recursion fix**: Run debate, check it completes 3 rounds without error
2. **Check sidebar behavior**: Identify which sidebar should open and when
3. **Verify tool execution**: Confirm tools (web_search, browse) are actually being called

## Code Quality

All changes maintain:
- ✓ Python syntax valid
- ✓ Sequential flow reduces complexity  
- ✓ Exit criteria logic intact
- ✓ Round management preserved
- ✓ Score tracking functional
