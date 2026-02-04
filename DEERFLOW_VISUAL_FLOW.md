# DEER-FLOW: Visuella Data Flödes-Diagram

## 📊 Komplett Visuell Översikt

Detta dokument innehåller detaljerade visuella diagram över hur data flödar genom deer-flow's forskningssystem, med fokus på faktakontroll och källspårning.

---

## 1. Övergripande Workflow

```
╔═══════════════════════════════════════════════════════════════════════╗
║                      DEER-FLOW MAIN WORKFLOW                          ║
╚═══════════════════════════════════════════════════════════════════════╝

┌─────────┐
│  START  │
└────┬────┘
     │
     ↓
┌──────────────────────────────────────────────────────────────┐
│                     COORDINATOR                               │
│  • Detektera språk (locale)                                  │
│  • Analysera user intent                                      │
│  • Route: greeting/chitchat → direct_response                │
│           research question → handoff_to_planner             │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────────────────────────┐
│           BACKGROUND INVESTIGATION (Optional)                 │
│  • enable_background_investigation = True/False              │
│  • Quick web_search för kontext                             │
│  • Samla bakgrundsinfo för planner                          │
│  • OUTPUT: Initial search results                           │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────────────────────────┐
│                        PLANNER                                │
│  • Skapa strukturerad plan                                   │
│  • Dela upp i steps:                                         │
│    - RESEARCH (requires web_search/RAG)                     │
│    - ANALYSIS (pure reasoning)                               │
│    - PROCESSING (code execution)                             │
│  • OUTPUT: Plan object med steps                            │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────────────────────────┐
│                   RESEARCH TEAM (Supervisor)                  │
│  • Läs plan, iterera genom steps                            │
│  • Route till rätt agent baserat på step_type:              │
│    - RESEARCH → Researcher                                   │
│    - ANALYSIS → Analyst                                      │
│    - PROCESSING → Coder                                      │
│  • Samla execution results                                   │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ├───────────┬───────────┬────────────┐
                   ↓           ↓           ↓            ↓
           ┌──────────┐ ┌──────────┐ ┌──────────┐     │
           │RESEARCHER│ │ ANALYST  │ │  CODER   │     │
           │(+Tools)  │ │(No Tools)│ │(+Python) │     │
           └────┬─────┘ └────┬─────┘ └────┬─────┘     │
                │            │            │            │
                └────────────┴────────────┴────────────┘
                                  │
                                  ↓
                    ┌──────────────────────────┐
                    │ All steps completed?     │
                    │ YES → Reporter           │
                    │ NO  → Next step          │
                    └──────────┬───────────────┘
                               ↓
                    ┌──────────────────────────┐
                    │       REPORTER           │
                    │ • Sammanställ results    │
                    │ • Extrahera citations    │
                    │ • Skapa final report     │
                    └──────────┬───────────────┘
                               │
                               ↓
                           ┌───────┐
                           │  END  │
                           └───────┘
```

---

## 2. Researcher Agent: Detaljerat Flöde

