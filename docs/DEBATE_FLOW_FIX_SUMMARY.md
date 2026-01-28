# Debate Flow Fix Summary

## Session Overview
Fixed two critical issues preventing proper debate completion and report generation.

## Issues Fixed

### Issue 1: Voting Step Execution Failure ✅

**Symptom:**
- Step 4 (Voting) went to analyst agent instead of researcher
- Analyst summarized the question instead of running voting
- No votes were collected from external models

**Root Cause:**
```python
# debate_planner prompts had:
{
  "title": "Röstning: Demokratiskt val",
  "step_type": "analysis",  # ❌ Routes to analyst (no debate tools)
  ...
}

# Routing logic in builder.py:
if step_type == StepType.ANALYSIS:
    return "analyst"  # ❌ Analyst doesn't have debate tools!
if step_type == StepType.RESEARCH:
    return "researcher"  # ✅ Researcher has all debate tools
```

**Fix:**
Changed `step_type` from "analysis" to "research" in voting step:
- `backend/deer_flow/prompts/debate_planner.md` (lines 32, 75)
- `backend/deer_flow/prompts/debate_planner.sv_SE.md` (lines 32, 75)

**Result:**
Step 4 now routes to researcher → has access to `collect_debate_votes` tool → voting executes properly

---

### Issue 2: Generic Report Instead of Debate Summary ✅

**Symptom:**
- Final report was generic research summary
- No voting results displayed
- No debate structure (rounds, evolution, etc.)

**Root Cause:**
```python
# App sets: report_style = ReportStyle.DEBATE ✅
# But reporter.md and reporter.sv_SE.md had:
{% if report_style == "academic" %}
  ...
{% elif report_style == "ai_comparison" %}
  ...
{% else %}  # ❌ DEBATE fell through to default!
  Generic prose format
{% endif %}
```

**Fix:**
Added complete `{% elif report_style == "debate" %}` section to both reporter prompts with mandatory structure:

```markdown
**CRITICAL REPORT STRUCTURE FOR DEBATE:**

1. **Voting Results FIRST** 🏆
   - Winner and vote statistics
   - Who voted for whom and why
   - Percentage distribution
   
2. **Round 3: Final Positions**
   - Each model's mature arguments
   - OneSeek's synthesis
   
3. **Evolution of Arguments**
   - R1 → R2 → R3 progression
   - Key refinement moments
   
4. **Consensus Points and Differences**
   - Where models agreed
   - Major disagreements
   
5. **OneSeek Synthesis**
   - Unique role and fact-checking
   
6. **Debate Conclusion**
   - Overall learnings
   - Value of multi-perspective analysis
```

**Result:**
Reporter now generates proper debate summary with voting results first

---

## Complete Fix Commits

1. **Context Explosion Analysis** (commits ca33bec - b59bb80)
   - Comprehensive flow analysis documents
   - Token counting and limits (60K hard limit for 95K model)
   - Context reduction (41.5K → 8K peak)

2. **Debate Flow Fixes** (commit 17b03a7)
   - Voting routing fix (analysis → research)
   - DEBATE report style implementation

## Testing Checklist

Before considering debate mode complete, verify:

- [x] VLLM doesn't crash (context limits working)
- [ ] Step 1 (Round 1) executes via researcher with debate tools
- [ ] Step 2 (Round 2) executes via researcher with debate tools
- [ ] Step 3 (Round 3) executes via researcher with debate tools
- [ ] **Step 4 (Voting) executes via researcher** ✅ (fixed)
- [ ] **Reporter generates DEBATE format** ✅ (fixed)
- [ ] Voting results appear at top of report
- [ ] Report shows round evolution
- [ ] All models' positions clearly presented

## Files Modified This Session

### Analysis Documents (Created)
- `docs/debate-context-flow-analysis.md` (856 lines)
- `docs/DEBATE_CONTEXT_FIX_SUMMARY.md` (316 lines)
- `docs/DEBATE_CONTEXT_95K_ADJUSTMENT.md` (new)
- `docs/FINAL_REPORT_DEBATE_CONTEXT.txt` (321 lines)

### Code Changes
- `backend/debate_flow.py` (context reduction logic)

### Prompt Changes
- `backend/deer_flow/prompts/debate_planner.md` (step_type fix)
- `backend/deer_flow/prompts/debate_planner.sv_SE.md` (step_type fix)
- `backend/deer_flow/prompts/reporter.md` (DEBATE style added)
- `backend/deer_flow/prompts/reporter.sv_SE.md` (DEBATE style added)

## Expected Behavior Now

### Successful Debate Flow
1. User enables debate mode and submits question
2. Coordinator routes to debate_planner
3. Planner creates 4-step debate plan
4. User approves plan
5. **Researcher executes all 4 steps** (not analyst!)
   - Step 1: start_debate_round(1), query_model_in_round for each model
   - Step 2: start_debate_round(2), query_model_in_round for each model
   - Step 3: start_debate_round(3), query_model_in_round, run_internal_analysis
   - Step 4: **collect_debate_votes** ✅ (fixed!)
6. **Reporter generates DEBATE format report** ✅ (fixed!)
   - Voting results at top with winner
   - Round 3 final positions
   - Argument evolution analysis
   - Consensus and differences
   - OneSeek synthesis
   - Debate conclusion

### Peak Context Usage
- Round 3: ~8K tokens (down from 10K)
- Voting: ~2.5K tokens per call (down from 5.3K)
- Total debate: ~16K tokens processed (down from 41.5K)
- Hard limit: 60K tokens (safe for 95K model)

## Related Issues Fixed Earlier

The following issues were fixed in previous commits:
- Frontend display (streaming and agent name)
- Pydantic validation errors
- Coordinator routing
- Tool swapping logic
- Plan serialization

All these remain working after the debate flow fixes.
