# Debate Mode Documentation

## Overview

Debate Mode orchestrates a **3-round multi-model debate** where all available AI models (GPT-3.5, Gemini 2.5 Flash, DeepSeek, Grok-4, and OneSeek) participate as **equal debaters**. Each model responds sequentially in randomized order, building on previous arguments through strict chain-of-thought flow. After round 3, external models vote democratically on the best answer.

## Architecture

Debate Mode follows the **same workflow as normal research**, ensuring consistency and reusing proven infrastructure:

### Current Flow

```
start
  │
  ▼
coordinator (analyzes query and routes based on mode)
  │
  ├─ enable_debate_mode=true ──→ debate_planner ──→ human_feedback ──→ research_team ──→ researcher (with debate tools) ──→ reporter ──→ END
  ├─ enable_ai_comparison=true ─→ planner ─────────→ ai_comparison ──→ reporter ──→ END
  └─ normal mode ───────────────→ planner ──────────→ human_feedback ──→ research_team ──→ researcher ──→ reporter ──→ END
```

**Key Principle**: Debate mode reuses the standard research workflow. The only differences are:
1. **debate_planner** creates a debate-specific plan instead of research plan
2. **researcher** receives debate tools instead of search/crawl tools
3. Each AI model query is treated as a tool call within the research workflow

### Key Components

1. **Coordinator Node**
   - Analyzes incoming queries
   - Checks `enable_debate_mode` state flag
   - Routes to debate_planner when debate mode is enabled

2. **Debate Planner Node**
   - Creates a structured debate plan with 4 steps:
     - Step 1: Round 1 (initial arguments from all 5 models)
     - Step 2: Round 2 (development based on Round 1)
     - Step 3: Round 3 (final positions and OneSeek synthesis)
     - Step 4: Voting and summary
   - Routes to `human_feedback` for plan approval (standard workflow)

3. **Human Feedback Node**
   - Reviews and approves the debate plan
   - Routes to `research_team` to execute plan

4. **Research Team → Researcher Node**
   - Executes debate plan steps sequentially
   - **Key Point**: Tools are exposed to LLM ONLY in researcher node, NOT in debate_planner
   - Debate_planner creates plan WITHOUT seeing tools (just knows debate pattern)
   - When researcher receives the plan in debate mode, it loads specialized debate tools:
     - `start_debate_round` - Initialize round with randomized order
     - `query_model_in_round` - Query a specific AI model
     - `run_internal_analysis` - OneSeek's internal fact-checking
     - `collect_debate_votes` - Gather votes from external models
     - `get_debate_summary` - Compile final results
   - Each model query is a tool call, executed in sequence
   - Loops through plan steps until all rounds and voting complete

5. **Debate Flow Engine** (`backend/debate_flow.py`)
   - Manages debate state across 3 rounds
   - Initializes all available AI models (GPT-3.5, Gemini, DeepSeek, Grok-4, OneSeek)
   - Controls `chain_so_far` (current round) vs `full_previous_round` (previous complete round)
   - Runs OneSeek internal analyses between responses
   - Collects votes from external models after round 3

6. **Reporter**
   - Receives complete debate results with all rounds
   - Synthesizes debate findings into comprehensive report
   - Presents voting results and winner

## Features

### Multi-Round Sequential Debate

All AI models participate in a **3-round debate** with these key features:

1. **Equal Participation**: All models (GPT-3.5, Gemini, DeepSeek, Grok-4, OneSeek) are equal debaters
2. **Randomized Order**: Each round randomizes the speaking order - no model has priority
3. **Sequential Chain-of-Thought**: Models respond one at a time, building on previous arguments
4. **Strict Context Control**: Clear separation between rounds prevents context explosion
5. **OneSeek Internal Analysis**: Between responses, OneSeek runs fact-checks via web search
6. **Democratic Voting**: After round 3, external models vote on the best answer (self-voting prevented)
7. **Standard Workflow**: Follows the same proven workflow as normal research (plan → approval → execution → report)

### Round-by-Round Protocol

**Round 1: Initial Arguments**
- First model receives: User question + language rules + token limit
- Subsequent models receive: User question + all responses in current round (chain_so_far)
- Each model provides initial position on the topic

