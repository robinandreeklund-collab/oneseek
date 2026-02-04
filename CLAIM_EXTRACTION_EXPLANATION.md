# Hur Påståenden Extraheras för Faktakontroll

## Svar på Frågan

**Påståenden extraheras med en HYBRID-STRATEGI:**

1. **Automatisk extraktion med kod** (initial filtrering)
2. **LLM:en kan sedan välja att söka mer** (dynamisk verifiering)

## Detaljerad Förklaring

### 🤖 Automatisk Extraktion (Kod-baserad)

I `backend/deer_flow/graph/nodes.py` finns funktionen `extract_claim_sentences()` (rad 751-765):

```python
def extract_claim_sentences(text: str, max_claims: int = 8) -> list[str]:
    """Extract claim-like sentences for controlled fact checking."""
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    claims = []
    for sentence in sentences:
        cleaned = sentence.strip()
        if len(cleaned) < 20:
            continue
        # Filtrera på nyckelord och nummer
        if any(token in cleaned.lower() for token in 
               ["%", "år", "year", "miljoner", "million", "billion", 
                "studie", "rapport", "enligt", "according", "fakta", "data"]) \
           or re.search(r"\d", cleaned):
            claims.append(cleaned)
        if len(claims) >= max_claims:
            break
    return claims
```

**Hur det fungerar:**
- Delar upp text i meningar (vid `.`, `!`, `?`)
- Filtrerar bort meningar kortare än 20 tecken
- Letar efter "påstående-signaler":
  - **Nyckelord**: %, år, year, miljoner, million, billion, studie, rapport, enligt, according, fakta, data
  - **Nummer**: Vilket heltal som helst
- Returnerar max 8 påståenden (eller enligt `max_claims` parameter)

### 🧠 LLM:ens Roll (Dynamisk Sökning)

Efter att kod-baserade påståenden extraherats, får fact_checker LLM:en:

1. **De automatiskt extraherade påståendena** (som kontext)
2. **Sökresultat** (både på originalfrågan och utvalda påståenden)
3. **Verktygsaccess** (`web_search` och `crawl`)

Från rad 5002-5010 i `nodes.py`:
```python
if claims:
    claims_text = "\n".join(f"- {claim}" for claim in claims[:max_claims])
    messages.append({
        "role": "system",
        "content": (
            "Identifierade påståenden att verifiera:\n\n"
            f"{claims_text}\n\n"
            "Du kan använda web_search verktyget för ytterligare verifiering vid behov."
        ),
    })
```

**LLM:en kan:**
- Välja vilka påståenden som är viktigast att verifiera
- Göra ytterligare sökningar via `web_search` verktyget
- Crawla specifika URLs via `crawl` verktyget
- Ignorera irrelevanta påståenden

## Skillnader mellan Debattläge och AI-Jämförelse

### Debattläge (debate_flow)
- ✅ Använder `extract_claim_sentences()` för initial filtrering
- ✅ Gör hybrid-sökning: originalfråga + 2 kritiska påståenden
- ✅ LLM får verktyg för dynamisk sökning
- ✅ Pre-söker på utvalda påståenden

### AI-Jämförelse (ai_comparison_flow)
- ❌ Använder INTE `extract_claim_sentences()`
- ✅ Gör bred sökning endast på originalfrågan
- ✅ LLM får alla sökresultat som kontext
- ⚠️ Mindre strukturerad påstående-identifiering

## Hybrid-Strategin i Debattläge (Nuvarande Implementation)

**Steg 1: Pre-sökning med kod**
```python
# Step 3: Targeted claim search for critical claims only
claims = extract_claim_sentences(state.get("external_ai_responses", ""))
max_claims = int(os.getenv("DEBATE_FACT_CHECK_MAX_CLAIMS", "2"))

for claim in claims[:max_claims]:
    results = debate_flow.cached_web_search(claim, current_round)
    search_summaries.append(f"Kritiskt påstående: {claim}\n{formatted}")
```

**Steg 2: LLM får verktyg**
```python
@tool("web_search")
def fact_check_web_search(query: str) -> str:
    """Search the web for fact verification."""
    # LLM:en kan anropa detta för mer verifiering
```

**Steg 3: LLM analyserar**
- LLM:en får alla pre-sökta resultat
- LLM:en ser lista på identifierade påståenden
- LLM:en kan välja att söka mer via verktyg

## Sammanfattning

**Påståendeextraktion = KOD + LLM**

1. **Kod** (`extract_claim_sentences`):
   - Initial automatisk filtrering
   - Regelbaserad (keywords + nummer)
   - Snabb och förutsägbar
   - Max 2-8 påståenden (konfigurerbart)

2. **LLM** (fact_checker agent):
   - Får de förfiltrerade påståendena
   - Kan välja vilka som är viktigast
   - Kan göra ytterligare sökningar
   - Intelligenter men långsammare

**Fördel med hybrid-ansatsen:**
- Effektiv: Kod filtrerar bort irrelevanta meningar
- Flexibel: LLM kan söka mer vid behov
- Kontrollerad: Begränsad initial sökning (undviker loopar)
- Intelligent: LLM prioriterar viktiga påståenden
