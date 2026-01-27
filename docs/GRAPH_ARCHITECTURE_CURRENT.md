# OneSeek Graph Architecture

This document describes the current LangGraph workflow architecture in OneSeek.

## Current Graph Structure (with Debate Mode)

```
┌─────────┐
│  START  │
└────┬────┘
     │
     ▼
┌────────────────┐
│  coordinator   │ ◄──────────────────┐
└────────┬───────┘                    │
         │                            │
         │ (routes based on mode)    │
         │                            │
    ┌────┴─────────────────────────┬────────────────┬──────────────────┐
    │                              │                │                  │
    │ enable_debate_mode=true      │ enable_ai_     │ normal mode      │
    │                              │ comparison=    │                  │
    │                              │ true           │                  │
    ▼                              ▼                ▼                  ▼
┌──────────────────┐         ┌─────────┐     ┌─────────────────┐
│ debate_planner   │         │ planner │     │ background_     │
└────────┬─────────┘         └────┬────┘     │ investigator    │
         │                        │           └────────┬────────┘
         │                        │                    │
         │                   ┌────┴───┐               │
         │                   │        │               │
         │              ┌────┘        └────┐          │
         │              │                  │          │
         │         has_enough_       enable_ai_       │
         │         context=true      comparison=      │
         │                           true             │
         │              │                  │          │
         │              ▼                  ▼          ▼
         │         ┌──────────┐      ┌──────────────────┐   ┌─────────┐
         └────────►│  human_  │      │  ai_comparison   │   │ planner │
                   │ feedback │      └────────┬─────────┘   └────┬────┘
                   └────┬─────┘               │                  │
                        │                     │                  │
                        │                     │                  │
                        ▼                     │                  │
                   ┌──────────────┐          │                  │
                   │ research_    │◄─────────┘                  │
                   │ team         │◄────────────────────────────┘
                   └──────┬───────┘
                          │
                          │ (conditional routing)
                     ┌────┴────┬──────────┬──────────┐
                     │         │          │          │
                     ▼         ▼          ▼          ▼
               ┌─────────┐ ┌─────────┐ ┌────────┐ ┌────────┐
               │planner  │ │researcher│ │analyst │ │ coder  │
               └────┬────┘ └────┬─────┘ └────┬───┘ └───┬────┘
                    │           │            │         │
                    │           │            │         │
                    └───────────┴────────────┴─────────┘
                                │
                                │ (all routes back to research_team)
                                │ (when all steps complete)
                                │
                                ▼
                          ┌──────────┐
                          │ reporter │◄──────────┐
                          └────┬─────┘           │
                               │                 │
                               │                 │ (ai_comparison routes
                               │                 │  directly to reporter)
                               ▼                 │
                            ┌─────┐         ┌────────────────┐
                            │ END │         │ ai_comparison  │
                            └─────┘         └────────────────┘
```

## Node Descriptions

### coordinator
**Purpose**: Entry point for all user queries  
**Responsibilities**:
- Analyze user query intent
- Determine routing mode (debate, ai_comparison, normal research)
- Handle clarification loops if enabled
- Extract research topic
- Route to appropriate planner or specialized node

**Routes to**:
- `debate_planner` (when `enable_debate_mode=True`)
- `planner` (when `enable_ai_comparison=True` or normal mode)
- `background_investigator` (when background investigation enabled and normal mode)
- `coordinator` (during clarification loops)
- `__end__` (for direct responses like greetings)

### debate_planner
**Purpose**: Create multi-perspective research plans  
**Responsibilities**:
- Use debate-specific prompts (English/Swedish)
- Generate balanced research plan with pro/con arguments
- Focus on diverse viewpoints and evidence-based analysis
- Route to standard research workflow

**Routes to**:
- `human_feedback` (standard flow)
- `reporter` (if has enough context)

### planner
**Purpose**: Create standard research plans  
**Responsibilities**:
- Use research-specific prompts
- Generate comprehensive research plan
- Validate and fix plan for web search requirements
- Handle plan iterations

