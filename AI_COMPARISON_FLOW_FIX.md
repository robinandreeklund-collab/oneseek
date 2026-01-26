# AI Comparison Flow Fix

## Problem (Problemet)

I AI-jämförelseläge skedde faktakontroll (researcher node) EFTER att rapporten genererades, istället för FÖRE eller UNDER jämförelsen.

**In English:** In AI comparison mode, fact-checking (researcher node) happened AFTER the report was generated, instead of BEFORE or DURING the comparison.

### Loggar visade (Logs showed):
1. Rapport genererades först (Swedish content: "Kritisk diskussion", "Referenser", etc.)
2. SEDAN började researcher_node (2026-01-26 16:07:28,876)
3. Researcher gjorde web searches EFTER rapporten var klar

Detta var fel ordning enligt issue #13.

## Grundorsak (Root Cause)

Grafen hade en fast kant (fixed edge):
```python
builder.add_edge("ai_comparison", "reporter")
```

Denna tvingade ai_comparison att gå direkt till reporter, vilket **åsidosatte** Command-returvärdet från ai_comparison_node.

ai_comparison_node returnerar `Command(goto="research_team")` för att säkerställa korrekt flöde genom research pipeline, men den fasta kanten överskred detta.

## Lösning (Solution)

Tog bort den fasta kanten och lade till en kommentar som förklarar det korrekta flödet:

```python
# AI comparison returns Command(goto="research_team") to follow normal flow:
# ai_comparison -> research_team -> planner -> reporter
# This ensures fact-checking happens BEFORE report generation, not after.
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
   ├─ Step completes with execution_res set
   └─ Returns Command(goto="research_team")
4. research_team_node (pass-through)
5. continue_to_running_research_team → checks plan → routes to "planner"
6. planner_node → sees complete plan → routes to "reporter" (via Command)
7. reporter_node → generates final report (with fact-checking already done)
8. END
```

## Nyckelfördel (Key Benefit)

✅ **Faktakontroll sker nu i steg 3** (under AI comparison agent execution via `fact_check_responses` tool)

❌ **INTE efter steg 7** (efter rapportgenerering)

Detta säkerställer att syntes och rapport inkluderar faktakontrollerad information från start, precis som krävs i issue #13.

## Tekniska Detaljer (Technical Details)

I LangGraph finns tre routing-mönster:
1. **Fixed edges**: `builder.add_edge(source, target)` - går alltid till target
2. **Conditional edges**: `builder.add_conditional_edges(source, function, targets)` - anropar funktion för att bestämma
3. **Command returns**: Node returnerar `Command(goto=target)` - Command hanterar routing direkt

ai_comparison_node använder mönster #3 (returnerar `Command[Literal["research_team"]]`), så den ska INTE ha en fast kant. Den fasta kanten åsidosatte Command, vilket orsakade buggen.

## Ändrade Filer (Files Changed)

- `backend/deer_flow/graph/builder.py`: 
  - Removed: 1 line (fixed edge)
  - Added: 3 lines (explanatory comment)

## Verifiering (Verification)

- ✅ Python syntax validerad
- ✅ Kod-granskning slutförd
- ✅ Ändring verifierad för att matcha LangGraph Command routing pattern

## Slutsats (Conclusion)

Denna fix säkerställer att AI-jämförelseläget använder verktygsanrop (tool calls) korrekt i flödet, med faktakontroll som sker INNAN rapporten genereras, precis som specificerats i issue #13.

**The fix ensures that AI comparison mode uses tool calls correctly in the flow, with fact-checking happening BEFORE the report is generated, exactly as specified in issue #13.**
