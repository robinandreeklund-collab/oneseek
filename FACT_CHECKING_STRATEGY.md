# Faktakontroll-strategi i Debattläge

## Nuvarande Approach (Efter Förenkling)

Faktakontrollen är nu **100% LLM-driven** - modellen bestämmer själv vad som behöver verifieras och när.

### Hur Det Fungerar

**Steg 1: Initial Kontext (Automatisk)**
- Bred webbsökning på användarens originalfråga
- RAG-hämtning från uppladdade dokument (om tillgängligt)
- Resultaten ges till fact_checker som startkontext

**Steg 2: LLM Analys och Verifiering (Intelligent)**
- LLM:en får tydliga instruktioner:
  ```
  1. Analysera svaren från de externa AI-modellerna
  2. Identifiera påståenden som behöver verifieras
  3. Använd web_search verktyget för viktiga påståenden
  4. Prioritera konkreta, verifierbara påståenden som är centrala
  ```

- LLM:en har tillgång till verktyg:
  - `web_search` - Söka efter verifieringsinformation
  - `crawl` - Läsa specifika webbsidor

- LLM:en bestämmer SJÄLV:
  - Vilka påståenden som är viktiga
  - Hur många sökningar som behövs (max 5 per runda)
  - Vilka söktermer som ska användas
  - När crawling behövs

### Fördelar med LLM-driven Approach

✅ **Smartare prioritering** - Modellen förstår kontext och relevans bättre än regex
✅ **Flexibel** - Anpassar sig efter situation och behov
✅ **Enklare kod** - Ingen komplex regelbaserad logik
✅ **Mindre overhead** - Gör bara sökningar som verkligen behövs
✅ **Bättre användarupplevelse** - Ingen förvirrande "automatisk extraktion"

### Jämförelse med Tidigare Implementation

| Aspekt | Tidigare (Hybrid) | Nu (LLM-driven) |
|--------|------------------|-----------------|
| **Påstående-identifiering** | Regex + Keywords | LLM analys |
| **Pre-sökning** | 2 automatiska på claims | Ingen |
| **Sökningar totalt** | 1 query + 2 claims = 3 | 1 query + upp till 4 LLM-drivna = 5 |
| **Flexibilitet** | Fast: alltid 2 claims | Dynamisk: 0-4 beroende på behov |
| **Komplexitet** | Hög (kod + LLM) | Låg (endast LLM) |

## Teknisk Implementation

### Faktakontroll-noden (fact_checker_node)

```python
# Steg 1: Ge initial kontext
search_summaries = []
search_summaries.append(f"Huvudsökning på originalfråga:\n{results}")
if rag_results:
    rag_summary = f"RAG-dokument ({len(items)} källor):\n..."

# Steg 2: Ge LLM verktyg och instruktioner
tools = [fact_check_web_search, fact_check_crawl]

messages.append({
    "role": "system",
    "content": (
        "Du har tillgång till web_search och crawl verktyg.\n"
        "Analysera svaren och använd verktygen för att verifiera viktiga påståenden.\n"
        "Du bestämmer själv vilka påståenden som är viktigast att kontrollera."
    ),
})

# LLM:en kör med full autonomi
fact_checker_agent = create_agent("fact_checker", tools, ...)
result = await fact_checker_agent.ainvoke(state, config)
```

### Sökgränser

- `DEBATE_WEB_SEARCH_MAX_CALLS`: **5 sökningar per runda**
  - 1 initial query-sökning (automatisk)
  - 4 tillgängliga för LLM att använda efter behov

### Exempel på LLM Beteende

**Scenario 1: Få oklara påståenden**
- LLM identifierar inga påståenden som behöver extra verifiering
- Använder 0 extra sökningar
- Baserar verifiering på initial kontext

**Scenario 2: Ett kritiskt påstående**
- LLM identifierar "Sverige har 12% förnybar energi"
- Gör 1 sökning: "Sweden renewable energy percentage 2024"
- Verifierar och rapporterar

**Scenario 3: Flera viktiga påståenden**
- LLM identifierar 3 statistiska påståenden
- Gör 3 sökningar för de viktigaste
- Prioriterar baserat på relevans och trovärdighet

**Scenario 4: Behöver djupdykning**
- LLM hittar studie-referens som verkar viktig
- Gör sökning på studien
- Använder `crawl` för att läsa original-källan
- Totalt 2 verktygsanrop för ett påstående

## Designbeslut

### Varför Ta Bort Kod-baserad Extraktion?

1. **Regex är för generisk**
   - Matchar nyckelord som "studie", "enligt", "%" etc.
   - Men många träffar är irrelevanta eller självklara
   - Skapar "noise" istället för signal

2. **LLM är smartare**
   - Förstår semantisk betydelse
   - Kan bedöma vad som är kontroversiellt
   - Vet vad som faktiskt behöver verifieras

3. **Eliminerar dubbelt arbete**
   - Tidigare: Kod extraherar → Pre-söker → LLM analyserar
   - Nu: LLM analyserar och söker direkt
   - Färre steg = snabbare och enklare

4. **Bättre resursanvändning**
   - Slösar inte sökningar på självklara saker
   - Fokuserar på vad som verkligen spelar roll
   - Kan använda fler sökningar när det behövs (5 vs 3)

### Varför Behålla Initial Query-sökning?

- Ger bred kontext direkt
- Täcker många vanliga verifieringsbehov
- LLM kan fokusera på gap och specifika påståenden
- Snabbare än att låta LLM först analysera och sedan söka basic info

## Framtida Förbättringar

Möjliga optimeringar (ej implementerade):

1. **Dynamisk sökgräns** - Justera max_calls baserat på komplexitet
2. **Caching av LLM decisions** - Undvik samma analys i flera rundor
3. **Confidence scores** - LLM anger hur säker den är på verifieringar
4. **Multi-step verification** - LLM kan bygga kedjor av verifieringar
5. **Source quality ranking** - LLM bedömer källors trovärdighet

## Sammanfattning

**Förr:** Kod filtrerar påståenden → Pre-söker 2 claims → LLM får resultaten + kan söka mer

**Nu:** Initial query-sökning + RAG → LLM analyserar, identifierar och söker på egen hand

Detta är enklare, smartare och ger modellen full kontroll över faktakontroll-processen.