**Routes to**:
- `human_feedback` (for plan approval)
- `ai_comparison` (when `enable_ai_comparison=True`)
- `reporter` (if has enough context or max iterations reached)
- `__end__` (on JSON decode errors)

### background_investigator
**Purpose**: Perform preliminary research before planning  
**Responsibilities**:
- Gather background context on user query
- Provide context to planner for better plan generation

**Routes to**:
- `planner` (always)

### human_feedback
**Purpose**: Get user approval for research plan  
**Responsibilities**:
- Present plan to user
- Handle plan edits or approvals
- Trigger research execution

**Routes to**:
- `research_team` (when plan approved)
- `planner` (for plan edits)

### research_team
**Purpose**: Route research tasks to specialized agents  
**Responsibilities**:
- Check which research steps are incomplete
- Route to appropriate specialist (researcher, analyst, coder)
- Track progress through research plan

**Routes to**:
- `researcher` (for search-based research steps)
- `analyst` (for analysis steps)
- `coder` (for coding steps)
- `planner` (when all steps complete)

### researcher
**Purpose**: Execute web search and research tasks  
**Responsibilities**:
- Perform web searches
- Gather information from sources
- Document findings
- **Tool swapping based on mode**: Uses different tool sets depending on debate mode

**Routes to**: `research_team` (always)

**Tool Sets**:
- **Normal mode**: `web_search`, `crawl`, `retriever`, and other research tools
- **Debate mode**: `start_debate_round`, `query_model_in_round`, `run_internal_analysis`, `collect_debate_votes`, `get_debate_summary`

### analyst
**Purpose**: Perform analysis on gathered data  
**Responsibilities**:
- Analyze research findings
- Identify patterns and insights
- Synthesize information

**Routes to**: `research_team` (always)

### coder
**Purpose**: Generate or analyze code  
**Responsibilities**:
- Write code solutions
- Analyze code from sources
- Generate technical examples

**Routes to**: `research_team` (always)

### ai_comparison
**Purpose**: Compare responses from multiple AI models  
**Responsibilities**:
- Query multiple external AI models sequentially
- Collect responses
- Synthesize best answer
- Execute all tools internally

**Routes to**:
- `reporter` (always, directly)

### reporter
**Purpose**: Generate final report  
**Responsibilities**:
- Synthesize all gathered information
- Format final report based on report style
- Handle special cases (AI comparison, debate results)
- Generate citations

**Routes to**: `END` (always)

## Tool Usage in the Graph

### Where Tools Are Exposed

Tools are made available to the LLM agent at specific nodes in the graph. The primary node that uses tools is the **researcher** node, though the **ai_comparison** node also uses tools internally.

### Tool Execution Flow

```
┌──────────────────────────────────────────────────────────────┐
│                     Tool Execution Flow                      │
└──────────────────────────────────────────────────────────────┘

1. Plan Created (planner/debate_planner node)
   │
   │ Plan contains steps with descriptions
   │ Example: "Round 1: Query all 5 AI models"
   │
   ▼

2. Plan Approved (human_feedback node)
   │
   │ User approves the plan
   │
   ▼

3. Research Team Routes to Specialist
   │
   │ research_team checks next incomplete step
   │ Routes to appropriate specialist (usually researcher)
   │
   ▼

4. Researcher Node Receives Step
   │
   │ Researcher receives current step description
   │ Checks if debate mode is enabled in state
   │
   ├─► Normal Mode:
   │   └─► Tools available: web_search, crawl, retriever, etc.
   │
   └─► Debate Mode:
       └─► Tools available: start_debate_round, query_model_in_round,
           run_internal_analysis, collect_debate_votes, get_debate_summary
   │
   ▼

5. LLM Agent Sees Tools (researcher_node)
   │
   │ LLM is given:
   │  - Step description from plan
   │  - Available tools (based on mode)
   │  - System prompt explaining how to use tools
   │  - Current context and state
   │
   │ LLM reads the step description and decides which tools to call
   │
   ▼

6. LLM Makes Tool Calls
   │
   │ LLM generates tool call requests (function calls)
   │ Example in debate mode:
   │   1. Call start_debate_round(round=1, query="...", locale="sv-SE")
   │   2. Call query_model_in_round(model="gpt-3.5-turbo", ...)
   │   3. Call run_internal_analysis(query="...")
   │   4. Call query_model_in_round(model="gemini-2.5-flash", ...)
   │   ... (continues for all models in round)
   │
   ▼

7. Tools Execute Sequentially
   │
   │ Each tool call is executed by the framework
   │ Tool results are returned to the LLM
   │ LLM sees the result and decides next tool call
   │
   │ This continues in a loop:
   │   LLM → Tool Call → Tool Execution → Result → LLM → ...
   │
   │ Until LLM decides the step is complete
   │
   ▼

8. Step Completion
   │
   │ LLM generates final response indicating step completion
   │ Result is stored in state
   │ researcher_node returns Command to route back to research_team
   │
   ▼

9. Next Step or Completion
   │
   │ research_team checks if more steps exist
   │  - If yes: route to specialist for next step (repeat from step 3)
   │  - If no: route to planner/reporter to finalize
   │
   ▼

10. Report Generation (reporter node)
    │
    │ Reporter synthesizes all step results
    │ Generates final formatted report
    │
    ▼
   END
```

