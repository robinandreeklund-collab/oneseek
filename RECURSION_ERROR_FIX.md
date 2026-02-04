# Fix för GraphRecursionError i Fact-Checker

## Problem

Efter att ha gjort faktakontrollen helt LLM-driven (borttaget kod-baserad påstående-extraktion), började agenten spamma webbsökningar tills den nådde rekursionsgränsen:

```
langgraph.errors.GraphRecursionError: Recursion limit of 100 reached without hitting a stop condition.
During task with name 'fact_checker' and id 'adf70954-1072-f8b9-7983-006b69b6b894'
```

## Grundorsak

När vi tog bort den kod-baserade `extract_claim_sentences()` funktionen, försvann också den automatiska begränsningen på antal sökningar. LLM-agenten fick då:
- Obegränsad tillgång till `web_search` verktyget
- Inga tydliga instruktioner om när den skulle sluta
- Ingen hård gräns på antal verktygsanrop

Resultat: Agenten fortsatte anropa `web_search` i en loop tills den nådde LangGraph's rekursionsgräns på 100 iterationer.

## Lösning

Implementerade **flera lager av skydd** för att förhindra oändliga loopar:

### 1. Hård Verktygs-gräns (Tool Call Limit)

```python
tool_call_count = {"count": 0, "max": 3}  # Strikt gräns på verktygsanrop

@tool("web_search")
def fact_check_web_search(query: str) -> str:
    tool_call_count["count"] += 1
    if tool_call_count["count"] > tool_call_count["max"]:
        return "VERKTYG_GRÄNS_NÅDD: Du har redan gjort 3 sökningar..."
```

**Hur det fungerar:**
- Delar räknare mellan `web_search` och `crawl` verktyg
- Efter 3 totala anrop, returnerar verktyget ett STOP-meddelande
- LLM:en kan inte göra fler sökningar även om den försöker

### 2. Reducerad Sök-budget

```python
max_search_calls = int(os.getenv("DEBATE_WEB_SEARCH_MAX_CALLS", "3"))
```

- Tidigare: 5 sökningar per runda
- Nu: 3 sökningar per runda (1 initial + 2 LLM-drivna)

### 3. Progressiva Varningar

Efter 2:a verktygsanropet:
```python
if tool_call_count["count"] >= 2:
    formatted_results += "\n\nNOTIS: Du har nu gjort flera sökningar. Överväg att ge ditt slutgiltiga svar baserat på denna information."
```

Detta "nuddar" LLM:en att sluta efter 2 sökningar istället för att vänta till gränsen.

### 4. Tydliga Stopp-instruktioner i Prompt

```python
"**VIKTIGT:**\n"
"- Gör INTE fler än 2-3 sökningar totalt\n"
"- När du fått svar på dina sökningar, GE DITT SLUTGILTIGA SVAR DIREKT\n"
"- Om verktyget säger 'SÖKGRÄNS_NÅDD', använd den information du redan har\n"
"- Försök INTE söka igen om du redan fått tillräcklig information"
```

Explicit kommunicerar:
- Max antal sökningar (2-3)
- När agenten ska sluta (efter den fått svar)
- Vad den ska göra om gränsen nås (använd befintlig info)

### 5. "SPARSMAKAT" Språk

Använder ord som "SPARSMAKAT", "SLUTGILTIGA SVAR", "DIREKT" för att framhäva att agenten inte ska fortsätta söka i evighet.

## Resultat

**Före:**
- Agent kunde göra 100+ verktygsanrop
- Nådde GraphRecursionError
- Oförutsägbart beteende

**Efter:**
- Max 3 verktygsanrop per körning
- Tydliga stopp-signaler
- Förutsägbart och kontrollerat beteende

## Tekniska Detaljer

### Varför Inte Bara max_iterations i Agent?

LangChain's `create_agent` stöder inte direkt en `max_iterations` parameter. Den räknare som finns är på LangGraph-nivå (rekursionsgräns = 100), inte på agent-nivå.

Vi valde istället att:
1. Implementera räknaren i verktyget själv (mer direkt kontroll)
2. Kombinera med prompt-engineering (lära LLM:en att sluta)
3. Använda progressiva varningar (nudging)

### Varför Räknare i Dict?

```python
tool_call_count = {"count": 0, "max": 3}
```

Vi använder en dictionary istället för en enkel variabel eftersom:
- Delas mellan två verktyg (web_search och crawl)
- Python's closure-regler fungerar bättre med mutable objects
- Lätt att dela state mellan nested functions

## Test-strategi

För att verifiera att fixen fungerar:

1. **Positiv test**: Kör faktakontroll med 2-3 viktiga påståenden
   - Förväntat: 2-3 verktygsanrop, sedan slutar agenten
   
2. **Stress test**: Ge många påståenden som behöver verifieras
   - Förväntat: Max 3 verktygsanrop, sedan STOP-meddelande
   
3. **Edge case**: LLM försöker söka efter gränsen
   - Förväntat: Verktyget returnerar "VERKTYG_GRÄNS_NÅDD"

## Framtida Förbättringar

Möjliga optimeringar (ej implementerade):

1. **Dynamisk gräns**: Justera max_calls baserat på komplexitet
2. **Kvalitets-check**: Om alla sökningar var misslyckade, tillåt 1 extra
3. **Kategori-baserad**: Olika gränser för web_search vs crawl
4. **Context-medveten**: Högre gräns om initial sökning gav lite info
5. **Learning**: Logga när agenter når gränsen för att justera framtida limits

## Sammanfattning

Problem: LLM-agent spammade sökningar → GraphRecursionError

Lösning: Hård verktygs-gräns (3 anrop) + Tydliga instruktioner + Progressiva varningar

Resultat: Kontrollerat beteende utan oändliga loopar