```
╔═══════════════════════════════════════════════════════════════════════╗
║              RESEARCHER AGENT: FACT-CHECKING FLOW                     ║
╚═══════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────┐
│ INPUT från Research Team:                                           │
│  • Task description                                                 │
│  • Step context från planner                                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ↓
┌──────────────────────────────────────────────────────────────────────┐
│                    TOOL SELECTION                                     │
│                                                                       │
│  if (user uploaded resources):                                       │
│    tools = [local_search_tool, web_search, crawl_tool]  ← ORDNING! │
│  else:                                                               │
│    tools = [web_search, crawl_tool]                                 │
│                                                                       │
│  Priority: RAG FÖRST, sedan web, sedan crawl                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ↓
┌──────────────────────────────────────────────────────────────────────┐
│                  AGENT EXECUTION START                                │
│  Prompt instruktioner:                                               │
│  1. "MANDATORY: Always perform web_search first"                    │
│  2. "CRITICAL: NEVER generate URLs on your own"                     │
│  3. "Forget previous knowledge, use tools"                          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ↓
        ┌──────────────────────────────────────────┐
        │  DECISION: Vilka verktyg ska användas?   │
        └──────────────┬───────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       ↓               ↓               ↓
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│LOCAL_SEARCH │ │ WEB_SEARCH  │ │ CRAWL_TOOL  │
│(if RAG)     │ │ (MANDATORY) │ │ (optional)  │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       │  Query: "AI safety concerns"  │
       │               ↓               │
       │  ┌────────────────────────┐  │
       │  │ Search Engine          │  │
       │  │ (Tavily/Bing/Google)   │  │
       │  └────────────┬───────────┘  │
       │               ↓               │
       │  ┌────────────────────────┐  │
       │  │ Results: [              │  │
       │  │   {title, url, snippet} │  │
       │  │   {title, url, snippet} │  │
       │  │   ...                   │  │
       │  │ ]                       │  │
       │  └────────────┬───────────┘  │
       │               ↓               │
       └───────────────┼───────────────┘
                       │
                       ↓
        ┌──────────────────────────────────────┐
        │ SYNTHESIS PHASE                       │
        │  • Kombinera RAG + Web + Crawl data  │
        │  • Identifiera huvudpunkter          │
        │  • Spåra källor per information      │
        │  • Organisera per topic (ej per tool)│
        └──────────────┬───────────────────────┘
                       │
                       ↓
        ┌──────────────────────────────────────┐
        │ OUTPUT FORMAT                         │
        │                                       │
        │ ## Problem Statement                  │
        │ [Restate task]                        │
        │                                       │
        │ ## Research Findings                  │
        │ ### Topic 1                           │
        │ - Finding A                           │
        │ - Finding B                           │
        │ ![image](url_from_search)             │
        │                                       │
        │ ### Topic 2                           │
        │ - Finding C                           │
        │                                       │
        │ ## Conclusion                         │
        │ [Synthesized answer]                  │
        │                                       │
        │ ## References                         │
        │ - [Title 1](https://source1.com)     │
        │                                       │
        │ - [Title 2](https://source2.com)     │
        └──────────────┬───────────────────────┘
                       │
                       ↓
        ┌──────────────────────────────────────┐
        │ RETURN TO RESEARCH TEAM               │
        │  execution_res = response text        │
        └───────────────────────────────────────┘
```

---

## 3. Source Tracking: Citations Flow