### Tool Swapping Mechanism

The researcher node dynamically swaps tool sets based on the current mode:

```python
# Simplified example from researcher_node

def researcher_node(state: State, config: RunnableConfig):
    # Determine which tools to provide based on mode
    if state.get("enable_debate_mode"):
        # Debate mode: provide debate tools
        tools = get_debate_tools()
        # Tools: start_debate_round, query_model_in_round,
        #        run_internal_analysis, collect_debate_votes,
        #        get_debate_summary
    else:
        # Normal mode: provide research tools
        tools = get_research_tools()
        # Tools: web_search, crawl, retriever, calculator, etc.
    
    # Create agent with appropriate tools
    agent = create_agent_with_tools(tools)
    
    # Execute agent with current step
    result = await agent.execute(state.current_step)
    
    return Command(goto="research_team", update=result)
```

### Tool Decision Making

The LLM agent decides which tools to call based on:

1. **Step Description**: The plan step provides context
   - Example: "Round 1: Query all AI models for initial arguments"
   
2. **System Prompt**: Instructions on how to use each tool
   - Explains what each tool does
   - Provides parameter descriptions
   - Suggests sequences (e.g., "call start_debate_round before query_model_in_round")

3. **Tool Schemas**: Function signatures with descriptions
   - Tool name, parameters, return types
   - Embedded in the LLM's context

4. **Previous Results**: Tool outputs from earlier calls
   - LLM sees results and decides next action
   - Enables sequential chain-of-thought execution

### Example: Debate Mode Tool Sequence

When executing a debate plan step "Round 1", the LLM sees these tools and typically calls them in this sequence:

```
Step: "Round 1: All models provide initial arguments"

Available Tools:
- start_debate_round(round, query, locale)
- query_model_in_round(model_id, query, locale)
- run_internal_analysis(query)
- collect_debate_votes(query)
- get_debate_summary()

LLM Reasoning & Tool Calls:
1. "I need to start round 1"
   → Call: start_debate_round(1, "User's question", "sv-SE")
   ← Result: "Round 1 started. Order: [gemini, oneseek, gpt, deepseek, grok]"

2. "First model is gemini, query it"
   → Call: query_model_in_round("gemini-2.5-flash", "User's question", "sv-SE")
   ← Result: "Gemini's response: [detailed argument]"

3. "Run internal analysis after gemini's response"
   → Call: run_internal_analysis("User's question")
   ← Result: "Analysis complete. Key facts verified via web search."

4. "Next model is oneseek, query it"
   → Call: query_model_in_round("oneseek-local", "User's question", "sv-SE")
   ← Result: "OneSeek's response: [detailed argument with synthesis]"

5. "Run internal analysis after oneseek's response"
   → Call: run_internal_analysis("User's question")
   ← Result: "Analysis complete."

... (continues for all 5 models)

10. "All models have responded for round 1. Step complete."
    → LLM generates completion message
    ← researcher_node returns to research_team
```

