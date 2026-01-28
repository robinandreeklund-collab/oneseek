# Debate Context Flow Analysis

**Författare:** AI Assistant  
**Datum:** 2026-01-28  
**Problem:** VLLM kraschar efter recent cursor commits - misstänkt kontextexplosion

---

## Sammanfattning

Debatten implementering i OneSeek skapar en **kraftig kontextaccumulation** som sannolikt överskrider VLLM's kapacitet. Analysen visar att kontexten kan växa från ~500 tokens i början till **över 50,000+ tokens** i runda 3, särskilt när voting sker.

**KRITISKT PROBLEM:** Varje modells svar läggs till i `chain_so_far`, och vid runda 2 och 3 får **alla modeller hela föregående rundan + nuvarande kedjan**. Detta skapar en exponentiell kontexttillväxt.

---

## Detaljerad Flödesanalys

### 1. Initialisering och Runda 1

#### Start av Debatt
```
Användare → Coordinator → Planner (debate_planner prompt) → Human Feedback → Researcher (debate tools)
```

**Debut Context (Runda 1, Första modellen):**
```
Kontext = Användarfråga (~50-100 tokens) + Instruktioner (~200 tokens)
Total: ~300 tokens
```

#### Runda 1 Progression (5 modeller)
För varje modell efter den första:
```
Kontext = Användarfråga + chain_so_far (alla tidigare svar i denna runda)

Modell 1: 300 tokens (query + instructions)
Modell 2: 300 + 500 = 800 tokens (+ modell 1's svar)
Modell 3: 300 + 1000 = 1,300 tokens (+ modell 1-2)
Modell 4: 300 + 1500 = 1,800 tokens (+ modell 1-3)
Modell 5: 300 + 2000 = 2,300 tokens (+ modell 1-4)
```

**Estimerat efter Runda 1:** ~2,500 tokens i `full_previous_round`

---

### 2. Runda 2 - Första Kontextexplosionen

#### Kontextbyggnad för Runda 2
```python
# Från debate_flow.py, rad 290-300
if self.full_previous_round:
    context_parts.append(f"\nKomplett Runda {prev_round}:\n")
    for resp in self.full_previous_round:
        context_parts.append(f"\n{resp['display_name']}: {resp['response']}\n")

if self.chain_so_far:
    context_parts.append(f"\nRunda {self.current_round} hittills:\n")
    for resp in self.chain_so_far:
        context_parts.append(f"\n{resp['display_name']}: {resp['response']}\n")
```

**Runda 2 Kontext per Modell:**
```
Modell 1: Query (100) + full_previous_round (2,500) = 2,600 tokens
Modell 2: Query + Runda 1 (2,500) + chain_so_far (500) = 3,100 tokens
Modell 3: Query + Runda 1 (2,500) + chain_so_far (1,000) = 3,600 tokens
Modell 4: Query + Runda 1 (2,500) + chain_so_far (1,500) = 4,100 tokens
Modell 5: Query + Runda 1 (2,500) + chain_so_far (2,000) = 4,600 tokens
```

**Estimerat efter Runda 2:** ~5,000 tokens i ny `full_previous_round`

---

### 3. Runda 3 - Kritisk Kontextexplosion

**Runda 3 Kontext per Modell:**
```
Modell 1: Query (100) + Runda 2 (5,000) = 5,100 tokens
Modell 2: Query + Runda 2 (5,000) + chain_so_far (500) = 5,600 tokens
Modell 3: Query + Runda 2 (5,000) + chain_so_far (1,000) = 6,100 tokens
Modell 4: Query + Runda 2 (5,000) + chain_so_far (1,500) = 6,600 tokens
Modell 5: Query + Runda 2 (5,000) + chain_so_far (2,000) = 7,100 tokens
```

