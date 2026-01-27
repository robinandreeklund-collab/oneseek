# OneSeek Graph Architecture - Future Vision

This document describes the planned future architecture for OneSeek's LangGraph workflow, featuring multiple specialized planners.

## Future Graph Structure (Multi-Planner Architecture)

```
┌─────────┐
│  START  │
└────┬────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│                      coordinator                              │
│                                                               │
│  (analyzes query and routes based on content/intent)         │
└──────────┬──────────────┬──────────────┬──────────────┬──────┘
           │              │              │              │
           │              │              │              │
    ┌──────┴──────┐  ┌───┴──────┐  ┌───┴──────┐  ┌───┴──────────┐
    │             │  │          │  │          │  │              │
    │  debate     │  │ compare  │  │ research │  │   general    │
    │  query      │  │ query    │  │ query    │  │   query      │
    │             │  │          │  │          │  │              │
    ▼             │  ▼          │  ▼          │  ▼              │
┌───────────────┐ │ ┌──────────────┐ ┌──────────────┐ ┌─────────────────┐
│ debate_       │ │ │ compare_     │ │ research_    │ │ general_        │
│ planner       │ │ │ planner      │ │ planner      │ │ planner         │
│               │ │ │              │ │ (current     │ │                 │
│ Multi-        │ │ │ AI model     │ │ planner)     │ │ Direct          │
│ perspective   │ │ │ comparison   │ │              │ │ responses       │
│ research      │ │ │ planning     │ │ Deep         │ │ Simple answers  │
└───────┬───────┘ │ └──────┬───────┘ │ research     │ │ No research     │
        │         │        │         │ planning     │ └────────┬────────┘
        │         │        │         └──────┬───────┘          │
        │         │        │                │                  │
        └─────────┴────────┴────────────────┘                  │
                  │                                            │
                  │  (all planners route to unified workflow)  │
                  │                                            │
                  ▼                                            │
        ┌──────────────────┐                                  │
        │  human_feedback  │                                  │
        │                  │                                  │
        │  (plan approval) │                                  │
        └────────┬─────────┘                                  │
                 │                                             │
                 │                                             │
                 ▼                                             │
        ┌──────────────────┐                                  │
        │  research_team   │                                  │
        │                  │                                  │
        │  (unified exec)  │                                  │
        └────────┬─────────┘                                  │
                 │                                             │
                 │  (conditional routing to specialists)       │
                 │                                             │
            ┌────┴────┬──────────┬──────────┐                │
            │         │          │          │                 │
            ▼         ▼          ▼          ▼                 │
      ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐       │
      │researcher│ │ analyst  │ │ coder  │ │  ...   │       │
      └────┬─────┘ └────┬─────┘ └───┬────┘ └───┬────┘       │
           │            │            │          │             │
           └────────────┴────────────┴──────────┘             │
                        │                                     │
                        │  (loop back until all steps done)   │
                        │                                     │
                        ▼                                     │
                ┌────────────────┐                           │
                │    reporter    │◄──────────────────────────┘
                │                │
                │  (synthesis)   │
                └────────┬───────┘
                         │
                         │
                         ▼
                ┌──────────────────┐
                │  human_feedback  │
                │                  │
                │  (loop back or   │
                │   end)           │
                └────────┬─────────┘
                         │
                    ┌────┴────┐
                    │         │
             (approved)   (edit plan)
                    │         │
                    ▼         └──────► (back to respective planner)
                ┌───────┐
                │  END  │
                └───────┘
```

## Planner Types (Future)

### 1. research_planner (Current "planner")
**Purpose**: Deep research with comprehensive information gathering

**Trigger Patterns**:
- "Research X"
- "Tell me about Y"
- "What is Z?"
- Complex, open-ended questions
- Questions requiring extensive web search

**Planning Strategy**:
- Break down into multiple research steps
- Emphasize depth and breadth
- Multiple search queries per topic
- Analysis and synthesis steps

**Example Plan**:
```json
{
  "steps": [
    {"type": "research", "title": "Historical context"},
    {"type": "research", "title": "Current state"},
    {"type": "research", "title": "Expert opinions"},
    {"type": "analysis", "title": "Synthesis"}
  ]
}
```

### 2. debate_planner (Implemented)
**Purpose**: Multi-model debate with sequential argumentation and democratic voting

**Trigger Patterns**:
- "Debate X"
- "Arguments for and against Y"
- "Is Z good or bad?"
- "Should we do X?"
- Controversial or opinion-based questions

**Planning Strategy**:
- Creates 4-step plan for 3-round debate + voting
- Each round queries all AI models sequentially
- Models treated as tools within researcher execution
- Round order randomized for fairness
- OneSeek performs internal analysis between responses