**Round 2: Development**
- All models receive: User question + complete Round 1 + current round responses
- Models develop arguments, respond to others' points, introduce new evidence
- Order is re-randomized from Round 1

**Round 3: Synthesis & Conclusions**
- All models receive: User question + complete Round 2 + current round responses
- **OneSeek special role**: When it's OneSeek's turn, it creates final synthesized answer using:
  - All debate context from rounds 1 & 2
  - Internal analyses and fact-checks performed during debate
  - Web search results for verification
- External models provide final arguments
- Order is re-randomized again

**Voting Phase**
- External models (not OneSeek) vote on best Round 3 answer
- Each model sees all Round 3 responses
- Self-voting is prevented
- Winner determined by most votes

### Context Management

To prevent context explosion across rounds:

```python
# Round 1
chain_so_far = []  # Accumulates Round 1 responses
full_previous_round = []  # Empty

# Round 2
full_previous_round = chain_so_far  # Complete Round 1
chain_so_far = []  # Reset for Round 2

# Round 3
full_previous_round = chain_so_far  # Complete Round 2
chain_so_far = []  # Reset for Round 3
```

### OneSeek Internal Analysis

Between each model response, OneSeek performs internal analysis (NOT shared with other models):

- Fact-checking via web search
- Knowledge gathering from sources
- Logical consistency review
- Identification of errors or misleading claims
- Preparation of counter-arguments

This analysis is used when it's OneSeek's turn to respond, especially for the Round 3 synthesis.

## Usage

### Frontend

1. Click the **"Debate"** / **"Debatt"** button in the input box
2. The button highlights to show debate mode is active
3. Submit your question
4. System generates and executes multi-perspective research plan
5. Receive comprehensive debate analysis report

### Backend API

Enable debate mode by setting the `enable_debate_mode` parameter:

```python
# In chat request
{
  "messages": [...],
  "enable_debate_mode": true,
  "locale": "sv-SE"
}
```

The system will:
1. Route to `debate_planner` node
2. Generate debate-focused research plan
3. Execute plan through standard research workflow
4. Return comprehensive multi-perspective report

## Configuration

### State Fields

- `enable_debate_mode`: Boolean flag to enable debate mode
- `current_plan`: Research plan generated by debate_planner
- `locale`: Language locale (affects prompt selection)

### Agent Configuration

In `backend/deer_flow/config/agents.py`:

```python
AGENT_LLM_MAP = {
    ...
    "debate": "basic",  # LLM type for debate planning
    ...
}
```

### Prompts

Two debate planner prompts:

- **`backend/deer_flow/prompts/debate_planner.md`**: English prompt
- **`backend/deer_flow/prompts/debate_planner.sv_SE.md`**: Swedish prompt

Both emphasize:
- Multi-perspective research
- Balanced argument gathering
- Evidence-based analysis
- Diverse source consultation

## Implementation Details

### Code Reuse Strategy

Debate mode leverages existing infrastructure:

```
✓ Reuses research_team node (no duplication)
✓ Reuses reporter node (standard synthesis)
✓ Reuses human_feedback loop (same pattern)
✓ Only difference: specialized debate_planner with debate-focused prompts
```

### Benefits

1. **Modularity**: Clean separation of planning vs. execution
2. **Maintainability**: Single research workflow to maintain
3. **Consistency**: All research modes follow similar patterns
4. **Scalability**: Easy to add new planner types (compare_planner, etc.)
5. **No Duplication**: Minimal code, maximum reuse

### Routing Logic

In `coordinator_node`:

```python
if state.get("enable_debate_mode", False):
    logger.info("Debate mode enabled, routing to debate_planner")
    goto = "debate_planner"
elif state.get("enable_ai_comparison", False):
    logger.info("AI comparison mode enabled, planner will route to ai_comparison")
    goto = "planner"
else:
    goto = "planner"
```

### Graph Structure

The graph builder adds the debate_planner node:

```python
builder.add_node("debate_planner", debate_planner_node)
```

Routes:
- `coordinator` → `debate_planner` (when debate mode enabled)
- `debate_planner` → `human_feedback`

