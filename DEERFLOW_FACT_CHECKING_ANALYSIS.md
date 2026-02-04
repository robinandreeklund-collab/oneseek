# DEER-FLOW Original Faktakontroll: Komplett Analys

## Executive Summary

Detta dokument innehåller en fullständig analys av hur det **ursprungliga deer-flow-projektet** (från ByteDance) hanterar faktakontroll och webbsökning i sitt "Deep Research Mode". Analysen baseras på källkoden från https://github.com/bytedance/deer-flow.

**Nyckelinsikt:** Deer-flow använder INTE en separat "fact-checker" agent. Istället är faktakontrollen **inbyggd i researcher-agenten** genom:
1. Obligatorisk web search före varje forskningsuppgift
2. Strikta instruktioner att ALDRIG generera egna URLs
3. Multi-tool approach (web_search + crawl_tool + local RAG)
4. Källor spåras genom hela processen

---

## 🏗️ Arkitektur Overview

### Huvudkomponenter

```
┌─────────────────────────────────────────────────────────────┐
│                    DEER-FLOW WORKFLOW                        │
│                                                               │
│  START → Coordinator → Background Investigation → Planner    │
│                            │                        │        │
│                            ↓                        ↓        │
│                      (Optional Web                Research   │
│                       Search)                      Team      │
│                                                     │        │
│                            ┌────────────────────────┘        │
│                            ↓                                 │
│                    ┌──────────────────┐                     │
│                    │  Research Team   │                     │
│                    │   (Supervisor)   │                     │
│                    └────────┬─────────┘                     │
│                             │                                │
│              ┌──────────────┼──────────────┐               │
│              ↓              ↓               ↓               │
│         Researcher      Analyst         Coder               │
│        (Web Search)   (Pure Reason)  (Code Exec)           │
│              │              │               │               │
│              └──────────────┼───────────────┘               │
│                             ↓                                │
│                         Reporter                             │
│                             │                                │
│                            END                               │
└─────────────────────────────────────────────────────────────┘
```

### Faktakontroll-strategi: INBYGGD I RESEARCHER

**Deer-flow har INGEN separat fact_checker node!** Istället:

```
┌─────────────────────────────────────────────────────────┐
│              RESEARCHER AGENT WORKFLOW                   │
│                                                           │
│  1. Ta emot forskningsuppgift från supervisor            │
│  2. OBLIGATORISK: Utför web_search (MÅSTE göras först)  │
│  3. Analysera sökresultat                                │
│  4. (Vid behov) Crawla specifika URLs från resultaten    │
│  5. (Vid behov) Sök i lokal RAG-databas                 │
│  6. Syntetisera information                              │
│  7. Returnera svar MED KÄLLOR SPÅRADE                    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Researcher Agent: Detaljerad Analys

### Prompt-instruktioner (researcher.md)

**KRITISKA REGLER:**

1. **Obligatorisk Web Search**
```markdown
**MANDATORY**: Always perform at least one web search using 
the **web_search** tool at the beginning of your research. 
This is not optional.
```

2. **Förbjudet att Generera URLs**
```markdown
**CRITICAL**: You MUST use the web_search tool to search 
for information. NEVER generate URLs on your own. 
All URLs must come from tool results.
```

3. **Multi-Tool Strategy**
```markdown
Available Tools:
- local_search_tool (if resources uploaded)
- web_search (ALWAYS available)
- crawl_tool (for reading URLs from search results)
- Dynamic loaded tools (MCP, specialized APIs)
```

### Verktyg och Användning

#### 1. Web Search Tool
```python
# src/graph/nodes.py (line 1389-1390)
if configurable.enable_web_search:
    tools.extend([
        get_web_search_tool(configurable.max_search_results), 
        crawl_tool
    ])
```

**Konfiguration:**
- `max_search_results`: Antal resultat per sökning (konfigurerbart)
- `enable_web_search`: Kan stängas av för pure RAG mode
- `enforce_researcher_search`: Tvingar web search även om RAG finns

#### 2. Crawl Tool
```markdown
(Optional) Use the **crawl_tool** to read content from 
necessary URLs. Only use URLs from search results or 
provided by the user.
```

**Användning:**
- Endast för URLs från sökresultat (ej genererade)
- Används när sökresultat inte ger tillräcklig detalj
- Läser full sidinnehåll för djupare analys

#### 3. Local RAG Search
```python
# src/graph/nodes.py (line 1395-1398)
retriever_tool = get_retriever_tool(state.get("resources", []))
if retriever_tool:
    tools.insert(0, retriever_tool)  # Highest priority