**Special för OneSeek (om det är modell 5):**
```python
# Från debate_flow.py, rad 267-271
if self.facts and model_key == "oneseek-local":
    context_parts.append("\n**Verifierade Fakta (från webbsökning):**\n")
    for fact in self.facts[-5:]:
        context_parts.append(f"- {fact['content']} (Källa: {fact['source']})\n")
```

**OneSeek får YTTERLIGARE:**
- Verifierade fakta: ~1,000 tokens
- Internal analysis resultat (implicit i minne): ~2,000 tokens

**Total för OneSeek i Runda 3:** ~10,000+ tokens

---

### 4. Voting - MASSIV Kontextexplosion

Detta är troligen där VLLM kraschar!

#### Voting Context Building
```python
# Från debate_flow.py, rad 475-485
voting_context = f"Fråga: {user_query}\n\nRunda 3 svar:\n"
for idx, resp in enumerate(round_3_responses):
    if not resp.get("error"):
        response_text = resp['response']
        if len(response_text) > 1000:
            response_text = response_text[:1000] + "... [trunkerat]"
        voting_context += f"\n[{idx}] {resp['display_name']}: {response_text}\n"
```

**Voting Prompt per Modell:**
```
Base: Query (100) + "Runda 3 svar:" header (50)
Modell 1 svar: 1,000 tokens (trunkerat från möjligen 2,000)
Modell 2 svar: 1,000 tokens
Modell 3 svar: 1,000 tokens
Modell 4 svar: 1,000 tokens
Modell 5 svar: 1,000 tokens
Instruktioner: 200 tokens

Total per voting call: ~5,300 tokens
```

**PROBLEM:** Även med truncation till 1,000 tokens per svar är voting context fortfarande ~5,300 tokens, och detta skickas till **varje modell** (5 anrop).

---

### 5. Internal Analysis - Parallella Anrop?

#### run_oneseek_internal_analysis
```python
# Från debate_flow.py, rad 422-443
if self.search_tool and len(resp["response"]) > 100:
    claim = resp["response"][:200]
    search_query = f"{user_query} {claim}"
    
    search_results = await asyncio.wait_for(
        asyncio.to_thread(self.search_tool.invoke, search_query),
        timeout=5.0
    )
```

**Problem:** Detta anropas efter **varje modellsvar**, vilket kan innebära:
- 5 anrop i Runda 1
- 5 anrop i Runda 2  
- 5 anrop i Runda 3
- **Totalt 15 web search anrop**

Men dessa är sekventiella (efter varje modell), inte parallella. Dock, om flera debatter körs samtidigt eller om LLM själv gör parallella tool calls internt, kan detta skapa memory pressure.

---

## Kontextackumulation Sammanfattning

| Steg | Kontext per Anrop | Antal Anrop | Total Kontext Genererad |
|------|------------------|-------------|-------------------------|
| Runda 1 | 300 - 2,300 tokens | 5 modeller | ~2,500 tokens sparade |
| Runda 2 | 2,600 - 4,600 tokens | 5 modeller | ~5,000 tokens sparade |
| Runda 3 | 5,100 - 10,000 tokens | 5 modeller | ~7,500 tokens sparade |
| Voting | 5,300 tokens | 5 modeller | ~26,500 tokens (totalt skickat) |
| **TOTAL** | - | **20 anrop** | **~41,500 tokens processade** |

**Kritiska Observationer:**
1. **Exponentiell tillväxt:** Kontexten fördubblas nästan varje runda
2. **Voting är värst:** Skickar ~5,300 tokens till varje modell (5x)
3. **OneSeek får mest:** Extra fakta + analysis i minnet
4. **Ingen context cleanup:** Gamla rundor sparas i sitt helhet

---

## VLLM Crash Analys

### Troliga Orsaker

#### 1. **Context Length Överskridande**
VLLM modeller har vanligtvis context windows på:
- Qwen2.5-14B-Instruct: **32,768 tokens** (32K context)
- Men med AWQ quantization kan effektiv context vara **lägre**