## Tool Usage in Debate Mode

### How Tools Enable the Debate

The multi-model debate is orchestrated entirely through **tool calls** in the researcher node. Each AI model query, each analysis, and the voting system are all implemented as tools that the LLM agent can call.

### Tool Execution Flow

```
┌──────────────────────────────────────────────────────────────┐
│            Debate Mode Tool Execution Flow                   │
└──────────────────────────────────────────────────────────────┘

1. Debate Plan Created (debate_planner node)
   │
   │ Creates plan with 4 steps:
   │  - Step 1: "Round 1: All models provide initial arguments"
   │  - Step 2: "Round 2: Models develop arguments based on Round 1"
   │  - Step 3: "Round 3: Final positions and OneSeek synthesis"
   │  - Step 4: "Voting: External models vote on best answer"
   │
   ▼

2. Plan Approved (human_feedback node)
   │
   │ User sees and approves the debate plan
   │
   ▼

3. Research Team Routes to Researcher
   │
   │ research_team checks enable_debate_mode flag
   │ Routes to researcher with Step 1
   │
   ▼

4. Researcher Receives Debate Tools
   │
   │ Because enable_debate_mode=True, researcher receives:
   │  ✓ start_debate_round
   │  ✓ query_model_in_round
   │  ✓ run_internal_analysis
   │  ✓ collect_debate_votes
   │  ✓ get_debate_summary
   │
   │ NOT normal research tools (web_search, crawl, etc.)
   │
   ▼

5. LLM Agent Sees Step 1 + Tools
   │
   │ LLM reads: "Round 1: All models provide initial arguments"
   │ LLM sees available debate tools with their schemas
   │ LLM understands it needs to:
   │  a) Start round 1
   │  b) Query each model
   │  c) Run analysis after each model
   │
   ▼

6. Tool Call Sequence for Round 1
   │
   │ LLM makes these tool calls:
   │
   │ 1. start_debate_round(round=1, query="User's question", locale="sv-SE")
   │    └─► Returns: "Round 1 started. Order: [gemini, oneseek, gpt, deepseek, grok]"
   │
   │ 2. query_model_in_round(model_id="gemini-2.5-flash", query="...", locale="sv-SE")
   │    └─► Returns: "Gemini response: [detailed argument about the topic]"
   │
   │ 3. run_internal_analysis(query="User's question")
   │    └─► Returns: "Internal analysis: Fact-checked via web search. Key points verified."
   │
   │ 4. query_model_in_round(model_id="oneseek-local", query="...", locale="sv-SE")
   │    └─► Returns: "OneSeek response: [argument incorporating previous context]"
   │
   │ 5. run_internal_analysis(query="User's question")
   │    └─► Returns: "Internal analysis complete."
   │
   │ ... (continues for all 5 models in randomized order)
   │
   │ Total: ~11 tool calls for Round 1 (1 start + 5×(query + analysis))
   │
   ▼

7. Step 1 Complete
   │
   │ LLM generates completion message
   │ researcher_node returns to research_team
   │ research_team sees Step 1 is complete, routes back with Step 2
   │
   ▼

8. Repeat for Round 2 (Step 2)
   │
   │ LLM starts fresh with Step 2 description
   │ Makes similar tool calls but for round 2
   │ Models receive Round 1 context via full_previous_round
   │ Order is re-randomized
   │
   ▼

9. Repeat for Round 3 (Step 3)
   │
   │ Round 3 executes similarly
   │ OneSeek creates synthesis when it's OneSeek's turn
   │ Uses all accumulated internal analyses
   │
   ▼

10. Voting Phase (Step 4)
    │
    │ LLM makes these tool calls:
    │
    │ 1. collect_debate_votes(query="User's question")
    │    └─► Returns: "Votes collected. GPT voted for OneSeek, 
    │                   Gemini voted for DeepSeek, ..."
    │
    │ 2. get_debate_summary()
    │    └─► Returns: "Debate complete. Winner: OneSeek with 3 votes.
    │                   Full debate history with all rounds included."
    │
    ▼

11. All Steps Complete
    │
    │ research_team sees all 4 steps done
    │ Routes to reporter
    │
    ▼

12. Reporter Generates Final Report
    │
    │ Reporter receives debate_results from state
    │ Synthesizes comprehensive debate report
    │ Shows all 3 rounds + voting results
    │
    ▼
   END
```

