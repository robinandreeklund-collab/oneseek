# Debate Mode Documentation

## Overview

Debate Mode orchestrates a **3-round multi-model debate** where all available AI models (GPT-3.5, Gemini 2.5 Flash, DeepSeek, Grok-4, and OneSeek) participate as **equal debaters**. Each model responds sequentially in randomized order, building on previous arguments through strict chain-of-thought flow. After round 3, external models vote democratically on the best answer.

## Architecture

Debate Mode implements a specialized debate orchestration flow with dedicated nodes and tools for multi-round sequential debates.

### Current Flow

```
start
  │
  ▼
coordinator (analyzes query and routes based on mode)
  │
  ├─ enable_debate_mode=true ──→ debate_planner ──→ debate ──→ reporter ──→ END
  ├─ enable_ai_comparison=true ─→ planner ─────────→ ai_comparison ──→ reporter ──→ END
  └─ normal mode ───────────────→ planner ──────────→ human_feedback ──→ research_team ──→ reporter ──→ END
```

### Key Components

1. **Coordinator Node**
   - Analyzes incoming queries
   - Checks `enable_debate_mode` state flag
   - Routes to debate_planner when debate mode is enabled

2. **Debate Planner Node**
   - Simplified router that extracts research topic
   - Routes directly to debate node for multi-round debate orchestration

3. **Debate Node**
   - Orchestrates complete 3-round debate with all AI models
   - Uses 5 specialized debate tools for sequential execution
   - Manages randomized order, context control, and voting
   - Routes directly to reporter after debate completion

4. **Debate Flow Engine** (`backend/debate_flow.py`)
   - Manages debate state across 3 rounds
   - Initializes all available AI models (GPT-3.5, Gemini, DeepSeek, Grok-4, OneSeek)
   - Controls `chain_so_far` (current round) vs `full_previous_round` (previous complete round)
   - Runs OneSeek internal analyses between responses
   - Collects votes from external models after round 3

5. **Reporter**
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