```

**Prioritering:**
- RAG-verktyg läggs till FÖRST i listan (högst prioritet)
- Om användare laddat upp dokument, sök där först
- Sedan komplettera med web search vid behov

---

## 🔄 Data Flow: Steg för Steg

### Scenario 1: Deep Research utan RAG

```
┌─────────────────────────────────────────────────────────────┐
│ USER: "Vad är de senaste framstegen inom kvantdatorer?"    │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│ COORDINATOR: Detektera språk (sv-SE), handoff to planner   │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│ BACKGROUND INVESTIGATION (Optional):                        │
│   - Gör snabb web_search för kontext                        │
│   - "quantum computing recent advances 2024"                │
│   - Samla bakgrundsinformation för planner                  │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│ PLANNER: Skapa forskningsplan                               │
│   Step 1: RESEARCH - "Aktuella kvantdator-framsteg 2024"   │
│   Step 2: RESEARCH - "Kvantdator företag och investeringar"│
│   Step 3: ANALYSIS - "Jämför olika kvantdator-teknologier" │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│ RESEARCH TEAM (Supervisor): Orchestrate execution           │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│ RESEARCHER (Step 1):                                         │
│   1. web_search("quantum computing advances 2024")          │
│      → [10 results with URLs]                               │
│   2. crawl_tool("https://nature.com/quantum-advance...")    │
│      → Fulltext article content                             │
│   3. Syntetisera findings                                   │
│   4. Return: "Senaste framsteg inkluderar..."              │
│      + SOURCES: [nature.com, arxiv.org, ibm.com]           │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│ RESEARCHER (Step 2):                                         │
│   1. web_search("quantum computing companies 2024")         │
│      → [10 results]                                         │
│   2. crawl_tool selected investment articles                │
│   3. Return: "Företag som IBM, Google, IonQ..."            │
│      + SOURCES: [techcrunch.com, bloomberg.com]            │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│ ANALYST (Step 3):                                            │
│   - Inga verktyg (pure reasoning)                           │
│   - Analysera info från Step 1 & 2                          │
│   - Jämför teknologier baserat på insamlad data            │
│   - Return: Komparativ analys                               │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│ REPORTER:                                                    │
│   - Sammanställ alla steg                                   │
│   - Extrahera ALLA källor från researcher responses         │
│   - Skapa final report med:                                 │
│     * Problem Statement                                      │
│     * Research Findings (organized by topic)                │
│     * Conclusion                                             │
│     * References (all URLs listed)                          │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
                 END
```

### Scenario 2: Deep Research MED RAG

```
┌─────────────────────────────────────────────────────────────┐
│ USER: "Analysera dokumenten jag laddade upp om AI-säkerhet"│
│ RESOURCES: [ai_safety_paper_1.pdf, ai_safety_paper_2.pdf]  │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│ RESEARCHER (Step 1):                                         │
│   TOOLS PRIORITET:                                          │
│   1. local_search_tool (FÖRST - RAG har högst prioritet)   │
│   2. web_search                                             │
│   3. crawl_tool                                             │
│                                                              │
│   EXECUTION:                                                │
│   1. local_search_tool("AI safety concerns")               │
│      → Hämtar relevanta chunks från PDFs                   │
│   2. web_search("AI safety 2024 latest research")          │
│      → Kompletterar med nyaste webinfo                     │
│   3. Syntetisera: Local findings + Web findings            │
│   4. Return: Komplett analys med källor från BÅDE          │
│      RAG (user docs) och web                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 Källspårning (Citation Tracking)

### Flöde för Källor

```
┌──────────────────────────────────────────────────────────┐
│             SOURCE TRACKING FLOW                          │
│                                                            │
│  web_search/crawl_tool                                    │
│         │                                                  │
│         ↓                                                  │
│  URLs stored in tool results                              │
│         │                                                  │
│         ↓                                                  │
│  Researcher mentions sources in response                  │
│  (implicit tracking via content)                          │
│         │                                                  │
│         ↓                                                  │
│  Reporter extracts citations from messages                │
│  using extract_citations_from_messages()                  │
│         │                                                  │
│         ↓                                                  │
│  Final report includes References section                 │
│  with all URLs listed                                     │
└──────────────────────────────────────────────────────────┘
```

### Citation Extraction (src/citations/)