### Available Debate Tools

When `enable_debate_mode=True`, the researcher node receives these 5 specialized tools:

#### 1. start_debate_round

**Purpose**: Initialize a new debate round with randomized order

**Parameters**:
- `round` (int): Round number (1, 2, or 3)
- `query` (str): User's question
- `locale` (str): Language locale (e.g., "sv-SE")

**Returns**: Confirmation message with randomized model order

**Example**:
```python
start_debate_round(1, "Är kärnkraft nödvändig?", "sv-SE")
# Returns: "Round 1 started. Speaking order: [gemini, oneseek, gpt, deepseek, grok]"
```

#### 2. query_model_in_round

**Purpose**: Query a specific AI model with appropriate context

**Parameters**:
- `model_id` (str): Model identifier (e.g., "gpt-3.5-turbo", "gemini-2.5-flash")
- `query` (str): User's question
- `locale` (str): Language locale

**Returns**: The model's response to the query with full context from current round

**Example**:
```python
query_model_in_round("gemini-2.5-flash", "Är kärnkraft nödvändig?", "sv-SE")
# Returns: "Gemini response: Ja, kärnkraft är avgörande för... [detailed argument]"
```

**Context Provided to Model**:
- Round 1: Query only (first model) or query + chain_so_far (subsequent models)
- Round 2/3: Query + full_previous_round + chain_so_far

#### 3. run_internal_analysis

**Purpose**: Execute OneSeek's internal fact-checking and analysis

**Parameters**:
- `query` (str): User's question

**Returns**: Summary of internal analysis (web search, fact-checking, etc.)

**Example**:
```python
run_internal_analysis("Är kärnkraft nödvändig?")
# Returns: "Analysis: Verified nuclear energy statistics via web search.
#           Found supporting evidence for carbon reduction claims."
```

**What It Does**:
- Performs web search for fact verification
- Gathers additional context
- Identifies logical inconsistencies in previous responses
- Results stored internally, used by OneSeek when it responds

#### 4. collect_debate_votes

**Purpose**: Gather votes from external models on best Round 3 answer

**Parameters**:
- `query` (str): User's question

**Returns**: Voting results with vote counts per model

**Example**:
```python
collect_debate_votes("Är kärnkraft nödvändig?")
# Returns: "Voting complete. Votes:
#           - OneSeek: 3 votes (gpt, gemini, grok)
#           - DeepSeek: 1 vote (deepseek cannot vote for self, abstained)"
```

**Voting Rules**:
- Only external models vote (GPT, Gemini, DeepSeek, Grok)
- Self-voting prevented
- Models vote based on Round 3 responses only

#### 5. get_debate_summary

**Purpose**: Compile complete debate results with all rounds

**Parameters**: None

**Returns**: Comprehensive summary with all rounds, voting results, and winner

**Example**:
```python
get_debate_summary()
# Returns: {
#   "winner": "oneseek-local",
#   "vote_count": 3,
#   "round_1": [...],
#   "round_2": [...],
#   "round_3": [...],
#   "voting_details": {...}
# }
```

### Why Tools?

Using tools for the debate provides several advantages:

1. **Modularity**: Each debate action (start round, query model, analyze, vote) is isolated
2. **Testability**: Each tool can be tested independently
3. **Flexibility**: LLM decides when and how to call tools based on plan
4. **State Management**: Tools access shared DebateFlow state for context control
5. **Streaming**: Tool results can be streamed to frontend in real-time
6. **Reusability**: Same researcher node used for both research and debate modes

### Tool Selection Logic

The researcher node detects debate mode and swaps tool sets:

```python
# Simplified from researcher_node implementation

def researcher_node(state: State, config: RunnableConfig):
    if state.get("enable_debate_mode"):
        # Debate mode: use debate tools
        tools = [
            start_debate_round,
            query_model_in_round,
            run_internal_analysis,
            collect_debate_votes,
            get_debate_summary
        ]
        system_prompt = load_debate_prompt(state.locale)
    else:
        # Normal mode: use research tools
        tools = [
            web_search,
            crawl,
            retriever,
            calculator,
            # ... other research tools
        ]
        system_prompt = load_research_prompt(state.locale)
    
    # Create agent with selected tools
    agent = create_agent_with_tools(tools, system_prompt)
    
    # Execute current plan step
    result = await agent.execute(state.current_plan.steps[state.current_step])
    
    return Command(goto="research_team", update=result)
```

### LLM Decision Making

The LLM agent autonomously decides tool usage based on:

1. **Step Description**: "Round 1: All models provide initial arguments"
   - LLM understands it needs to start round 1, then query all models

2. **Tool Schemas**: Each tool has detailed description
   - LLM knows what each tool does and what parameters it needs

3. **System Prompt**: Debate-specific instructions
   - Explains the 3-round structure
   - Describes sequential chain-of-thought protocol
   - Instructs to run analysis after each model query

4. **Previous Tool Results**: Feedback loop
   - LLM sees results from previous tool calls
   - Decides next action based on those results

### Real-World Example

For the query "Är kärnkraft nödvändig för att nå klimatmålen?":

**Step 1 Execution ("Round 1: All models provide initial arguments")**:

```
LLM reads step → Decides to start round 1

Tool Call 1:
>>> start_debate_round(1, "Är kärnkraft nödvändig för att nå klimatmålen?", "sv-SE")
<<< "Round 1 started. Order: [deepseek, grok, gemini, oneseek, gpt]"

LLM sees order → Queries first model (deepseek)

Tool Call 2:
>>> query_model_in_round("deepseek-chat", "Är kärnkraft nödvändig...", "sv-SE")
<<< "DeepSeek: Kärnkraft är en viktig del av energimixen... [200 tokens]"

LLM sees response → Runs internal analysis

Tool Call 3:
>>> run_internal_analysis("Är kärnkraft nödvändig...")
<<< "Analysis: Verified claim about carbon emissions. Found IEA data supporting..."

LLM continues → Queries next model (grok)

Tool Call 4:
>>> query_model_in_round("grok-4-fast-reasoning", "Är kärnkraft...", "sv-SE")
<<< "Grok: Kärnkraft har både för- och nackdelar... [250 tokens]"

... (continues for all 5 models)

Total: 11 tool calls (1 start + 5 models × 2 actions each)

LLM finishes → Returns completion message
```

This pattern repeats for Steps 2 (Round 2), 3 (Round 3), and 4 (Voting).

### Tool Exposure Flow: Planner vs Researcher 🔍

**CRITICAL ARCHITECTURAL UNDERSTANDING**: Tools are exposed ONLY in the researcher node, NOT in the planner node!

#### Where Tools Are Visible

```
┌──────────────────────────────────────────────────────────────────┐
│              Tool Visibility Across Nodes                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  coordinator node:     🚫 NO TOOLS                              │
│    └─ Routes based on mode flags                                │
│                                                                  │
│  debate_planner node:  🚫 NO TOOLS VISIBLE                      │
│    └─ Creates plan from pattern knowledge                       │
│    └─ Knows: "Debate = 3 rounds + 5 models + voting"            │
│    └─ Does NOT see actual tool signatures or parameters         │
│    └─ Uses debate-specific prompt with structure knowledge      │
│                                                                  │
│  human_feedback node:  🚫 NO TOOLS                              │
│    └─ Reviews and approves plan                                 │
│                                                                  │
│  research_team node:   🚫 NO TOOLS                              │
│    └─ Routing logic only                                        │
│                                                                  │
│  researcher node:      ✅ TOOLS EXPOSED HERE!                   │
│    └─ Receives approved plan from debate_planner                │
│    └─ Dynamically loads tools based on enable_debate_mode flag  │
│    └─ LLM sees tools + step description → makes tool calls      │
│    └─ Tool swapping happens here (debate vs research tools)     │
│                                                                  │
│  reporter node:        🚫 NO TOOLS                              │
│    └─ Synthesizes results                                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### How Plans Are Created Without Tools

**The Key Insight**: The debate_planner doesn't need to see tools! It creates a strategic plan based on:

1. **Debate-specific prompt**: System prompt teaches the debate structure
2. **Pattern knowledge**: "Debates have 3 rounds, models answer sequentially, then vote"
3. **High-level steps**: Creates step descriptions like "Round 1: All models argue"

**Example Plan Creation**:

```python
# debate_planner_node (NO TOOLS VISIBLE)
# Just knows the debate pattern from its prompt