```
╔═══════════════════════════════════════════════════════════════════════╗
║                    CITATION TRACKING FLOW                             ║
╚═══════════════════════════════════════════════════════════════════════╝

Stage 1: TOOL EXECUTION
┌────────────────────────────────────────────────────────────┐
│ web_search("quantum computing 2024")                       │
│  ↓                                                          │
│ RETURNS:                                                   │
│ [                                                           │
│   {                                                         │
│     title: "Quantum Breakthrough at IBM"                   │
│     url: "https://ibm.com/quantum-2024"                   │
│     snippet: "IBM announces..."                            │
│   },                                                        │
│   {                                                         │
│     title: "Nature: Quantum Error Correction"              │
│     url: "https://nature.com/articles/quantum-ecc"        │
│     snippet: "Researchers demonstrate..."                  │
│   }                                                         │
│ ]                                                           │
└────────────────────────────────────────────────────────────┘
                           │
                           ↓
Stage 2: RESEARCHER PROCESSING
┌────────────────────────────────────────────────────────────┐
│ LLM reads tool results och writes response:                │
│                                                             │
│ "Recent advances in quantum computing include IBM's        │
│  breakthrough in quantum error correction..."              │
│                                                             │
│ References section:                                         │
│ - [IBM Quantum](https://ibm.com/quantum-2024)             │
│ - [Nature Article](https://nature.com/articles...)        │
│                                                             │
│ NOTE: URLs kommer från tool results, ej LLM generation     │
└────────────────────────────────────────────────────────────┘
                           │
                           ↓
Stage 3: MESSAGE STORAGE
┌────────────────────────────────────────────────────────────┐
│ state["messages"] append:                                   │
│ {                                                           │
│   role: "ai",                                              │
│   content: "Recent advances...[response]...References..."  │
│   name: "researcher",                                      │
│   tool_calls: [web_search results],                       │
│   metadata: {step_id, sources}                            │
│ }                                                           │
└────────────────────────────────────────────────────────────┘
                           │
                           ↓
Stage 4: CITATION EXTRACTION (Reporter)
┌────────────────────────────────────────────────────────────┐
│ from src.citations import extract_citations_from_messages  │
│                                                             │
│ citations = extract_citations_from_messages(                │
│     state["messages"]                                       │
│ )                                                           │
│  ↓                                                          │
│ RETURNS:                                                    │
│ [                                                           │
│   {                                                         │
│     title: "IBM Quantum",                                  │
│     url: "https://ibm.com/quantum-2024",                  │
│     source: "researcher step 1"                            │
│   },                                                        │
│   {                                                         │
│     title: "Nature Article",                               │
│     url: "https://nature.com/articles/...",               │
│     source: "researcher step 1"                            │
│   }                                                         │
│ ]                                                           │
└────────────────────────────────────────────────────────────┘
                           │
                           ↓
Stage 5: FINAL REPORT ASSEMBLY
┌────────────────────────────────────────────────────────────┐
│ Reporter node kompilerar:                                   │
│                                                             │
│ # Research Report                                           │
│                                                             │
│ [Content from all steps]                                    │
│                                                             │
│ ## References                                               │
│                                                             │
│ - [IBM Quantum](https://ibm.com/quantum-2024)             │
│                                                             │
│ - [Nature: Quantum Error Correction]                       │
│   (https://nature.com/articles/quantum-ecc)               │
│                                                             │
│ - [ArXiv Paper](https://arxiv.org/...)                    │
│                                                             │
│ [Empty line mellan varje källa för readability]            │
└────────────────────────────────────────────────────────────┘
```

---

## 4. RAG + Web Search: Prioriteringsstrategi

