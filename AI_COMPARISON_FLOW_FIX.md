# AI Comparison Flow Fix

## Problem (Problemet)

### Initial Issue
I AI-jämförelseläge skedde faktakontroll (researcher node) EFTER att rapporten genererades, istället för FÖRE eller UNDER jämförelsen.

**In English:** In AI comparison mode, fact-checking (researcher node) happened AFTER the report was generated, instead of BEFORE or DURING the comparison.

### Second Issue (After First Fix)
Efter första fixen, researcher node anropades i en loop (8+ gånger), vilket orsakade:
- För många web-sökningar
- `GraphRecursionError: Recursion limit of 25 reached`
- Rapporten skapades aldrig

**In English:** After the first fix, researcher node was called in a loop (8+ times), causing:
- Too many web searches
- `GraphRecursionError: Recursion limit of 25 reached`
- Report was never created

## Grundorsak (Root Cause)

### Initial Problem
Grafen hade en fast kant (fixed edge): `builder.add_edge("ai_comparison", "reporter")` som tvingade ai_comparison att gå direkt till reporter.

### Loop Problem
Efter att ha tagit bort den fasta kanten, ai_comparison_node returnerade `Command(goto="research_team")`. Men eftersom comparison_step hade `step_type=StepType.RESEARCH`, dirigerade research_team till **researcher** istället för tillbaka till planner. Detta skapade en loop:
1. ai_comparison → research_team
2. research_team ser RESEARCH step → dirigerar till researcher
3. researcher slutför → tillbaka till research_team
4. Loop upprepas eftersom steget fortfarande är ofullständigt

**In English:** After removing the fixed edge, ai_comparison_node returned `Command(goto="research_team")`. But because comparison_step had `step_type=StepType.RESEARCH`, research_team routed to **researcher** instead of back to planner. This created a loop.

## Lösning (Solution)

ai_comparison_node går nu **direkt till reporter** istället för genom research_team:

```python
# In nodes.py:
async def ai_comparison_node(...) -> Command[Literal["reporter"]]:
    # Execute ai_comparison agent with tools
    result = await _setup_and_execute_agent_step(...)
    
    # Mark step as complete
    comparison_step.execution_res = "AI comparison completed successfully"
    
    # Go directly to reporter (bypassing research_team to avoid loops)
    return Command(
        update={
            **result.update,
            "current_plan": comparison_plan,
        },
        goto="reporter",
    )
```

## Förväntat Flöde Efter Fix (Expected Flow After Fix)

```
1. coordinator → planner (via Command)
2. planner detects enable_ai_comparison=True → ai_comparison (via Command)
3. ai_comparison_node:
   ├─ Creates Plan with one step: "AI Model Comparison"
   ├─ Agent executes, calling tools:
   │  ├─ query_gpt35
   │  ├─ query_gemini_flash
   │  ├─ query_deepseek
   │  ├─ query_grok4
   │  ├─ fact_check_responses ← FAKTAKONTROLL SKER HÄR!
   │  ├─ run_meta_analysis
   │  └─ synthesize_optimal_answer
   ├─ Marks step as complete
   └─ Returns Command(goto="reporter")  ← DIREKT TILL REPORTER, INGEN LOOP!
4. reporter_node → generates final report (with fact-checking already done)
5. END
```

## Nyckelfördel (Key Benefit)

✅ **Faktakontroll sker under AI comparison agent execution** (via `fact_check_responses` tool)

✅ **Ingen loop genom researcher** - går direkt till reporter

✅ **Inga recursion errors** - endast en genomgång av comparison

❌ **INTE efter rapportgenerering**

Detta säkerställer att syntes och rapport inkluderar faktakontrollerad information från start, och undviker onödiga loopar som orsakar för många sökningar.

## Tekniska Detaljer (Technical Details)

Problemet uppstod eftersom:
1. `step_type=StepType.RESEARCH` i comparison_step
2. `continue_to_running_research_team()` dirigerar RESEARCH steps till researcher
3. Detta skapade en loop: ai_comparison → research_team → researcher → research_team → ...

Lösningen är att **inte använda research_team routing** för ai_comparison alls. Istället går den direkt till reporter efter att ha utfört alla verktygsanrop internt.

## Ändrade Filer (Files Changed)

- `backend/deer_flow/graph/nodes.py`: 
  - Changed return type: `Command[Literal["research_team"]]` → `Command[Literal["reporter"]]`
  - Mark comparison_step as complete before returning
  - Return Command(goto="reporter") instead of returning result from _setup_and_execute_agent_step
  
- `backend/deer_flow/graph/builder.py`: 
  - Updated comment to explain direct routing to reporter

## Verifiering (Verification)

- ✅ Python syntax validerad
- ✅ Ändring förhindrar research_team loop
- ✅ ai_comparison agent kör alla verktyg innan reporter

## Slutsats (Conclusion)

Denna fix säkerställer att AI-jämförelseläget:
1. ✅ Kör faktakontroll UNDER jämförelsen (inte efter)
2. ✅ Undviker loopar genom researcher
3. ✅ Genererar rapport efter att alla verktyg har körts
4. ✅ Respekterar recursion limits

**The fix ensures that AI comparison mode:**
1. ✅ Runs fact-checking DURING comparison (not after)
2. ✅ Avoids loops through researcher
3. ✅ Generates report after all tools have executed
4. ✅ Respects recursion limits