```python
# Deer-flow använder citation-tracking system
from src.citations import (
    extract_citations_from_messages, 
    merge_citations
)

# I reporter node:
citations = extract_citations_from_messages(state["messages"])
```

**Format i final report:**
```markdown
# References

- [Nature Article on Quantum Computing](https://nature.com/quantum...)

- [IBM Quantum Roadmap 2024](https://ibm.com/quantum...)

- [ArXiv Paper: Quantum Error Correction](https://arxiv.org/...)
```

---

## ⚙️ Konfiguration och Kontroller

### Web Search Enforcement

```python
# src/graph/nodes.py
configurable.enforce_researcher_search  # Boolean flag
```

**Beteende:**
- `True`: Researcher MÅSTE göra web search även med RAG
- `False`: Researcher kan skippa web search om RAG finns

### Background Investigation

```python
# src/workflow.py (line 36)
enable_background_investigation: bool = True
```

**Funktion:**
- Gör snabb pre-search innan planner
- Ger planner mer kontext för bättre planering
- Optional, kan stängas av

### Max Search Results

```python
# Konfigurerbart per sökning
max_search_results: int  # Default varies by config
```

---

## 📊 Jämförelse: Deer-Flow vs OneSeek Current

| Aspekt | Deer-Flow (Original) | OneSeek (Före fix) | OneSeek (Efter fix) |
|--------|---------------------|-------------------|-------------------|
| **Fact-checking approach** | Inbyggd i researcher | Separat fact_checker node | Separat fact_checker node |
| **Web search timing** | FÖRE varje research task | EFTER modell-svar | Initial + on-demand |
| **Obligatorisk sökning** | Ja, MANDATORY | Nej | Nej (LLM-driven) |
| **URL-generation** | FÖRBJUDET (verktyg only) | Tillåten | Tillåten |
| **Tool call limit** | Ingen hård gräns | Ingen gräns → Loop | Max 3 calls |
| **Multi-tool strategy** | RAG → Web → Crawl | Web only | Web + RAG + Crawl |
| **Source tracking** | Genom hela processen | I fact_checker | I fact_checker |
| **Iteration control** | Task-based (per step) | Agent-loop → recursion | Tool-level limit |

### Nyckelskillnader

**Deer-Flow's Styrka:**
1. ✅ Proaktiv sökning (söker FÖRST, resonerar sedan)
2. ✅ Strikta regler (aldrig generera URLs)
3. ✅ Ingen separat fact-check node = enklare arkitektur
4. ✅ Källor spåras naturligt i researcher flow

**OneSeek's Approach:**
1. ⚠️ Reaktiv sökning (resonerar först, söker vid behov)
2. ⚠️ LLM-driven = flexibel men riskabel
3. ⚠️ Separat fact_checker = mer komplex
4. ⚠️ Krävde hard limits för att undvika loopar

---

## 💡 Rekommendationer för OneSeek

### Option 1: Adopera Deer-Flow's Approach (Enklast)

**Förslag:** Ta bort fact_checker node helt och flytta logiken till researcher/debater.

```python
# I debater/researcher node:
@tool("web_search")
def mandatory_web_search(query: str) -> str:
    """MANDATORY: Always call this first. Never generate URLs."""
    # Obligatorisk sökning
    # Strikta regler mot URL-generation
    pass
```

**Fördelar:**
- ✅ Enklare arkitektur (färre nodes)
- ✅ Naturlig källspårning
- ✅ Beprövad approach (Deer-flow fungerar perfekt)

**Nackdelar:**
- ❌ Stor omstrukturering krävs
- ❌ Förändrar current workflow betydligt

### Option 2: Hybrid Approach (Pragmatisk)

**Förslag:** Behåll fact_checker men gör den mer lik deer-flow's researcher.

```python
# I fact_checker:
1. OBLIGATORISK initial web_search på user query
2. LLM får sedan 2-3 extra searches för specifika claims
3. FÖRBJUD URL-generation explicit i prompt
4. Spåra källor strikt
```

**Implementation:**
```python
# Före agent creation:
initial_search = web_search(user_query)  # MANDATORY

# I prompt:
"Du har redan fått sökresultat. Använd dessa. 
 Om du behöver mer info, använd web_search (max 2 extra).
 ALDRIG generera egna URLs."
```

**Fördelar:**
- ✅ Minimal förändring av current code
- ✅ Behåller separat fact_checker (kan vara bra för debate mode)
- ✅ Lägger till deer-flow's strikta regler