**Vår peak usage:**
- Runda 3, sista modellen: ~10,000 tokens input
- Voting: 5,300 tokens × 5 anrop = ~26,500 tokens total
- **Potentiellt över 32K om modellen genererar långa svar**

#### 2. **Memory Pressure från Parallella Anrop**
Även om tool calls är sekventiella, kan flera chattsessioner köra samtidigt, vardera med sin debatt:
```
Session 1: Runda 3 voting (5 anrop × 5,300 tokens) = 26,500 tokens i minnet
Session 2: Runda 3 voting (5 anrop × 5,300 tokens) = 26,500 tokens i minnet
Session 3: Runda 2 (5 anrop × 4,000 tokens avg) = 20,000 tokens i minnet

Total VLLM memory load: ~73,000 tokens samtidigt
```

Med KV cache och activation memory kan detta lätt överskrida GPU memory.

#### 3. **Reporter Node Summarization (Redan Fixad)**
Commit 8eea39e fixade detta:
```
"Fix debate report generation: Bypass LLM summarization in reporter_node to prevent context overflow"
```

**Före fix:** Reporter fick hela debate history och försökte summera med LLM
**Efter fix:** Reporter returnerar debate_results direkt utan LLM-anrop

Detta var bra! Men det räcker inte för att lösa problemet i tidigare steg.

---

## Identifierade Problem

### 🔴 KRITISKA (Måste Fixas)

#### Problem 1: Voting Context är För Stor
**Beskrivning:** Varje modell får ALL of round 3's svar (5 × 1,000 tokens) = 5,300 tokens

**Lösning:**
```python
# I debate_flow.py, collect_votes()
# Istället för att skicka alla svar, skicka endast:
# 1. Sammanfattningar (100 tokens vardera)
# 2. Eller använd en "voting coordinator" LLM som läser allt och ber om röster
```

**Implementationsförslag:**
```python
async def collect_votes(self, user_query: str, round_3_responses: List[Dict]) -> Dict:
    # OPTION A: Summarize each response först
    summaries = []
    for resp in round_3_responses:
        summary = resp['response'][:200] + "..."  # Ännu mer aggressiv truncation
        summaries.append(summary)
    
    # OPTION B: Använd en separat "voting coordinator" approach
    # Istället för att fråga varje modell, använd ONE local LLM call:
    # "Based on these 5 responses (summaries), which is best? Vote."
```

#### Problem 2: Runda 2 & 3 Får Hela Föregående Rundan
**Beskrivning:** `full_previous_round` innehåller alla svar från föregående runda oförändrade

**Lösning:** Använd sammanfattningar istället för fulltext
```python
def build_context_for_model(self, model_key: str, user_query: str, locale: str) -> str:
    # BEFORE: Include full previous round
    # AFTER: Include summarized previous round
    
    if self.current_round > 1 and self.full_previous_round:
        # Generate summary of previous round (NOT full text)
        prev_summary = self._summarize_round(self.full_previous_round)
        context_parts.append(f"\n**Sammanfattning av Runda {self.current_round - 1}:**\n")
        context_parts.append(prev_summary)
```

**Summarization Strategy:**
- Använd en separat "summarizer" LLM call (light-weight)
- Eller: Hårdkodad logik som tar första 200 tokens från varje svar
- Target: Reducera 2,500 tokens → 500 tokens (80% reduction)

#### Problem 3: chain_so_far Växer Olinjärt
**Beskrivning:** Varje modell i samma runda får **alla tidigare svar i den rundan**

**Lösning:** Begränsa `chain_so_far` till senaste N svar
```python
# I build_context_for_model()
if self.chain_so_far:
    # BEFORE: Visa alla svar i nuvarande runda
    # AFTER: Visa endast senaste 2-3 svar
    recent_responses = self.chain_so_far[-3:]  # Max 3 senaste
    context_parts.append(f"\nSenaste svar i runda {self.current_round}:\n")
    for resp in recent_responses:
        context_parts.append(f"{resp['display_name']}: {resp['response'][:300]}...\n")
```

