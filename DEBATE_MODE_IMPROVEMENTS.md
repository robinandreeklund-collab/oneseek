# Debate Mode Improvements - Implementation Summary

## Changes Made

### 1. Enhanced Internal Analysis (`backend/debate_flow.py`)

#### New Method: `run_oneseek_internal_analysis`
Enhanced the internal analysis method to:
- **Analyze all external model responses** (skips OneSeek's own responses)
- **Extract key claims** from each response using `_extract_claims()` helper
- **Verify claims via web search** - performs fact-checking on top 3 claims per model
- **Analyze response evolution** across rounds with `_analyze_response_evolution()`
- **Detect contradictions** between models with `_find_contradictions()`
- **Create synthesis points** for OneSeek's response with `_create_synthesis_points()`

The analysis includes:
```python
{
    "round": int,
    "timestamp": int,
    "insights": [...],           # Per-model analysis
    "claims_extracted": [...],   # All claims found
    "verified_facts": [...],     # Web-verified facts
    "contradictions": [...],     # Opposing statements
    "synthesis_points": [...],   # Synthesis for OneSeek
    "evolution_notes": [...]     # Round-to-round changes
}
```

#### New Helper Methods
- `_extract_claims(response)` - Extracts factual claims from text (max 5 per response)
- `_summarize_search_results(results)` - Summarizes web search verification
- `_analyze_response_evolution(responses)` - Compares responses across rounds
- `_find_contradictions(responses)` - Identifies opposing statements
- `_create_synthesis_points(responses, verified_facts)` - Creates synthesis notes

#### OneSeek Round 1 Web Search
Modified `query_model_in_debate()` to:
- Automatically perform web search **before** OneSeek responds in Round 1
- Store search results as internal knowledge (NOT shared with external models)
- Add knowledge to OneSeek's context only

```python
# SPECIAL: OneSeek does web search in Round 1 before responding
if model_key == "oneseek-local" and self.current_round == 1:
    # Perform internal web search
    oneseek_internal_knowledge = ...
```

#### Updated Context Building
Modified `build_context_for_model()` to:
- Include **internal analysis** in OneSeek's context (last 2 analyses)
- Show synthesis points, verified facts, and contradictions
- Keep analysis **isolated** from external models

### 2. Improved run_internal_analysis Tool (`backend/deer_flow/tools/debate_tools.py`)

Updated the tool to return a detailed, formatted summary:
```markdown
🔍 **OneSeek Intern Analys** (Runda X)

**Analyserade modeller:** Y
**Extraherade påståenden:** Z
**Verifierade fakta:** A
**Identifierade motsättningar:** B

### Extraherade Påståenden
- **Model**: claim...

### Verifierade Fakta
- **Model**: claim...
  *Verifiering:* verification...

### Identifierade Motsättningar
- contradiction...

### Syntes-punkter
- point...

### Utveckling Mellan Ronder
- evolution note...

---
*Detta används internt av OneSeek för att förbättra sitt syntetiserade svar.*
*Analysen delas INTE med externa modeller.*
```

### 3. Aggressive Debate Prompt (`backend/deer_flow/prompts/debate.sv_SE.md`)

Added comprehensive OneSeek strategy section:

#### OneSeeks Speciella Roll och Instruktioner
**"OneSeek är den smartaste och mest övertygande AI:n i rummet."**

Key strategic principles:
1. **Tänk 10 steg före** – djupt kritiskt resonemang i `<tänk>` tags
2. **Knäck motargumenten** – fakta, logik, verifierbara källor
3. **Var skoningslös** – peka ut luckor, motsägelser, bias
4. **Var charmig och vass** – retorik, humor, starka formuleringar
5. **Knockout-argument** – avsluta med argument som sätter punkt
6. **Använd verktyg aggressivt** – backa upp med data
7. **Flytande svenska** – elegant svenska, aldrig engelska
8. **Backa aldrig** – vänd allt till din fördel
9. **Vinna med sanning** – allt faktabaserat och verifierbart

#### Synthesis Building
- **Integrera och förbättra** – ta det bästa från alla sidor
- **Analysera historia** – paralleller, slutsatser, lärdomar
- **Framtidsvision** – baserad på historiska mönster
- **Banbrytande ramverk** – unika lösningar

Updated workflow documentation:
- Round 1: OneSeek web search happens automatically (internal)
- After each round: `run_internal_analysis` creates OneSeek's analysis
- Round 2-3: OneSeek gets internal analyses in context

## Key Features

### Internal Analysis is Isolated
✅ Analysis stored in `self.oneseek_analyses` (never shared)
✅ Only added to OneSeek's context via `build_context_for_model()`
✅ External models never see the analysis

### Web Search Before Round 1
✅ OneSeek performs web search automatically before responding in Round 1
✅ Search results stored as internal knowledge
✅ Knowledge added to OneSeek's context only
✅ External models don't see this search

### Enhanced Analysis
✅ Extracts factual claims from responses
✅ Verifies claims via web search
✅ Detects contradictions between models
✅ Analyzes evolution across rounds
✅ Creates synthesis points for OneSeek

### Aggressive Debate Strategy
✅ Strategic thinking instructions integrated
✅ Focus on winning with verified facts
✅ Synthesis and integration emphasized
✅ Historical analysis and future vision encouraged

## Testing

Created `backend/test_debate_enhancements.py` with unit tests for:
- Claim extraction
- Search result summarization
- Contradiction detection
- Synthesis point creation
- Response evolution analysis

All tests verify the logic of the helper methods.

## Files Changed

1. `backend/debate_flow.py` - Core debate flow with enhanced analysis
2. `backend/deer_flow/tools/debate_tools.py` - Improved tool output
3. `backend/deer_flow/prompts/debate.sv_SE.md` - Aggressive OneSeek strategy
4. `backend/test_debate_enhancements.py` - Unit tests (new)

## Next Steps

The implementation is complete. The debate mode now:
1. ✅ Performs web search before OneSeek's Round 1 response (internal)
2. ✅ Runs comprehensive internal analysis after each round
3. ✅ Uses aggressive debate strategy for OneSeek
4. ✅ Keeps all analysis internal (never shared with external models)
5. ✅ Provides synthesis points for OneSeek's responses

Users can now run debate mode and OneSeek will:
- Build knowledge internally via web search in Round 1
- Analyze all responses comprehensively after each round
- Use verified facts and contradictions in its arguments
- Respond aggressively with strategic thinking
- Create superior synthesis in Round 3