def debate_planner_node(state):
    # LLM reads debate-specific prompt:
    # "Create a plan for multi-model debate.
    #  Structure: 3 rounds + voting.
    #  Each round: models speak in random order."
    
    # Creates strategic plan:
    plan = Plan(
        topic=state.query,
        steps=[
            Step(1, "Round 1: Initial arguments from all 5 models"),
            Step(2, "Round 2: Development based on Round 1"),
            Step(3, "Round 3: Synthesis and final positions"),
            Step(4, "Voting: External models vote on best answer")
        ]
    )
    
    return Command(goto="human_feedback", update={"plan": plan})

# researcher_node (TOOLS VISIBLE HERE)
# Executes the plan with actual debate tools

def researcher_node(state):
    # Tool swapping based on mode:
    if state.enable_debate_mode:
        tools = get_debate_tools()  # ← Tools loaded HERE
    else:
        tools = get_research_tools()
    
    # LLM sees Step 1: "Round 1: Initial arguments from all 5 models"
    # LLM also sees available tools with schemas
    # LLM decides: "I need start_debate_round, then query_model_in_round 5 times"
    
    agent = create_agent_with_tools(tools)
    result = await agent.execute(state.current_step)
    
    return Command(goto="research_team", update=result)
```

**Why This Separation?**

1. **Clean separation of concerns**: Strategy (planner) vs. execution (researcher)
2. **Flexibility**: Same plan can use different tool implementations
3. **Simplicity**: Planner focuses on "what to do", researcher on "how to do it"
4. **Maintainability**: Tool changes don't require planner changes

### Parallelism and Performance Optimization ⚡

**IMPORTANT PERFORMANCE CONSIDERATION**: The system supports **up to 250 parallel model calls**!

#### Current Limitation in `run_internal_analysis`

The current `run_internal_analysis` tool bundles multiple operations into ONE sequential call:

```python
# CURRENT (Suboptimal):
@tool
async def run_internal_analysis(query: str) -> str:
    # Does EVERYTHING in sequence within one tool call:
    debate_flow = get_debate_flow()
    
    # 1. Web search (5 seconds)
    search_results = await search_tool.invoke(query)
    
    # 2. Claim detection (potential, not implemented)
    # claims = await claim_detector.detect(responses)
    
    # 3. Fact checking (potential, not implemented)
    # facts = await fact_checker.verify(claims)
    
    # 4. Logical consistency (potential, not implemented)
    # consistency = await consistency_checker.check(responses)
    
    return "Analysis complete"  # 1 tool call = 1 slot used
```

**Problem**: This uses only **1 out of 250 parallel slots**!

#### Optimized Approach: Separate Tools for Parallel Execution

**RECOMMENDED ARCHITECTURE**:

Break `run_internal_analysis` into multiple specialized tools that LLM can call in parallel:

```python
# OPTIMIZED (Better parallelism):

@tool
async def web_search_query(query: str) -> str:
    """Search web for claims verification."""
    return await search_tool.invoke(query)

@tool
async def detect_claims(text: str) -> List[str]:
    """Meta-agent: Extract factual claims from text."""
    return await claim_detector_agent.detect(text)

@tool
async def verify_fact(claim: str) -> dict:
    """Meta-agent: Verify a specific factual claim."""
    return await fact_checker_agent.verify(claim)

@tool
async def check_logical_consistency(argument: str) -> dict:
    """Meta-agent: Analyze logical structure."""
    return await logic_checker_agent.check(argument)

@tool
async def find_counter_arguments(position: str) -> List[str]:
    """Find counter-arguments to a position."""
    return await counter_arg_finder.find(position)