**Example Plan**:
```json
{
  "topic": "Is nuclear power necessary to meet climate goals?",
  "steps": [
    {
      "id": 1,
      "type": "researcher",
      "description": "Round 1: Initial arguments from all models",
      "details": "Query each model: GPT-3.5, Gemini, DeepSeek, Grok, OneSeek"
    },
    {
      "id": 2,
      "type": "researcher",
      "description": "Round 2: Development and counter-arguments",
      "details": "Re-randomized order, models see Round 1 context"
    },
    {
      "id": 3,
      "type": "researcher",
      "description": "Round 3: Final positions and synthesis",
      "details": "OneSeek creates comprehensive synthesis when it's OneSeek's turn"
    },
    {
      "id": 4,
      "type": "researcher",
      "description": "Voting and summary",
      "details": "External models vote on best Round 3 answer"
    }
  ]
}
```

**Tool Execution Within Researcher**:
- `start_debate_round(round_num)` - Initialize round with randomized order
- `query_model_in_round(model, query)` - Query specific model (5 per round)
- `run_internal_analysis(query)` - OneSeek fact-checking (5 per round)
- `collect_debate_votes(query)` - Gather votes from external models
- `get_debate_summary()` - Compile final results

**Workflow**:
```
debate_planner (creates plan) → human_feedback (approval) → 
research_team → researcher (executes debate tools) → reporter (synthesizes)
```

### 3. compare_planner (Planned)
**Purpose**: Side-by-side comparison with all AI models providing perspectives

**Trigger Patterns**:
- "Compare X and Y"
- "X vs Y"
- "Difference between X and Y"
- "Which is better: X or Y?"

**Planning Strategy**:
- Creates multi-step plan for comparative analysis
- Each AI model (GPT-3.5, Gemini, DeepSeek, Grok, OneSeek) analyzes both options
- Models treated as tools within researcher execution
- Research phase gathers objective data on each option
- Comparison phase has each model create side-by-side analysis
- OneSeek synthesizes all perspectives into unified comparison

**Example Plan**:
```json
{
  "topic": "Compare Python vs JavaScript for web development",
  "steps": [
    {
      "id": 1,
      "type": "researcher",
      "description": "Research Python capabilities",
      "details": "Web frameworks, performance, ecosystem, use cases"
    },
    {
      "id": 2,
      "type": "researcher",
      "description": "Research JavaScript capabilities",
      "details": "Frameworks, performance, ecosystem, use cases"
    },
    {
      "id": 3,
      "type": "researcher",
      "description": "Multi-model comparison analysis",
      "details": "Each AI model creates comparison based on gathered data"
    },
    {
      "id": 4,
      "type": "researcher",
      "description": "Unified synthesis",
      "details": "OneSeek synthesizes all model perspectives into comparison table"
    }
  ]
}
```

**Tool Execution Within Researcher**:
- Standard research tools for Steps 1-2 (web_search, crawl, retriever)
- Comparison-specific tools for Steps 3-4:
  - `query_model_comparison(model, option_a, option_b)` - Get model's comparison
  - `gather_comparison_criteria()` - Extract common comparison points
  - `create_comparison_matrix()` - Build structured comparison table
  - `synthesize_comparison()` - OneSeek creates unified analysis

**Output Format**:
- Side-by-side comparison table with all perspectives
- Each AI model's analysis included
- Pros/cons from multiple viewpoints
- Consensus recommendation where models agree
- Divergent opinions highlighted where models disagree

**Workflow**:
```
compare_planner (creates plan) → human_feedback (approval) → 
research_team → researcher (gathers data + executes comparison tools) → reporter (formats comparison)
```

### 4. general_planner (Planned)
**Purpose**: Quick, direct responses leveraging all AI models for simple queries

**Trigger Patterns**:
- Simple factual questions
- Greetings and small talk
- Basic definitions
- Questions with obvious answers
- Calculator-type queries

**Planning Strategy**:
- Creates minimal 1-2 step plan for quick execution
- May query multiple AI models for diverse quick takes
- Skip extensive research for simple queries
- Fast-path through researcher with minimal tools

**Example Plan**:
```json
{
  "topic": "What is the capital of France?",
  "steps": [
    {
      "id": 1,
      "type": "researcher",
      "description": "Quick multi-model response",
      "details": "Query 2-3 AI models for quick answer, synthesize"
    }
  ]
}
```

