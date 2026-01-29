# Sequential Debate Implementation - Complete Guide

## Overview

Successfully integrated **sequential 3-round debate** system using the existing `debate_tools.py` and `debate_flow.py` infrastructure. The debate follows strict rules from the old system:

- ✅ **Sequential execution** (EN I TAGET - ONE AT A TIME)
- ✅ **Randomized order** each round
- ✅ **3 rounds** with accumulating context
- ✅ **Democratic voting** after round 3
- ✅ **Complete summary** with results

## Architecture

### Components

1. **debate_tools.py** - Provides debate orchestration tools
2. **debate_flow.py** - Manages debate state and context
3. **external_ai_caller_node** - Orchestrates debate rounds
4. **external_ai_caller.sv_SE.md** - Instructions for sequential execution

### Models Participating

- **gpt-3.5-turbo** (ChatGPT - OpenAI)
- **gemini-2.5-flash** (Gemini - Google)
- **deepseek-chat** (DeepSeek)
- **grok-4-fast-reasoning** (Grok - xAI)
- **oneseek-local** (OneSeek - creates final synthesis)

## Debate Flow

### Round 1: Initial Argumentation

```
1. start_debate_round(round_number=1, user_query, locale)
   → Returns randomized model order
   
2. For each model in randomized order:
   query_model_in_round(model_key, user_query, locale)
   → Model receives: user_query + chain_so_far
   
   Context: Only previous responses in THIS round
```

**Example Order (randomized):**
1. deepseek-chat
2. oneseek-local
3. gpt-3.5-turbo
4. gemini-2.5-flash
5. grok-4-fast-reasoning

Each model sees the previous models' responses in THIS round only.

### Round 2: Development

```
1. start_debate_round(round_number=2, user_query, locale)
   → New randomized order
   
2. For each model in randomized order:
   query_model_in_round(model_key, user_query, locale)
   → Model receives: user_query + ALL Round 1 + chain_so_far
   
   Context: Complete Round 1 + previous responses in Round 2
```

Models can now build on insights from Round 1 and respond to each other's Round 2 arguments.

### Round 3: Synthesis and Conclusions

```
1. start_debate_round(round_number=3, user_query, locale)
   → New randomized order
   
2. For each model in randomized order:
   query_model_in_round(model_key, user_query, locale)
   → Model receives: user_query + ALL Round 2 + chain_so_far
   
   Context: Complete Round 1 + Complete Round 2 + previous responses in Round 3
   
3. When OneSeek's turn:
   - OneSeek has access to ALL previous rounds
   - Internal analysis tools available
   - Creates final synthesized answer
   - Can use debater_web_search() for fact verification
```

### Voting (After Round 3)

```
1. collect_debate_votes(user_query)
   → External models vote on best answer
   
Rules:
- External models ONLY (not OneSeek)
- Models CANNOT vote for themselves
- Each model gets ONE vote
- Tool returns voting results with winner
```

**Voting Process:**
- Each external model reviews all Round 3 responses
- Votes for the most compelling, accurate, and well-reasoned answer
- Self-voting is prevented by the system
- Winner declared by majority

### Final Summary

```
get_debate_summary()
→ Returns complete debate overview:
  - All 3 rounds with responses
  - Voting results
  - Winner declaration
  - Participation statistics
```

## Tools Available

### 1. start_debate_round()

```python
async def start_debate_round(
    round_number: int,      # 1, 2, or 3
    user_query: str,        # Original debate question
    locale: str = "sv-SE"   # Language (Swedish default)
) -> str
```

**Returns:**
- Round number
- Randomized model order
- Previous round info
- Language setting

**Purpose:** Initialize a new round with randomized participation order.

### 2. query_model_in_round()

```python
async def query_model_in_round(
    model_key: str,         # "gpt-3.5-turbo", "gemini-2.5-flash", etc.
    user_query: str,        # Original debate question
    locale: str = "sv-SE"   # Language
) -> str
```

**Returns:**
- Model's response
- Position in round
- Context used
- Display name

**Purpose:** Query a specific model with appropriate context for current round.

**Context Provided:**
- **Round 1:** user_query + chain_so_far (this round)
- **Round 2:** user_query + ALL Round 1 + chain_so_far
- **Round 3:** user_query + ALL Round 2 + chain_so_far

### 3. debater_web_search()

```python
async def debater_web_search(query: str) -> str
```

**Returns:** Search results summary

**Purpose:** Perform web search for fact verification. Results are shared with OneSeek for synthesis.

### 4. collect_debate_votes()

```python
async def collect_debate_votes(user_query: str) -> str
```

**Returns:**
- Total voters
- Winner name
- Winner vote count
- Detailed votes from each model
- Voting prompt used

**Purpose:** Collect democratic votes from external models after Round 3.

**Constraints:**
- Only callable after Round 3
- Only external models vote (not OneSeek)
- Models cannot vote for themselves

### 5. get_debate_summary()

```python
async def get_debate_summary() -> str
```

**Returns:**
- Total rounds
- Current round
- All responses per round
- Internal analyses count

**Purpose:** Get complete debate overview.

## Implementation Details

### external_ai_caller_node (nodes.py)

```python
async def external_ai_caller_node(
    state: State, config: RunnableConfig
) -> Command[Literal["fact_checker"]]:
    """
    Orchestrates sequential debate rounds using debate_tools.
    
    - Imports get_debate_tools()
    - Creates agent with debate tools
    - Agent follows external_ai_caller.sv_SE.md instructions
    - Executes 3 rounds sequentially
    - Collects votes and summary
    - Routes to fact_checker with results
    """
```