### Tool Availability by Mode

| Mode | Node | Tools Available |
|------|------|-----------------|
| Normal Research | researcher | web_search, crawl, retriever, calculator, python_repl, etc. |
| Debate Mode | researcher | start_debate_round, query_model_in_round, run_internal_analysis, collect_debate_votes, get_debate_summary |
| AI Comparison | ai_comparison | query_external_model, synthesize_responses (internal, not exposed to LLM) |

### Key Insights

1. **Tools are node-specific**: Only certain nodes have access to tools (primarily researcher)
2. **Dynamic tool sets**: The same node (researcher) uses different tools based on mode
3. **LLM autonomy**: The LLM agent decides when and how to call tools based on the plan step
4. **Sequential execution**: Tools are called one at a time, results inform next decisions
5. **State-driven**: Tool selection is driven by state flags (enable_debate_mode, etc.)
6. **Plan-driven**: The plan's step descriptions guide the LLM's tool usage strategy

### Critical Architectural Clarification: Tool Exposure Flow 🔍

**IMPORTANT**: Tools are exposed ONLY in the **researcher node**, NOT in planner nodes!

#### Complete Tool Visibility Map

```
┌─────────────────────────────────────────────────────────────────┐
│           Tool Visibility Across All Nodes                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  START node:           🚫 NO TOOLS                             │
│                                                                 │
│  coordinator node:     🚫 NO TOOLS                             │
│    Role: Routing based on mode flags                           │
│    Decision: Check enable_debate_mode, enable_ai_comparison    │
│                                                                 │
│  planner node:         🚫 NO TOOLS (Research Planning)         │
│    Role: Create research plan                                  │
│    Method: Uses LLM with planning prompt (NO tool access)      │
│    Creates: Plan object with steps                             │
│    Knowledge: Understands research patterns from prompt        │
│                                                                 │
│  debate_planner node:  🚫 NO TOOLS (Debate Planning)           │
│    Role: Create debate plan                                    │
│    Method: Uses LLM with debate-specific prompt (NO tools)     │
│    Creates: Plan with 4 steps (Round 1, 2, 3, Voting)          │
│    Knowledge: Understands debate structure from prompt         │
│      - "Debates have 3 rounds"                                 │
│      - "Models speak in random order"                          │
│      - "Voting happens after round 3"                          │
│    Does NOT need: Actual tool signatures/parameters            │
│                                                                 │
│  human_feedback node:  🚫 NO TOOLS                             │
│    Role: Plan review and approval                              │
│    Interaction: User approves/rejects plan                     │
│                                                                 │
│  research_team node:   🚫 NO TOOLS (Routing Logic)             │
│    Role: Route to appropriate specialist                       │
│    Method: Check current_step, route to researcher/etc.        │
│                                                                 │
│  background_investigator: 🔧 TOOLS (Background Research)       │
│    Tools: web_search, crawler, summarizer                      │
│    Role: Quick context gathering before main research          │
│                                                                 │
│  researcher node:      ✅ TOOLS EXPOSED HERE!                  │
│    Role: Execute plan steps with tools                         │
│    Method: Tool swapping based on state.enable_debate_mode     │
│                                                                 │
│    IF enable_debate_mode = True:                               │
│      Tools = [start_debate_round, query_model_in_round,        │
│               run_internal_analysis, collect_debate_votes,     │
│               get_debate_summary]                              │
│                                                                 │
│    ELSE (normal research):                                     │
│      Tools = [web_search, crawl, retriever, calculator,        │
│               python_repl, ...]                                │
│                                                                 │
│    LLM sees: Current step description + Available tools        │
│    LLM decides: Which tools to call and in what order          │
│                                                                 │
│  ai_comparison node:   🔧 TOOLS (Internal, Not LLM-Exposed)    │
│    Tools: query_external_model (used internally, not by LLM)   │
│    Role: Compare AI model responses                            │
│    Method: Hardcoded tool sequence (not LLM-driven)            │
│                                                                 │
│  reporter node:        🚫 NO TOOLS                             │
│    Role: Synthesize results into final report                  │
│    Method: Format results from state                           │
│                                                                 │
│  END node:             🚫 NO TOOLS                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Why Planners Don't Need Tools

**Key Architectural Principle**: Separation of strategy (planning) from tactics (execution).

**Planner Node (debate_planner example)**:
```python
def debate_planner_node(state: State) -> Command:
    """
    Creates debate plan WITHOUT seeing tools.
    Uses debate-specific system prompt that teaches structure.
    """
    
    # System prompt contains knowledge:
    system_prompt = """
    You are creating a plan for a multi-model debate.
    
    Structure:
    - 3 rounds of sequential model responses
    - Each round: randomize order, all 5 models respond
    - After each model: internal analysis for fact-checking
    - After round 3: external models vote on best answer
    - Finally: compile summary
    
    Create a plan with 4 steps following this structure.
    """
    
    # LLM creates plan based on PATTERN KNOWLEDGE, not tool access
    llm = get_llm("basic")  # No tools attached!
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Create debate plan for: {state.query}")
    ])
    
    plan = parse_plan(response)  # Extracts Plan object
    
    # Plan contains high-level steps:
    # Step 1: "Round 1: All models provide initial arguments"
    # Step 2: "Round 2: Models develop arguments"
    # Step 3: "Round 3: Final positions and synthesis"
    # Step 4: "Voting and summary"
    
    return Command(goto="human_feedback", update={"plan": plan})