```
╔═══════════════════════════════════════════════════════════════════════╗
║          RAG + WEB SEARCH PRIORITY FLOW                               ║
╚═══════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────┐
│ USER QUERY: "Analyze my uploaded documents about AI safety" │
│ RESOURCES: [ai_safety_paper_1.pdf, ai_safety_paper_2.pdf]  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                  TOOL INITIALIZATION                          │
│                                                               │
│  tools = []                                                   │
│                                                               │
│  # Add retriever FIRST (highest priority)                    │
│  if state.get("resources"):                                  │
│      retriever = get_retriever_tool(resources)               │
│      tools.insert(0, retriever)  ← Index 0 = Högst prioritet │
│                                                               │
│  # Add web search second                                     │
│  if enable_web_search:                                       │
│      tools.append(web_search)                                │
│      tools.append(crawl_tool)                                │
│                                                               │
│  RESULT: tools = [retriever, web_search, crawl]             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌──────────────────────────────────────────────────────────────┐
│              LLM TOOL SELECTION LOGIC                         │
│                                                               │
│  Prompt säger:                                               │
│  "If user mentioned documents, use local_search_tool first"  │
│                                                               │
│  LLM reasoning:                                              │
│  1. User sa "my uploaded documents"                          │
│  2. local_search_tool finns i tools list                    │
│  3. → Call local_search_tool("AI safety concerns")          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
    ┌──────────────────────────────────────────────┐
    │        TOOL CALL 1: local_search_tool        │
    │  Query: "AI safety concerns"                 │
    │   ↓                                           │
    │  Vector search i uploaded PDFs               │
    │   ↓                                           │
    │  RETURNS: [                                   │
    │    "Chunk 1 from paper 1: AI alignment..."   │
    │    "Chunk 2 from paper 2: Safety metrics..." │
    │    "Chunk 3 from paper 1: Risk assessment..." │
    │  ]                                            │
    └──────────────────┬───────────────────────────┘
                       │
                       ↓
    ┌──────────────────────────────────────────────┐
    │ LLM EVALUATION:                              │
    │ "RAG results ger bra overview, men saknar    │
    │  senaste 2024 utvecklingar. Behöver          │
    │  komplettera med web search."                │
    └──────────────────┬───────────────────────────┘
                       │
                       ↓
    ┌──────────────────────────────────────────────┐
    │        TOOL CALL 2: web_search               │
    │  Query: "AI safety latest research 2024"     │
    │   ↓                                           │
    │  RETURNS: [                                   │
    │    {url: anthropic.com, title: "..."}        │
    │    {url: openai.com, title: "..."}          │
    │  ]                                            │
    └──────────────────┬───────────────────────────┘
                       │
                       ↓
    ┌──────────────────────────────────────────────┐
    │            SYNTHESIS                          │
    │                                               │
    │  COMBINE:                                     │
    │  • RAG findings (user's papers)              │
    │  • Web findings (latest 2024 research)       │
    │                                               │
    │  OUTPUT:                                      │
    │  "Based on your uploaded documents:          │
    │   [findings from RAG]                         │
    │                                               │
    │   Latest developments in 2024:                │
    │   [findings from web]                         │
    │                                               │
    │   References:                                 │
    │   - Your documents: ai_safety_paper_1.pdf    │
    │   - Anthropic Safety Report (...)            │
    │   - OpenAI Alignment Research (...)          │
    │  "                                            │
    └───────────────────────────────────────────────┘
```

---

## 5. Multi-Step Research: Komplett Exempel

```
╔═══════════════════════════════════════════════════════════════════════╗
║     MULTI-STEP RESEARCH EXAMPLE: "Future of Renewable Energy"        ║
╚═══════════════════════════════════════════════════════════════════════╝

USER INPUT
───────────
"What are the latest developments in renewable energy and their 
 economic impact for 2024-2025?"

│
↓

COORDINATOR
───────────
• Detect: Research question, not greeting
• Action: handoff_to_planner

│
↓

BACKGROUND INVESTIGATION (Optional)
──────────────────────────────────
• web_search("renewable energy 2024 2025")
• Quick scan: Solar, wind, battery tech trending
• Pass context to planner

│
↓

PLANNER
───────
Creates 3-step plan:

  Step 1: RESEARCH
    "Latest renewable energy technologies 2024-2025"
  
  Step 2: RESEARCH  
    "Economic impact and investment in renewables"
  
  Step 3: ANALYSIS
    "Synthesize tech + economic trends"

│
↓

RESEARCH TEAM → Step 1: RESEARCHER
───────────────────────────────────

Tool calls:
  1. web_search("renewable energy latest technology 2024 2025")
     → [10 results: solar, wind, battery innovations]
  
  2. crawl_tool("https://iea.org/reports/renewables-2024")
     → Full report content
  
  3. crawl_tool("https://nature.com/articles/solar-perovskite")
     → Research paper details

Synthesis:
  "## Latest Technologies

   ### Solar Power
   - Perovskite solar cells reaching 30% efficiency
   - [Source: Nature]
   
   ### Wind Energy  
   - Offshore wind farms 15MW turbines
   - [Source: IEA Report]
   
   ### Energy Storage
   - Solid-state batteries commercial by 2025
   - [Source: BloombergNEF]"

execution_res = [response with sources]

│
↓

RESEARCH TEAM → Step 2: RESEARCHER
───────────────────────────────────

Tool calls:
  1. web_search("renewable energy investment economic impact 2024")
     → [Results on funding, jobs, GDP impact]
  
  2. crawl_tool("https://irena.org/publications/2024/economic")
     → Economic analysis report

Synthesis:
  "## Economic Impact
  
   ### Investment
   - $500B global investment in 2024
   - [Source: IRENA]
   
   ### Employment
   - 12M jobs in renewable sector
   - [Source: IRENA]
   
   ### Cost Competitiveness
   - Solar now cheapest electricity source
   - [Source: BloombergNEF]"

execution_res = [response with sources]

│
↓

RESEARCH TEAM → Step 3: ANALYST
────────────────────────────────

No tools (pure reasoning)

Input:
  - Step 1 results (tech trends)
  - Step 2 results (economic impact)

Analysis:
  "## Synthesis
  
   Combining technological and economic trends:
   
   1. **Technology-Cost Correlation**
      - Efficiency gains → Cost reductions
      - Perovskite cells could lower solar costs 40%
   
   2. **Investment Drivers**
      - Battery tech enables grid stability
      - Offshore wind scales economy of scale
   
   3. **2024-2025 Outlook**
      - Accelerating adoption in Asia-Pacific
      - Policy support in EU, US critical
   
   Key insight: Economic viability now driving 
   adoption more than environmental policy."

execution_res = [analysis]

│
↓

REPORTER
────────

Compile all steps:

# Research Report: Future of Renewable Energy

## Problem Statement
[Restate user question]

## Research Findings

### Latest Technologies (Step 1 findings)
[Solar, Wind, Storage details]

### Economic Impact (Step 2 findings)  
[Investment, jobs, costs]

### Analysis (Step 3 synthesis)
[Integrated insights]

## Conclusion
[Overall synthesis]

## References

- [Nature: Perovskite Solar Cells](https://nature.com/...)

- [IEA Renewables 2024 Report](https://iea.org/...)

- [IRENA Economic Analysis](https://irena.org/...)

- [BloombergNEF Market Outlook](https://bnef.com/...)

│
↓

END
───
Return final report to user
```