### 🟡 VIKTIGA (Bör Fixas)

#### Problem 4: facts Array Kan Växa Okontrollerat
**Beskrivning:** `self.facts` appendas efter varje `debater_web_search`, ingen begränsning

**Nuvarande kod:**
```python
# debate_flow.py, rad 221-228
def add_fact(self, fact: str, source: str = "web_search"):
    self.facts.append({"content": fact, "source": source, "round": self.current_round})
```

**Problem:** Om 15 web searches görs (5 per runda × 3 rundor), kan `facts` bli >15,000 tokens

**Lösning:**
```python
def add_fact(self, fact: str, source: str = "web_search"):
    # Truncate fact content
    if len(fact) > 500:
        fact = fact[:500] + "..."
    
    self.facts.append({
        "content": fact, 
        "source": source, 
        "round": self.current_round
    })
    
    # Keep only last 10 facts
    if len(self.facts) > 10:
        self.facts = self.facts[-10:]
```

#### Problem 5: Internal Analysis Resultat Sparas Men Används Sällan
**Beskrivning:** `oneseek_analyses` växer med varje `run_oneseek_internal_analysis` call (potentiellt 15)

**Nuvarande användning:** Endast OneSeek har implicit tillgång via minne, men ingen explicit context passage

**Lösning:**
- Begränsa `oneseek_analyses` till max 5 senaste
- Eller: Summera analyser innan de läggs till OneSeek's context

### 🟢 MINDRE PRIORITET (Nice to Have)

#### Problem 6: Inga Token Count Metrics
**Beskrivning:** Vi vet inte exakt hur mycket kontext som genereras

**Lösning:** Lägg till token counting:
```python
import tiktoken

def _count_tokens(self, text: str) -> int:
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")  # Approximation
    return len(enc.encode(text))

def build_context_for_model(self, ...):
    context = "..."  # Build context
    token_count = self._count_tokens(context)
    logger.warning(f"Context for {model_key}: {token_count} tokens")
    
    if token_count > 8000:
        logger.error(f"DANGER: Context exceeds 8K tokens!")
    
    return context
```

---

## Rekommenderade Förändringar

### Prioritet 1: Omedelbar Fix (Kritisk)

#### 1.1 Begränsa Voting Context
**Fil:** `backend/debate_flow.py`, metod `collect_votes()`

```python
async def collect_votes(self, user_query: str, round_3_responses: List[Dict]) -> Dict:
    """FIXED VERSION: Reduce voting context"""
    
    # Build MINIMAL voting context
    voting_context = f"Fråga: {user_query}\n\nRunda 3 svar (sammanfattade):\n"
    
    for idx, resp in enumerate(round_3_responses):
        if not resp.get("error"):
            # Drastically truncate: 300 chars = ~75 tokens
            summary = resp['response'][:300]
            if len(resp['response']) > 300:
                summary += "... [fortsätter]"
            voting_context += f"\n[{idx}] {resp['display_name']}: {summary}\n"
    
    # Samma voting logic...
    # Target: Reduce from 5,300 → 1,500 tokens (70% reduction)
```

**Estimerad Impact:** Voting context reduceras från 5,300 → 1,500 tokens per anrop

#### 1.2 Summera Föregående Rundor
**Fil:** `backend/debate_flow.py`, ny metod + uppdatera `build_context_for_model()`

