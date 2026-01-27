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
**Purpose**: Multi-perspective analysis with balanced viewpoints

**Trigger Patterns**:
- "Debate X"
- "Arguments for and against Y"
- "Is Z good or bad?"
- "Should we do X?"
- Controversial or opinion-based questions

**Planning Strategy**:
- Seek opposing viewpoints explicitly
- Balance pro/con research steps
- Evidence-based argument gathering
- Multiple perspective representation

**Example Plan**:
```json
{
  "steps": [
    {"type": "research", "title": "Arguments supporting X"},
    {"type": "research", "title": "Arguments opposing X"},
    {"type": "research", "title": "Neutral analysis"},
    {"type": "analysis", "title": "Balanced synthesis"}
  ]
}
```

### 3. compare_planner (Planned)
**Purpose**: Side-by-side comparison of options

**Trigger Patterns**:
- "Compare X and Y"
- "X vs Y"
- "Difference between X and Y"
- "Which is better: X or Y?"

**Planning Strategy**:
- Research each option independently
- Identify comparison criteria
- Gather metrics for each option
- Create comparison matrix

**Example Plan**:
```json
{
  "steps": [
    {"type": "research", "title": "Research option X features"},
    {"type": "research", "title": "Research option Y features"},
    {"type": "research", "title": "Identify comparison criteria"},
    {"type": "analysis", "title": "Create comparison table"}
  ]
}
```

**Output Format**:
- Side-by-side comparison table
- Pros/cons for each option
- Recommendation based on criteria
- Context-specific guidance

### 4. general_planner (Planned)
**Purpose**: Quick, direct responses without extensive research

**Trigger Patterns**:
- Simple factual questions
- Greetings and small talk
- Basic definitions
- Questions with obvious answers
- Calculator-type queries

**Planning Strategy**:
- Minimal or no research steps
- Use existing knowledge
- Direct response generation
- Skip research_team entirely if possible

**Example Plan**:
```json
{
  "steps": [
    {"type": "direct_response", "title": "Generate answer"}
  ]
}
```

**Routing**:
- May route directly to reporter
- Bypasses research_team for simple queries
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
Any Planner → human_feedback → research_team → reporter → human_feedback → END
```

### Benefits:

1. **Code Reuse**: Single research_team implementation
2. **Consistency**: Same UX for all query types
3. **Maintainability**: Fix bugs once, benefits all modes
4. **Testability**: Test workflow once, applies to all planners
5. **Scalability**: Easy to add new planner types

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
- Implement debate_planner
- Test with enable_debate_mode flag
- Validate multi-perspective research

### Phase 2: Compare Planner (Next)
- Create compare_planner node
- Implement comparison-specific prompts
- Add comparison result formatting in reporter
- Test with enable_compare_mode flag

### Phase 3: General Planner
- Create general_planner node
- Implement fast-path routing
- Add direct_response capability
- Test response quality vs. speed

### Phase 4: Intelligent Coordinator
- Enhance coordinator with classification logic
- Remove manual mode flags
- Automatic planner selection
- Test classification accuracy

### Phase 5: Unified State
- Replace boolean flags with planner_type enum
- Simplify state management
- Clean up legacy code
- Final integration testing

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

1. Create planner node function (copy from existing planner)
2. Create specialized prompts (English & Swedish)
3. Add to graph builder: `builder.add_node("new_planner", new_planner_node)`
4. Update coordinator routing logic
5. Test with enable_new_mode flag initially
6. Eventually integrate into coordinator's automatic routing

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