**Nackdelar:**
- ❌ Fortfarande mer komplex än deer-flow

### Option 3: Bästa av Båda Världar

**Förslag:** Olika strategier för olika modes.

```
Deep Research Mode: 
  - Använd deer-flow's approach (inbyggd i researcher)
  - Enkel, proaktiv, beprövad

Debate Mode:
  - Behåll separat fact_checker
  - Men använd deer-flow's regler (obligatorisk search, no URL generation)
```

---

## 🎯 Konkreta Actionables

### Kortsiktigt (Quick Wins)

1. **Lägg till obligatorisk initial search**
```python
# I fact_checker_node, FÖRE agent creation:
initial_results = debate_flow.cached_web_search(user_query, current_round)
search_summaries.append(f"Obligatorisk initial sökning:\n{initial_results}")
```

2. **Förbjud URL-generation i prompt**
```python
messages.append({
    "role": "system",
    "content": (
        "**KRITISKT**: Du får ALDRIG generera egna URLs. "
        "Alla URLs måste komma från web_search verktygsresultat. "
        "Om du behöver mer info, använd web_search igen."
    )
})
```

3. **Öka tool call limit till 5 MEN med obligatorisk initial search**
```python
# 1 obligatorisk initial + 4 LLM-drivna = totalt 5
tool_call_count = {"count": 0, "max": 4}  # Exkludera initial search
```

### Medellång sikt

4. **Implementera source tracking som deer-flow**
```python
# Använd deer-flow's citation system
from backend.deer_flow.citations import extract_citations_from_messages

# I reporter/synthesizer
citations = extract_citations_from_messages(all_messages)
```

5. **Lägg till RAG-prioritering**
```python
# I fact_checker, prioritera RAG först
if debate_flow.retriever_tool:
    rag_results = await debate_flow.retriever_tool.ainvoke(user_query)
    # Använd RAG först, sedan komplettera med web
```

### Långsiktigt

6. **Överväg att förenkla till deer-flow's arkitektur**
- En researcher node istället för researcher + fact_checker
- Enklare = färre buggar
- Beprövad approach

---

## 📈 Success Metrics

För att mäta om vi närmar oss deer-flow's kvalitet:

1. **Source Quality**
   - Alla URLs från verktygsresultat (ej genererade)
   - Minst 3 källor per claim

2. **Search Efficiency**
   - 1 obligatorisk initial search + 2-3 targeted
   - Totalt 3-4 searches per fact-check (inte 100+)

3. **Zero Recursion Errors**
   - Inga GraphRecursionErrors
   - Tool calls stoppar vid limit

4. **User Satisfaction**
   - Relevanta källor
   - Snabba svar
   - Inga loops

---

## 🔗 Källkod Referenser

### Deer-Flow Original

**Key Files:**
- `src/graph/nodes.py` (line 1375-1415): Researcher node
- `src/prompts/researcher.md`: Researcher prompt med regler
- `src/graph/builder.py`: Workflow graph structure
- `src/citations/`: Citation extraction system

**Repo:** https://github.com/bytedance/deer-flow

### OneSeek Current

**Key Files:**
- `backend/deer_flow/graph/nodes.py` (line 4890+): fact_checker_node
- `backend/debate_flow.py`: Debate orchestration
- `backend/deer_flow/tools/debate_tools.py`: Debate tools

---

## 📝 Sammanfattning

**Deer-flow's hemlighet för perfekt faktakontroll:**

1. ✅ **Ingen separat fact-checker** - Inbyggt i researcher
2. ✅ **Obligatorisk proaktiv sökning** - Alltid search först
3. ✅ **Strikta regler mot URL-generation** - Endast från verktyg
4. ✅ **Multi-tool strategy** - RAG → Web → Crawl
5. ✅ **Naturlig källspårning** - Genom hela processen
6. ✅ **Task-based iteration** - En uppgift i taget, ingen agent-loop

**Nyckel-insight:**
> Deer-flow löser faktakontroll genom att göra varje forskningsuppgift 
> inneboende faktabaserad (web search först, aldrig gissa). Ingen 
> separat "fact-checker" behövs eftersom all research ÄR fact-checking.

**Rekommendation för OneSeek:**
> Kort sikt: Lägg till obligatorisk initial search + förbjud URL-generation
> Lång sikt: Överväg att förenkla till deer-flow's arkitektur för debate mode