```python
def _summarize_round(self, responses: List[Dict]) -> str:
    """Summarize a round's responses"""
    summary_parts = []
    for resp in responses:
        if not resp.get("error"):
            # Take first 150 chars of each response
            snippet = resp['response'][:150]
            summary_parts.append(f"- **{resp['display_name']}**: {snippet}...")
    
    return "\n".join(summary_parts)

def build_context_for_model(self, model_key: str, user_query: str, locale: str) -> str:
    """FIXED VERSION with summarization"""
    context_parts = []
    context_parts.append(f"Användares fråga: {user_query}\n")
    
    # Round 2 & 3: Use SUMMARY instead of full previous round
    if self.current_round > 1 and self.full_previous_round:
        summary = self._summarize_round(self.full_previous_round)
        context_parts.append(f"\n**Sammanfattning Runda {self.current_round - 1}:**\n")
        context_parts.append(summary)
        context_parts.append("\n")
    
    # Limit chain_so_far to last 3 responses
    if self.chain_so_far:
        recent = self.chain_so_far[-3:]
        context_parts.append(f"\nSenaste {len(recent)} svar i denna runda:\n")
        for resp in recent:
            # Also truncate chain_so_far
            snippet = resp['response'][:300]
            context_parts.append(f"{resp['display_name']}: {snippet}...\n")
    
    # Rest of method...
```

**Estimerad Impact:**
- Runda 2 context: 4,600 → 1,800 tokens (60% reduction)
- Runda 3 context: 10,000 → 3,500 tokens (65% reduction)

#### 1.3 Begränsa facts Array
**Fil:** `backend/debate_flow.py`, metod `add_fact()`

```python
def add_fact(self, fact: str, source: str = "web_search"):
    """FIXED VERSION: Limit fact accumulation"""
    # Truncate individual facts
    if len(fact) > 500:
        fact = fact[:500] + "... [trunkerat]"
    
    self.facts.append({
        "content": fact,
        "source": source,
        "round": self.current_round
    })
    
    # Keep only last 10 facts (instead of unbounded)
    if len(self.facts) > 10:
        self.facts = self.facts[-10:]
        logger.info(f"Trimmed facts array to last 10 entries")
```

**Estimerad Impact:** facts-relaterad context reduceras från ~5,000 → ~1,000 tokens

---

### Prioritet 2: Monitoring och Säkerhet

#### 2.1 Lägg till Token Counting
**Fil:** `backend/debate_flow.py`, lägg till helper metod

```python
import tiktoken

class DebateFlow:
    def __init__(self, ...):
        # ...
        self.token_encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.token_encoder.encode(text))
        except:
            # Fallback: 1 token ≈ 4 chars
            return len(text) // 4
    
    def build_context_for_model(self, ...):
        context = "\n".join(context_parts)
        
        # COUNT AND LOG
        token_count = self._count_tokens(context)
        logger.info(f"Context for {model_key} in round {self.current_round}: {token_count} tokens")
        
        if token_count > 10000:
            logger.error(f"⚠️ CRITICAL: Context exceeds 10K tokens! Model may fail!")
        elif token_count > 5000:
            logger.warning(f"⚠️ WARNING: Context exceeds 5K tokens")
        
        return context
```

#### 2.2 Context Size Guards
**Fil:** `backend/debate_flow.py`, lägg till guards

```python
async def query_model_in_debate(self, model_key: str, user_query: str, locale: str) -> Dict:
    """GUARDED VERSION"""
    context = self.build_context_for_model(model_key, user_query, locale)
    token_count = self._count_tokens(context)
    
    # HARD LIMIT: Refuse to send if context > 15K tokens
    if token_count > 15000:
        logger.error(f"Context too large ({token_count} tokens), skipping {model_key}")
        return {
            "model": model_key,
            "display_name": DEBATE_MODELS.get(model_key, {}).get("display_name", model_key),
            "response": f"❌ Skipped due to context size ({token_count} tokens exceeds limit)",
            "error": True,
            "context_used": "Context too large"
        }
    
    # Proceed with model query...
```

---

### Prioritet 3: Långsiktig Optimering

#### 3.1 Använd Streaming Summarization
Istället för att spara hela svar, summera i realtid:

```python
async def query_model_in_debate(self, ...):
    # Get full response
    response = await model.ainvoke(messages)
    response_text = response.content
    
    # Store both full and summary
    summary = response_text[:300] + "..." if len(response_text) > 300 else response_text
    
    result = {
        "model": model_key,
        "display_name": display_name,
        "response": response_text,  # Full for current usage
        "summary": summary,  # For future rounds
        ...
    }
    
    self.chain_so_far.append(result)
```

Sedan i `build_context_for_model`, använd `summary` istället för `response` för äldre rundor.

#### 3.2 Separata Context Strategies per Modell Type
OneSeek (local) behöver mer kontext än externa modeller:

```python
def build_context_for_model(self, model_key: str, ...):
    is_oneseek = model_key == "oneseek-local"
    
    if is_oneseek:
        # OneSeek gets more context (up to 12K tokens)
        max_context = 12000
    else:
        # External models get less (up to 5K tokens)
        max_context = 5000
    
    # Build context and trim if needed
    context = self._build_full_context(...)
    token_count = self._count_tokens(context)
    
    if token_count > max_context:
        context = self._trim_context_to_fit(context, max_context)
```

---

## Sammanfattade Estimat: Före och Efter Fix

| Komponent | Före (tokens) | Efter (tokens) | Reduktion |
|-----------|--------------|----------------|-----------|
| Runda 1 (sista modellen) | 2,300 | 2,300 | 0% (OK) |
| Runda 2 (sista modellen) | 4,600 | 1,800 | 61% ✅ |
| Runda 3 (sista modellen) | 10,000 | 3,500 | 65% ✅ |
| Voting (per anrop) | 5,300 | 1,500 | 72% ✅ |
| Voting (totalt 5 anrop) | 26,500 | 7,500 | 72% ✅ |
| **Peak Single Context** | **10,000** | **3,500** | **65% ✅** |
| **Total Processed** | **41,500** | **16,100** | **61% ✅** |

**Resultat:** Med dessa fixes reduceras total kontextanvändning med ~60%, vilket bör eliminera VLLM crashes.

---

## Implementation Roadmap

### Fas 1: Kritiska Fixes (Gör Nu) ⚡
**Tid:** 2-3 timmar  
**Filer att ändra:**
- `backend/debate_flow.py`
  - `collect_votes()` - Reducera voting context
  - `build_context_for_model()` - Summera föregående rundor
  - `add_fact()` - Begränsa facts array

**Test:** 
1. Kör en full debatt med 5 modeller
2. Verifiera att VLLM inte kraschar
3. Kontrollera att logs visar lägre token counts

### Fas 2: Monitoring (Denna Vecka) 📊
**Tid:** 1-2 timmar  
**Filer att ändra:**
- `backend/debate_flow.py`
  - Lägg till `_count_tokens()` metod
  - Lägg till logging av token counts
  - Lägg till context size guards

**Test:**
1. Kör debatt och granska logs
2. Verifiera att warnings visas vid >5K tokens
3. Verifiera att errors visas vid >10K tokens

### Fas 3: Långsiktig Optimering (Nästa Sprint) 🔄
**Tid:** 4-6 timmar  
**Förbättringar:**
- Streaming summarization
- Per-model context strategies
- Smart context trimming algorithm

---

## Slutsats

**Diagnos:** Debatten implementering skapar exponentiell kontexttillväxt som överskrider VLLM's kapacitet, särskilt i Runda 3 och Voting.

**Root Cause:**
1. Hela föregående rundor kopieras in i varje ny runda
2. `chain_so_far` växer linjärt inom varje runda
3. Voting skickar ~5K tokens till varje modell (5x)

**Lösning:** Implementera de 3 kritiska fixarna:
1. Reducera voting context (72% reduktion)
2. Summera föregående rundor (65% reduktion)
3. Begränsa facts array (80% reduktion)

**Estimerad Impact:** Total kontextanvändning reduceras från 41,500 → 16,100 tokens (61% reduktion), vilket bör eliminera VLLM crashes.