**Alternative Plan for Very Simple Queries**:
```json
{
  "topic": "Hello, how are you?",
  "steps": [
    {
      "id": 1,
      "type": "direct_response",
      "description": "Generate greeting response",
      "details": "OneSeek generates direct response, no model querying needed"
    }
  ]
}
```

**Tool Execution Within Researcher**:
- Minimal tool usage for speed
- `query_model_quick(model, query)` - Fast query without context building
- `direct_answer()` - OneSeek generates answer from existing knowledge
- Optional: Single web_search for fact verification

**Workflow**:
```
general_planner (creates minimal plan) → human_feedback (approval) → 
research_team → researcher (minimal tools) → reporter (quick formatting)
```

**Optimization**:
- Bypasses extensive research steps
- Uses fewer AI model calls (1-3 instead of 5)
- Shorter token limits for responses
- May skip reporter for very simple queries
- Fastest path for basic questions

## Coordinator Intelligence

The coordinator uses advanced analysis to determine which planner to use:

### Query Analysis Dimensions

1. **Complexity**: Simple vs. Complex
2. **Controversy**: Factual vs. Opinion-based
3. **Comparison**: Single topic vs. Multiple options
4. **Depth**: Surface-level vs. Deep-dive

### Routing Decision Matrix

| Query Type | Complexity | Controversy | Comparison | → Planner |
|-----------|-----------|------------|------------|-----------|
| "What is X?" | Low | Low | No | general_planner |
| "Research X" | High | Low | No | research_planner |
| "Is X good?" | Medium | High | No | debate_planner |
| "X vs Y" | Medium | Low | Yes | compare_planner |
| "Debate: Should we X?" | High | High | No | debate_planner |

### Coordinator Prompt Enhancement

Future coordinator prompt will include:

```markdown
Analyze the user query and classify it:

1. **Query Intent**:
   - Information seeking (→ research_planner)
   - Opinion/debate seeking (→ debate_planner)
   - Comparison seeking (→ compare_planner)
   - Simple question (→ general_planner)

2. **Required Depth**:
   - Shallow (→ general_planner)
   - Moderate (→ compare_planner or debate_planner)
   - Deep (→ research_planner)

3. **Controversy Level**:
   - Factual/neutral (→ research_planner or compare_planner)
   - Opinion-based (→ debate_planner)

Route to appropriate planner based on classification.
```

## Unified Workflow Benefits

All planners share the same downstream workflow:

```
Any Planner (creates plan) → human_feedback (approval) → research_team → researcher (executes with appropriate tools) → reporter (synthesizes) → human_feedback (loop or end) → END
```

### Key Principle: Planners Create Plans, Researcher Executes Tools

- **Planners**: Create structured Plan objects with steps describing what to do
- **Researcher**: Executes the plan using appropriate tools based on step types
- **Tool Swapping**: Researcher detects mode (debate, compare, etc.) and loads corresponding tools
- **Models as Tools**: AI models become tools that researcher invokes during execution

### Benefits:

1. **Code Reuse**: Single research_team → researcher → reporter pipeline for all modes
2. **Consistency**: Same UX, streaming behavior, and error handling for all query types
3. **Maintainability**: Fix bugs once in researcher, benefits all planners
4. **Testability**: Test workflow once, applies to all planners
5. **Scalability**: Easy to add new planner types - just create plan structure and tools
6. **Modularity**: Clear separation between planning (what to do) and execution (how to do it)

### Tool Swapping in Researcher

The researcher node detects the plan type/mode and swaps toolsets:

**Normal Research Mode**:
- web_search, crawl, retriever, calculator, etc.

**Debate Mode** (when `enable_debate_mode=True`):
- start_debate_round, query_model_in_round, run_internal_analysis, collect_debate_votes, get_debate_summary

**Compare Mode** (future, when `enable_compare_mode=True`):
- web_search, crawl (for research steps)
- query_model_comparison, create_comparison_matrix, synthesize_comparison (for comparison steps)

**General Mode** (future, when `enable_general_mode=True` or simple query):
- query_model_quick, direct_answer
- Minimal tool usage for speed

This architecture ensures that adding a new mode requires:
1. Creating a new planner node
2. Creating tools specific to that mode
3. Adding tool swapping logic in researcher
4. No changes to core workflow (human_feedback, research_team, reporter)

## State Fields for Multi-Planner System

### Current State Fields
```python
enable_debate_mode: bool = False
enable_ai_comparison: bool = False
```

### Future State Fields (Planned)
```python
planner_type: Literal["research", "debate", "compare", "general"] = "research"
planning_strategy: str = ""  # Detailed strategy from coordinator
comparison_options: List[str] = []  # For compare_planner
debate_perspectives: List[str] = []  # For debate_planner
```