**Key Changes:**
- Replaced parallel AI comparison tools with sequential debate_tools
- Agent now orchestrates entire 3-round debate
- Uses proven debate_flow.py infrastructure

### external_ai_caller.sv_SE.md (Prompt)

```markdown
# External AI Caller - Debattorkestrator

Instructs agent to:
1. Call start_debate_round for each round (1, 2, 3)
2. For each model in randomized order:
   - Call query_model_in_round sequentially
3. After Round 3: Call collect_debate_votes
4. Finally: Call get_debate_summary

Emphasizes:
- **EN I TAGET** (ONE AT A TIME)
- Strict round order
- Sequential, not parallel
- Democratic voting
```

## State Management

### debate_flow.py State

```python
class DebateFlow:
    current_round: int              # 0, 1, 2, or 3
    chain_so_far: List              # Current round responses
    full_previous_round: List       # Complete previous round
    debate_history: List            # All rounds history
    oneseek_analyses: List          # Internal analyses
    facts: List                     # Shared facts from searches
```

**Context Control:**
- Round 1: chain_so_far only
- Round 2: full_previous_round (Round 1) + chain_so_far
- Round 3: full_previous_round (Round 2) + chain_so_far

## Benefits

### 1. Sequential Chain-of-Thought
- Each model builds on previous responses
- Natural debate progression
- Better context understanding

### 2. Fair Randomization
- Order changes each round
- No model consistently goes first/last
- Equal opportunity to respond to others

### 3. Context Accumulation
- Round 2 models see ALL Round 1
- Round 3 models see ALL Round 2
- Rich context for informed responses

### 4. OneSeek Synthesis
- OneSeek participates as equal debater
- Internal analysis between responses
- Final synthesis in Round 3 with complete context
- Web search for fact verification

### 5. Democratic Voting
- External models vote objectively
- Cannot vote for themselves
- Fair winner determination

## Example Debate Flow

```
User Question: "Vad är fördelarna och nackdelarna med AI i utbildning?"

=== RUNDA 1: Initial Argumentation ===
start_debate_round(1, "Vad är fördelarna...", "sv-SE")
→ Order: [gemini, deepseek, oneseek, grok, gpt]

query_model_in_round("gemini-2.5-flash", "Vad är fördelarna...", "sv-SE")
→ Gemini: "AI kan personalisera lärandet..."

query_model_in_round("deepseek-chat", "Vad är fördelarna...", "sv-SE")
→ DeepSeek sees Gemini's response, adds: "Instämmer men oro för data..."

query_model_in_round("oneseek-local", "Vad är fördelarna...", "sv-SE")
→ OneSeek sees Gemini + DeepSeek, synthesizes...

(continues with grok and gpt)

=== RUNDA 2: Vidareutveckling ===
start_debate_round(2, "Vad är fördelarna...", "sv-SE")
→ New order: [grok, oneseek, gpt, gemini, deepseek]

query_model_in_round("grok-4-fast-reasoning", "Vad är fördelarna...", "sv-SE")
→ Grok sees ALL Round 1: "Bygger på tidigare poäng om personalisering..."

(continues sequentially with new order)

=== RUNDA 3: Syntes ===
start_debate_round(3, "Vad är fördelarna...", "sv-SE")
→ New order: [deepseek, gpt, gemini, grok, oneseek]

(All models respond with full context from Rounds 1 & 2)

query_model_in_round("oneseek-local", "Vad är fördelarna...", "sv-SE")
→ OneSeek creates final synthesis with ALL context
→ Uses debater_web_search() for verification

=== RÖSTNING ===
collect_debate_votes("Vad är fördelarna...", "sv-SE")
→ gemini votes for: oneseek-local
→ deepseek votes for: grok-4-fast-reasoning
→ grok votes for: oneseek-local
→ gpt votes for: oneseek-local
→ Winner: oneseek-local (3 votes)

=== SAMMANFATTNING ===
get_debate_summary()
→ Complete overview of all 3 rounds + voting
```

## Testing

To test the sequential debate:

1. **Start a debate:** Enable debate mode in coordinator
2. **Accept plan:** Approve the debate plan
3. **Monitor execution:** Watch logs for sequential calls
4. **Verify rounds:** Check that 3 rounds complete
5. **Check voting:** Ensure votes are collected
6. **Review summary:** Verify complete summary

**Expected behavior:**
- Models called one at a time (not parallel)
- Different order each round
- Context accumulates
- Voting happens after Round 3
- Summary provided

## Troubleshooting

### Issue: Models called in parallel
**Solution:** Check external_ai_caller.sv_SE.md prompt emphasizes "EN I TAGET"

### Issue: Same order every round
**Solution:** Verify start_debate_round() is called for each round

### Issue: No context accumulation
**Solution:** Check debate_flow.py state management

### Issue: No voting
**Solution:** Ensure collect_debate_votes() is called after Round 3

### Issue: Incomplete summary
**Solution:** Verify get_debate_summary() is called at end

## Conclusion

The sequential debate system is now fully integrated using the proven `debate_tools.py` and `debate_flow.py` infrastructure. The system provides:

✅ Sequential execution (one model at a time)
✅ Randomized order (fair participation)
✅ Context accumulation (informed responses)
✅ Democratic voting (objective winner)
✅ Complete summary (full transparency)

This creates a **real debate** with actual AI model responses following structured rules!
