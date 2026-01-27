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

**Routes to**: `research_team` (always)

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