## Migration Path

### Phase 1: ✅ Debate Planner (Current)
- Implement debate_planner node ✅
- Create debate tools (start_debate_round, query_model_in_round, etc.) ✅
- Add tool swapping logic in researcher for debate mode ✅
- Test with enable_debate_mode flag ✅
- Validate 3-round multi-model debate with voting ✅
- Document unified workflow pattern ✅

### Phase 2: Compare Planner (Next)
- Create compare_planner node (copy pattern from debate_planner)
- Implement comparison-specific tools:
  - `query_model_comparison(model, option_a, option_b)`
  - `gather_comparison_criteria()`
  - `create_comparison_matrix()`
  - `synthesize_comparison()`
- Add tool swapping logic in researcher for compare mode
- Add comparison result formatting in reporter
- Test with enable_compare_mode flag
- Validate multi-model comparison analysis

### Phase 3: General Planner
- Create general_planner node (copy pattern from debate_planner)
- Implement fast-path tools:
  - `query_model_quick(model, query)`
  - `direct_answer()`
- Add tool swapping logic in researcher for general mode
- Optimize for speed (fewer models, shorter tokens)
- Test with enable_general_mode flag
- Validate response quality vs. speed tradeoff

### Phase 4: Intelligent Coordinator
- Enhance coordinator with classification logic
- Remove manual mode flags (enable_debate_mode, etc.)
- Automatic planner selection based on query analysis
- Test classification accuracy across query types
- Gradual rollout with fallback to manual flags

### Phase 5: Unified State
- Replace boolean flags with planner_type enum
- Simplify state management (single field vs. multiple booleans)
- Update tool swapping to use planner_type instead of flags
- Clean up legacy code
- Final integration testing across all modes

## Future Enhancements

### Additional Planner Types

1. **tutorial_planner**: Step-by-step how-to guides
2. **analysis_planner**: Data analysis and insights
3. **creative_planner**: Creative writing and brainstorming
4. **diagnostic_planner**: Problem diagnosis and troubleshooting

### Advanced Features

1. **Multi-round planning**: Planners can request additional rounds
2. **Hybrid modes**: Combine multiple planners for complex queries
3. **User preferences**: Remember user's preferred planner style
4. **Context-aware routing**: Use conversation history for better routing

## Implementation Notes

### Adding a New Planner

1. **Create planner node function** (copy from debate_planner_node)
   - Extract topic from query
   - Create Plan object with appropriate steps
   - Route to human_feedback

2. **Create specialized prompts** (English & Swedish)
   - Planning prompt for the planner node
   - Execution prompt for researcher (optional, if different from standard)

3. **Create mode-specific tools** (if needed)
   - Tools that researcher will use during execution
   - Follow pattern from debate_tools.py
   - Each tool should be focused and composable

4. **Add tool swapping logic in researcher**
   - Detect mode via state flag (enable_X_mode) or plan analysis
   - Load appropriate tools for that mode
   - Example: `if state.enable_compare_mode: tools = get_compare_tools()`

5. **Add to graph builder**
   - `builder.add_node("new_planner", new_planner_node)`
   - Configure edge: `new_planner → human_feedback`
   - Update coordinator routing to include new planner

6. **Test with mode flag initially**
   - Add `enable_new_mode` boolean to state
   - Test end-to-end workflow with flag enabled
   - Validate plan creation and tool execution

7. **Eventually integrate into coordinator's automatic routing**
   - Add query pattern detection in coordinator
   - Remove manual flag requirement
   - Automatic planner selection

### Testing Strategy

For each new planner:

1. Unit test planner node in isolation
2. Integration test with research_team
3. End-to-end test full workflow
4. Validate output quality
5. Test edge cases and error handling

## Backward Compatibility

- Existing functionality remains unchanged
- New planners add capabilities, don't replace
- research_planner (current planner) remains default
- Legacy enable_* flags supported during transition

## Documentation Requirements

For each planner:

- Planning strategy documentation
- Example queries and plans
- Output format specification
- Configuration options
- Troubleshooting guide

## Success Metrics

- **Response Quality**: User satisfaction with answers
- **Response Time**: Time to generate plan and complete research
- **Routing Accuracy**: Correct planner selected for query type
- **Code Reuse**: Percentage of shared vs. specialized code
- **Maintainability**: Time to add new planner or fix bugs

## Timeline

- **Q1 2026**: debate_planner (✅ Complete)
- **Q2 2026**: compare_planner
- **Q3 2026**: general_planner
- **Q4 2026**: Intelligent coordinator with automatic routing
- **2027**: Additional specialized planners as needed