```

**Researcher Node (execution with tools)**:
```python
def researcher_node(state: State) -> Command:
    """
    Executes plan WITH tools.
    Tools are loaded based on mode.
    """
    
    # Tool swapping based on mode
    if state.enable_debate_mode:
        tools = get_debate_tools()  # ← Tools loaded HERE
    else:
        tools = get_research_tools()
    
    # LLM with tools
    llm = get_llm("basic")
    agent = create_agent(llm, tools)  # Tools bound to agent
    
    # Execute current step
    current_step = state.plan.steps[state.current_step_index]
    
    # LLM sees:
    # 1. Step description: "Round 1: All models provide initial arguments"
    # 2. Available tools with full schemas
    # 3. System prompt explaining how to use tools
    
    result = agent.invoke({
        "step": current_step,
        "history": state.messages
    })
    
    # LLM made tool calls: start_debate_round, query_model_in_round, etc.
    
    return Command(goto="research_team", update={"step_result": result})
```

**Benefits of This Separation**:

1. **Simplicity**: Planners focus on "what to do", not "how to do it"
2. **Flexibility**: Same plan can be executed with different tool implementations
3. **Testability**: Can test planning and execution independently
4. **Maintainability**: Tool changes don't affect planner logic
5. **Clarity**: Clear boundary between strategy and tactics

### Performance Optimization: Parallelism and Tool Design ⚡

**CRITICAL PERFORMANCE INSIGHT**: The system supports **up to 250 parallel LLM calls**!

#### Current Bottleneck: Bundled Tools

Many operations are currently bundled into single tools, limiting parallelism:

```python
# CURRENT (Suboptimal for parallelism):
@tool
async def run_internal_analysis(query: str) -> str:
    """
    Performs multiple analyses sequentially within one tool call.
    Uses only 1 out of 250 parallel slots!
    """
    # 1. Web search (5 seconds)
    search_results = await web_search(query)
    
    # 2. Claim detection (3 seconds) - Meta-agent
    # claims = await claim_detector_agent.detect(responses)
    
    # 3. Fact verification (4 seconds) - Meta-agent
    # verified = await fact_checker_agent.verify(claims)
    
    # 4. Logical consistency (2 seconds) - Meta-agent
    # consistency = await logic_checker_agent.check(argument)
    
    # Total: 14 seconds sequentially
    # Uses: 1 parallel slot
    
    return "Analysis complete with all checks"
```

**Problem**: All operations run sequentially inside ONE tool call!

#### Optimized Approach: Granular Tools for Parallel Execution

**RECOMMENDED**: Break bundled tools into fine-grained tools that LLM can call in parallel:

```python
# OPTIMIZED (Better parallelism):