@tool
async def validate_sources(sources: List[str]) -> dict:
    """Meta-agent: Validate credibility of sources."""
    return await source_validator.validate(sources)
```

**LLM Can Now Make Parallel Calls**:

```python
# Instead of 1 sequential call using 1 slot:
run_internal_analysis("query")  # 1 slot, sequential inside

# LLM makes 6 parallel calls using 6 slots simultaneously:
[
    web_search_query("nuclear power climate"),      # Slot 1 ⎤
    detect_claims(model_response),                  # Slot 2 ⎥
    verify_fact("Nuclear reduces CO2"),             # Slot 3 ⎬ Parallel!
    check_logical_consistency(argument),            # Slot 4 ⎥
    find_counter_arguments("Pro-nuclear stance"),   # Slot 5 ⎥
    validate_sources(["IEA", "IPCC"])              # Slot 6 ⎦
]

# All 6 execute in parallel → Results come back together
# Total time = slowest single call, NOT sum of all calls
```

#### Performance Benefit Example

**Sequential (current)**:
- Web search: 5s
- Claim detection: 3s
- Fact checking: 4s
- Logic check: 2s
- **Total: 14 seconds** ⏱️

**Parallel (optimized)**:
- All run simultaneously
- **Total: 5 seconds** (longest single operation) ⚡
- **~3x faster!**

#### Recommended Debate Tools Architecture

```
Current (5 tools):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ start_debate_round          - Initialize round
✅ query_model_in_round         - Query AI model
⚠️  run_internal_analysis       - Bundled analysis (sequential)
✅ collect_debate_votes         - Gather votes
✅ get_debate_summary           - Compile results

Optimized (10+ tools):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ start_debate_round           - Initialize round
✅ query_model_in_round          - Query AI model

Analysis Tools (can run in parallel):
✅ web_search_query             - Search web
✅ detect_claims                - Meta-agent: Extract claims
✅ verify_fact                  - Meta-agent: Check facts
✅ check_logical_consistency    - Meta-agent: Logic analysis
✅ find_counter_arguments       - Find opposing views
✅ validate_sources             - Meta-agent: Source credibility

Completion Tools:
✅ collect_debate_votes         - Gather votes
✅ get_debate_summary           - Compile results
```

#### Implementation Benefit

With separate tools, after each model responds in debate, LLM can:

```
Model 1 responds →
  LLM makes 5 PARALLEL analysis calls:
  ├─ web_search_query("verify claim X")          ⎤
  ├─ detect_claims(model1_response)              ⎥
  ├─ verify_fact("claim from response")          ⎬ All parallel!
  ├─ check_logical_consistency(argument)         ⎥
  └─ find_counter_arguments(model1_position)     ⎦
  
  Results arrive → Model 2 can respond with enriched context