---

## 6. Error Handling och Edge Cases

```
╔═══════════════════════════════════════════════════════════════════════╗
║                    ERROR HANDLING FLOW                                ║
╚═══════════════════════════════════════════════════════════════════════╝

Scenario A: Web Search Fails
─────────────────────────────

  web_search(query)
       │
       ├─→ Timeout / API Error
       │
       ↓
  Return: "Search failed: [error]"
       │
       ↓
  LLM Response: 
    "Unable to perform web search. Based on available 
     information..."
       │
       ↓
  Falls back to:
    - RAG data (if available)
    - LLM knowledge (with disclaimer)


Scenario B: All Tools Disabled
───────────────────────────────

  enable_web_search = False
  resources = []
       │
       ↓
  tools = []  (empty list)
       │
       ↓
  Warning logged:
    "No tools available. Pure reasoning mode."
       │
       ↓
  Researcher operates on:
    - LLM internal knowledge only
    - Explicitly states: "Based on general 
      knowledge, without external verification..."


Scenario C: URL Generation Attempt
───────────────────────────────────

  LLM tries to write:
    "See more at https://example.com/fake-url"
       │
       ↓
  Prompt EXPLICITLY forbids this:
    "CRITICAL: NEVER generate URLs on your own"
       │
       ↓
  IF it happens anyway:
    - Reporter/citation extractor validates URLs
    - Only URLs from tool results included
    - Generated URLs filtered out


Scenario D: GraphRecursionError
────────────────────────────────

  Agent calls tools repeatedly
       │
       ├─→ 100 iterations reached
       │
       ↓
  GraphRecursionError raised
       │
       ↓
  Deer-flow approach:
    - Task-based iteration (not agent loop)
    - Each step = discrete task
    - No recursion within single task
       │
       ↓
  Result: ERROR PREVENTED BY DESIGN
```

---

## 7. Konfiguration: Decision Tree