@tool
async def web_search_query(query: str, max_results: int = 5) -> dict:
    """Search the web for information."""
    return await web_search_tool.invoke(query, max_results)

@tool
async def detect_claims_in_text(text: str) -> List[str]:
    """
    Meta-agent: Extract factual claims from text.
    Uses specialized claim detection model.
    """
    return await claim_detector_agent.detect(text)

@tool
async def verify_factual_claim(claim: str) -> dict:
    """
    Meta-agent: Verify a specific factual claim against sources.
    Returns: {verified: bool, confidence: float, sources: List[str]}
    """
    return await fact_checker_agent.verify(claim)

@tool
async def check_logical_consistency(argument: str) -> dict:
    """
    Meta-agent: Analyze logical structure and detect fallacies.
    Returns: {is_consistent: bool, fallacies: List[str], score: float}
    """
    return await logic_checker_agent.check(argument)

@tool
async def find_counter_arguments(position: str, topic: str) -> List[str]:
    """Find counter-arguments to a given position."""
    return await counter_argument_finder.find(position, topic)

@tool
async def validate_information_sources(sources: List[str]) -> dict:
    """
    Meta-agent: Validate credibility and reliability of sources.
    Returns: {source: str, credibility_score: float, reputation: str}
    """
    return await source_validator.validate(sources)

@tool
async def extract_key_entities(text: str) -> List[dict]:
    """
    Meta-agent: Extract named entities and their relationships.
    Returns entities with types and confidence scores.
    """
    return await entity_extractor_agent.extract(text)
```

#### Parallel Execution Example

With granular tools, the LLM can make parallel calls:

```python
# After Model 1 responds in debate:
model1_response = "Nuclear power produces 55% less CO2 than coal..."

# LLM makes 6 PARALLEL tool calls:
parallel_calls = [
    web_search_query("nuclear power CO2 emissions vs coal"),     # Slot 1  ⎤
    detect_claims_in_text(model1_response),                      # Slot 2  ⎥
    verify_factual_claim("Nuclear power 55% less CO2"),          # Slot 3  ⎥
    check_logical_consistency(model1_response),                  # Slot 4  ⎬ Parallel!
    find_counter_arguments("Pro-nuclear stance", topic),         # Slot 5  ⎥
    validate_information_sources(["IEA", "IPCC", "WNA"]),       # Slot 6  ⎦
]

# All execute simultaneously
# Total time = max(call_times) ≈ 5 seconds
# NOT sum(call_times) ≈ 21 seconds
```

**Performance Gain**: ~4x faster! (5s vs 21s)

#### Meta-Agents as Individual Tools

**Current Confusion**: Are meta-agents tools or not?

**Answer**: Meta-agents SHOULD be exposed as individual tools for maximum parallelism!

**Meta-Agent Tool Pattern**:

```python
@tool
async def claim_detector_meta_agent(text: str) -> List[str]:
    """
    Specialized meta-agent for claim detection.
    Uses fine-tuned model for extracting factual claims.
    
    This is a TOOL that wraps a meta-agent.
    """
    meta_agent = get_meta_agent("claim_detector")
    claims = await meta_agent.process(text)
    return claims

# Benefits:
# 1. Can be called in parallel with other tools
# 2. Encapsulates complex meta-agent logic
# 3. LLM sees it as a regular tool in the toolset
# 4. Maintains separation of concerns
```

#### Recommended Tool Architecture for Debate Mode

```
Current Debate Tools (5):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ start_debate_round           - Round initialization
✅ query_model_in_round          - AI model query
⚠️  run_internal_analysis        - Bundled (suboptimal)
✅ collect_debate_votes          - Voting collection
✅ get_debate_summary            - Final compilation

Optimized Debate Tools (13+):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Core Debate:
✅ start_debate_round           - Round initialization
✅ query_model_in_round          - AI model query