```

This maximizes the system's 250 parallel call capacity and dramatically improves performance!

### Migration Path

To implement optimized parallelism:

1. **Keep current `run_internal_analysis` for compatibility**
2. **Add new specialized tools** (web_search_query, detect_claims, etc.)
3. **Update debate prompt** to encourage parallel tool usage
4. **Meta-agents** (claim_detector, fact_checker, etc.) become **individual tools**
5. **Monitor performance** improvement (should see ~2-3x speedup)

- `human_feedback` → `research_team`
- `research_team` → `reporter`
- `reporter` → END

## Examples

### Example Research Plan

For query: "Is nuclear power necessary to achieve climate goals?"

Debate planner generates:

```json
{
  "locale": "en-US",
  "has_enough_context": false,
  "thought": "Need to research arguments for and against nuclear power...",
  "title": "Nuclear Power and Climate Goals Debate",
  "steps": [
    {
      "need_search": true,
      "title": "Research pro-nuclear arguments",
      "description": "Gather evidence supporting nuclear power for climate...",
      "step_type": "research"
    },
    {
      "need_search": true,
      "title": "Research anti-nuclear arguments",
      "description": "Gather evidence against nuclear power...",
      "step_type": "research"
    },
    {
      "need_search": true,
      "title": "Research alternative perspectives",
      "description": "Examine renewable energy alternatives...",
      "step_type": "research"
    }
  ]
}
```

### Example Output

The final report includes:

- **Arguments FOR nuclear power**
  - Low carbon emissions
  - High energy density
  - Proven technology
  - Evidence and expert opinions

- **Arguments AGAINST nuclear power**
  - Safety concerns
  - Waste disposal challenges
  - High costs
  - Evidence and expert opinions

- **Alternative perspectives**
  - Renewable energy solutions
  - Energy efficiency approaches
  - Hybrid approaches

- **Synthesis**
  - Areas of agreement
  - Key points of contention
  - Contextual factors
  - Balanced conclusion

## Current Implementation vs. Future Vision

### What's Implemented Now ✅

The current debate mode implementation focuses on **multi-perspective research planning**:

- **Debate Planner**: Specialized planner that creates research plans emphasizing multiple viewpoints
- **Balanced Research**: Research team gathers arguments from different perspectives (pro/con)
- **Synthesized Analysis**: Reporter creates a comprehensive report presenting all viewpoints
- **Standard Workflow**: Reuses existing research_team → reporter infrastructure

This provides balanced, multi-perspective analysis through intelligent research planning and synthesis.

### Original Vision (Not Yet Implemented)

The original PR concept described a more ambitious system:

1. **Real-time multi-model debates**: External AI models (GPT, Gemini, DeepSeek, Grok) debating with each other in sequential rounds
2. **Sequential chain-of-thought**: Each model responding to previous models' arguments
3. **Voting mechanisms**: External models voting on best arguments after debate rounds
4. **OneSeek participation**: OneSeek as an equal debate participant alongside external models

**Why the simpler approach?**
- The multi-model debate system proved complex to orchestrate reliably
- LLM agents had difficulty following multi-round debate protocols
- The simpler planner-based approach provides similar value (balanced perspectives) with better reliability
- Reuses proven research infrastructure rather than creating new debate-specific code

### Future Enhancements

The debate planner architecture enables future extensions:

1. **Enhanced perspective analysis**: Deeper analysis of conflicting viewpoints
2. **Stakeholder mapping**: Identify and research perspectives from different stakeholder groups
3. **Argument strength scoring**: Rate the strength of evidence for each perspective
4. **Interactive debates**: User-guided debate flow and dynamic re-planning
5. **Comparative analysis**: Side-by-side comparison of argument quality

## Troubleshooting

### Common Issues

**Issue**: Debate mode not activating
- **Check**: Frontend sends `enable_debate_mode: true`
- **Check**: Coordinator routes to `debate_planner`
- **Logs**: Look for "Debate mode enabled, routing to debate_planner"

**Issue**: Unbalanced research plan
- **Check**: Debate planner prompt properly loaded
- **Check**: Locale matches available prompt (en-US or sv-SE)
- **Solution**: Review generated plan in logs, adjust prompts if needed

**Issue**: Research not finding opposing views
- **Check**: Web search is enabled
- **Check**: Search queries in plan are balanced
- **Solution**: Improve debate_planner prompt specificity

## Files

### Backend

- `backend/deer_flow/graph/nodes.py`: debate_planner_node implementation
- `backend/deer_flow/graph/builder.py`: Graph structure with debate_planner
- `backend/deer_flow/prompts/debate_planner.md`: English prompt
- `backend/deer_flow/prompts/debate_planner.sv_SE.md`: Swedish prompt
- `backend/deer_flow/config/agents.py`: Agent configuration

### Frontend

- `web/src/app/chat/components/input-box.tsx`: Debate button
- `web/src/components/deer-flow/icons/debate.tsx`: Debate icon
- `web/src/core/store/settings-store.ts`: State management
- `web/src/core/api/chat.ts`: API integration
- `web/messages/en.json`: English translations
- `web/messages/sv.json`: Swedish translations

## Contributing

When modifying debate mode:

1. **Maintain code reuse**: Don't duplicate research_team logic
2. **Update both prompts**: Keep English and Swedish in sync
3. **Test routing**: Verify coordinator routes correctly
4. **Test workflow**: Ensure full flow works end-to-end
5. **Update docs**: Keep this documentation current

## License

Copyright (c) 2026 Oneseek