```
╔═══════════════════════════════════════════════════════════════════════╗
║              CONFIGURATION DECISION TREE                              ║
╚═══════════════════════════════════════════════════════════════════════╝

                    ┌─────────────────┐
                    │  Start Workflow │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │enable_background│
                    │_investigation?  │
                    └────┬──────┬─────┘
                         │      │
                    YES  │      │  NO
                         │      │
                    ┌────▼──┐  └──→ Skip to Planner
                    │ Do    │
                    │ Search│
                    └───┬───┘
                        │
                        ↓
                    ┌────────────────┐
                    │   PLANNER      │
                    └────────┬───────┘
                             │
                    ┌────────▼────────┐
                    │ Steps created   │
                    │ with step_type  │
                    └────┬──────┬─────┘
                         │      │
                    RESEARCH  ANALYSIS
                         │      │
                    ┌────▼──┐  └──→ Analyst (no tools)
                    │User   │
                    │upload?│
                    └─┬───┬─┘
                      │   │
                 YES  │   │  NO
                      │   │
                ┌─────▼┐  └──→ web_search only
                │ RAG  │
                │first │
                └──┬───┘
                   │
          ┌────────▼────────┐
          │enforce_researcher│
          │    _search?      │
          └────┬──────┬──────┘
               │      │
          YES  │      │  NO
               │      │
         ┌─────▼┐    └──→ RAG only if sufficient
         │ Do   │
         │ both │
         │RAG + │
         │ Web  │
         └──────┘
```

---

## Slutsats: Varför Deer-Flow Fungerar Perfekt

### Visuell Sammanfattning

```
┌──────────────────────────────────────────────────────────────┐
│           DEER-FLOW SUCCESS FACTORS                          │
│                                                               │
│  1. PROACTIVE SEARCH                                         │
│     └─→ Söker FÖRST, resonerar sedan                        │
│                                                               │
│  2. STRICT RULES                                             │
│     └─→ Aldrig generera URLs, endast från verktyg           │
│                                                               │
│  3. TASK-BASED ITERATION                                     │
│     └─→ En uppgift i taget, ingen agent-loop                │
│                                                               │
│  4. MULTI-TOOL PRIORITY                                      │
│     └─→ RAG → Web → Crawl (intelligent prioritering)        │
│                                                               │
│  5. NATURAL SOURCE TRACKING                                  │
│     └─→ Källor följer automatiskt genom workflow            │
│                                                               │
│  6. SIMPLE ARCHITECTURE                                      │
│     └─→ Ingen separat fact-checker behövs                   │
│                                                               │
└──────────────────────────────────────────────────────────────┘

                         ↓
                         
               ┌─────────────────┐
               │  RESULTAT:      │
               │  • Inga loops   │
               │  • Bra källor   │
               │  • Snabb exec   │
               │  • User happy   │
               └─────────────────┘
```

---

## Appendix: Tool Signatures

### web_search Tool

```python
@tool
def web_search(query: str) -> str:
    """
    Search the web for information.
    
    Args:
        query: Search query string
    
    Returns:
        Formatted search results with titles, URLs, snippets
    
    Example:
        web_search("quantum computing 2024")
        
        Returns:
        [
          {
            "title": "IBM Quantum Roadmap",
            "url": "https://ibm.com/quantum",
            "snippet": "IBM announces..."
          },
          ...
        ]
    """
```

### crawl_tool Tool

```python
@tool  
def crawl_tool(url: str) -> str:
    """
    Crawl and extract content from a URL.
    
    Args:
        url: Valid URL to crawl
        
    Returns:
        Extracted text content from webpage
        
    CRITICAL: URL must come from search results.
              Never use generated URLs.
    """
```

### local_search_tool (RAG)

```python
@tool
def local_search_tool(query: str) -> str:
    """
    Search in uploaded documents using RAG.
    
    Args:
        query: Search query
        
    Returns:
        Relevant chunks from uploaded documents
        
    Priority: ALWAYS use this FIRST if available.
    """
```