Analysis Tools (parallel-capable):
✅ web_search_query             - Web search
✅ detect_claims                - Meta-agent tool
✅ verify_fact                  - Meta-agent tool
✅ check_logical_consistency    - Meta-agent tool
✅ find_counter_arguments       - Counter-arg finder
✅ validate_sources             - Meta-agent tool
✅ extract_entities             - Meta-agent tool
✅ detect_bias                  - Meta-agent tool (optional)

Completion:
✅ collect_debate_votes         - Voting collection
✅ get_debate_summary           - Final compilation
```

#### Migration Strategy

To implement optimized parallelism without breaking existing functionality:

1. **Phase 1**: Keep `run_internal_analysis` for backward compatibility
2. **Phase 2**: Add new granular tools (web_search_query, detect_claims, etc.)
3. **Phase 3**: Update debate system prompt to encourage parallel tool usage
4. **Phase 4**: Expose meta-agents as individual tools
5. **Phase 5**: Monitor performance improvement (expect 2-4x speedup)
6. **Phase 6**: Deprecate `run_internal_analysis` once new tools are proven

#### Performance Metrics

**Expected Improvements with Parallel Tools**:

| Scenario | Sequential (current) | Parallel (optimized) | Speedup |
|----------|---------------------|---------------------|---------|
| After each model response | 14s (bundled) | 5s (parallel) | 2.8x |
| Full Round 1 (5 models) | 70s analysis time | 25s analysis time | 2.8x |
| Complete 3-round debate | 210s analysis | 75s analysis | 2.8x |
| With 250 parallel capacity | Limited to ~20 ops | Can do 250 parallel | 12.5x potential |

**Real-World Benefit**: A 3-round debate that takes 5 minutes today could take ~2 minutes with optimized parallelism!

## State Management

Key state fields used for routing:

- `enable_debate_mode`: Boolean, triggers debate planner
- `enable_ai_comparison`: Boolean, triggers AI comparison mode
- `enable_background_investigation`: Boolean, triggers background investigator
- `enable_clarification`: Boolean, enables clarification loops
- `current_plan`: Current research plan being executed
- `locale`: Language locale for prompts
- `research_topic`: User's query/topic
- `clarified_research_topic`: Topic after clarification
- `comparison_results`: Results from AI comparison
- `debate_results`: Results from debate mode

## Routing Decision Points

### Coordinator Routing
```python
if enable_debate_mode:
    goto = "debate_planner"
elif enable_ai_comparison:
    goto = "planner"  # planner will route to ai_comparison
elif enable_background_investigation:
    goto = "background_investigator"
else:
    goto = "planner"
```

### Planner Routing
```python
if has_enough_context:
    goto = "reporter"
elif enable_ai_comparison:
    goto = "ai_comparison"
else:
    goto = "human_feedback"
```

### Research Team Routing
```python
if all_steps_complete:
    goto = "planner"
else:
    # Find first incomplete step
    if step.type == "research":
        goto = "researcher"
    elif step.type == "analysis":
        goto = "analyst"
    elif step.type == "coding":
        goto = "coder"
```

## Edge Types

- **Conditional Edges**: Routes that depend on state (e.g., research_team routing)
- **Direct Edges**: Fixed routes (e.g., background_investigator → planner)
- **Command-based Edges**: Routes determined by node return value (most nodes)

## Special Patterns

### Debate Mode Pattern
```
coordinator → debate_planner → human_feedback → research_team → reporter → END
```
- Reuses standard research workflow
- Only difference: specialized debate planner

### AI Comparison Pattern
```
coordinator → planner → ai_comparison → reporter → END
```
- Bypasses research_team entirely
- AI comparison executes all tools internally

### Normal Research Pattern
```
coordinator → planner → human_feedback → research_team → (specialists) → reporter → END
```
- Standard deep research workflow
- Multiple specialists can be invoked

### Clarification Loop Pattern
```
coordinator → coordinator → ... → coordinator → planner
```
- Loops within coordinator until clarification complete
- Then routes to appropriate planner

## Notes

- All nodes return `Command` objects that specify next routing
- State is preserved and updated throughout the workflow
- Streaming is supported for real-time updates
- Checkpointing can be enabled for conversation persistence