**Nästa Steg:** Implementera Fas 1 fixes omedelbart.

---

## Appendix: Kodexempel för Fullständig Fix

Se nedan för komplett implementationsexempel:

```python
# backend/debate_flow.py - FIXED VERSION

class DebateFlow:
    def __init__(self, max_search_results: int = 3, resources: List[Any] = None):
        # ... existing init ...
        
        # NEW: Add token encoder
        try:
            import tiktoken
            self.token_encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except:
            self.token_encoder = None
            logger.warning("tiktoken not available, using character-based estimation")
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.token_encoder:
            try:
                return len(self.token_encoder.encode(text))
            except:
                pass
        # Fallback: 1 token ≈ 4 chars
        return len(text) // 4
    
    def _summarize_round(self, responses: List[Dict]) -> str:
        """Summarize a round's responses to reduce context"""
        summary_parts = []
        for resp in responses:
            if not resp.get("error"):
                # Take first 150 chars (~40 tokens) of each response
                snippet = resp['response'][:150]
                if len(resp['response']) > 150:
                    snippet += "..."
                summary_parts.append(f"- **{resp['display_name']}**: {snippet}")
        
        return "\n".join(summary_parts)
    
    def add_fact(self, fact: str, source: str = "web_search"):
        """Add fact with size limits - FIXED VERSION"""
        # Truncate individual facts to 500 chars
        if len(fact) > 500:
            fact = fact[:500] + "... [trunkerat för kontext]"
        
        self.facts.append({
            "content": fact,
            "source": source,
            "round": self.current_round
        })
        
        # Keep only last 10 facts
        if len(self.facts) > 10:
            self.facts = self.facts[-10:]
            logger.info(f"Trimmed facts array to last 10 entries")
    
    def build_context_for_model(
        self, 
        model_key: str, 
        user_query: str, 
        locale: str = "sv-SE"
    ) -> str:
        """Build context with size limits - FIXED VERSION"""
        language = "svenska" if locale.startswith("sv") else "engelska"
        context_parts = []
        
        # Add user query
        context_parts.append(f"Användares fråga: {user_query}\n")
        
        # Add facts ONLY for OneSeek, and limit to last 5
        if self.facts and model_key == "oneseek-local":
            context_parts.append("\n**Verifierade Fakta (senaste 5):**\n")
            for fact in self.facts[-5:]:
                context_parts.append(f"- {fact['content']}\n")
        
        # Add instruction to include name
        context_parts.append(f"\nVIKTIGT: Inled ditt svar med: **{model_key}**\n")
        
        # Round 1: Minimal context for first, chain_so_far for others
        if self.current_round == 1:
            if not self.chain_so_far:
                context_parts.append(f"Debatt runda 1. Du är först. Svara på {language}, max 500 tokens.\n")
            else:
                # Limit to last 3 responses in chain
                recent = self.chain_so_far[-3:]
                context_parts.append(f"\nRunda 1, senaste {len(recent)} svar:\n")
                for resp in recent:
                    # Truncate to 300 chars
                    snippet = resp['response'][:300]
                    if len(resp['response']) > 300:
                        snippet += "..."
                    context_parts.append(f"{resp['display_name']}: {snippet}\n")
        
        # Round 2 & 3: Use SUMMARY of previous round + limited chain_so_far
        else:
            if self.full_previous_round:
                # CHANGED: Use summary instead of full text
                summary = self._summarize_round(self.full_previous_round)
                context_parts.append(f"\n**Sammanfattning Runda {self.current_round - 1}:**\n")
                context_parts.append(summary)
                context_parts.append("\n")
            
            if self.chain_so_far:
                # Limit to last 3 responses
                recent = self.chain_so_far[-3:]
                context_parts.append(f"\nRunda {self.current_round}, senaste {len(recent)} svar:\n")
                for resp in recent:
                    snippet = resp['response'][:300]
                    if len(resp['response']) > 300:
                        snippet += "..."
                    context_parts.append(f"{resp['display_name']}: {snippet}\n")
            
            # Round 3 OneSeek synthesis instructions
            if self.current_round == 3 and model_key == "oneseek-local":
                context_parts.append("\nRunda 3: Skapa ditt bästa syntetiserade svar.\n")
        
        context = "\n".join(context_parts)
        
        # NEW: Log token count
        token_count = self._count_tokens(context)
        logger.info(f"Context for {model_key} round {self.current_round}: {token_count} tokens")
        
        if token_count > 10000:
            logger.error(f"⚠️ CRITICAL: Context {token_count} tokens exceeds 10K!")
        elif token_count > 5000:
            logger.warning(f"⚠️ Context {token_count} tokens exceeds 5K")
        
        return context
    
    async def query_model_in_debate(self, model_key: str, user_query: str, locale: str = "sv-SE") -> Dict:
        """Query model with context size guard - FIXED VERSION"""
        if model_key not in self.models:
            # ... existing error handling ...
        
        try:
            model = self.models[model_key]
            display_name = DEBATE_MODELS.get(model_key, {}).get("display_name", model_key)
            
            # Build context
            context = self.build_context_for_model(model_key, user_query, locale)
            token_count = self._count_tokens(context)
            
            # NEW: Hard limit guard
            if token_count > 15000:
                logger.error(f"Context too large ({token_count} tokens), skipping {model_key}")
                return {
                    "model": model_key,
                    "display_name": display_name,
                    "response": f"❌ Skipped: Context size {token_count} tokens exceeds 15K limit",
                    "error": True,
                    "context_used": "Exceeded context limit"
                }
            
            # Query the model
            logger.info(f"Querying {display_name} in round {self.current_round}")
            messages = [HumanMessage(content=context)]
            response = await model.ainvoke(messages)
            
            response_text = response.content if hasattr(response, "content") else str(response)
            
            # Enforce 500 token limit (~2000 chars)
            if len(response_text) > 2000:
                response_text = response_text[:2000] + "... [trunkerat]"
            
            result = {
                "model": model_key,
                "display_name": display_name,
                "response": response_text,
                "round": self.current_round,
                "position": len(self.chain_so_far),
                "error": False,
                "context_used": context  # Full context for debugging
            }
            
            self.chain_so_far.append(result)
            logger.info(f"{display_name} responded ({len(response_text)} chars)")
            
            return result
            
        except Exception as e:
            # ... existing error handling ...
    
    async def collect_votes(self, user_query: str, round_3_responses: List[Dict]) -> Dict:
        """Collect votes with reduced context - FIXED VERSION"""
        logger.info("Collecting votes from external models")
        
        votes = {}
        vote_details = []
        
        # Build MINIMAL voting context
        voting_context = f"Fråga: {user_query}\n\nRunda 3 svar (sammanfattade):\n"
        
        for idx, resp in enumerate(round_3_responses):
            if not resp.get("error"):
                # CHANGED: Drastically reduce to 300 chars (~75 tokens)
                summary = resp['response'][:300]
                if len(resp['response']) > 300:
                    summary += "... [fortsätter]"
                voting_context += f"\n[{idx}] {resp['display_name']}: {summary}\n"
        
        voting_context += "\n\nRösta på bästa svaret [0-" + str(len(round_3_responses)-1) + "]. "
        voting_context += "Du får INTE rösta på dig själv. Ge endast nummer."
        
        # Log voting context size
        token_count = self._count_tokens(voting_context)
        logger.info(f"Voting context: {token_count} tokens (target: <2000)")
        
        # ... rest of voting logic unchanged ...
        
        return {
            "votes": votes,
            "vote_details": vote_details,
            "winner": winner,
            "winner_votes": max_votes,
            "total_voters": len(vote_details),
            "voting_prompt": voting_context
        }
```

**END OF DOCUMENT**
