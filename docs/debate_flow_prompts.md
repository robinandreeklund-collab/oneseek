# Debate Flow - Prompter och Flöde

## Översikt

Debattkedjan är en komplett separat kedja från forskningskedjan där flera externa AI-modeller (Grok, Gemini, ChatGPT, DeepSeek, OneSeek) deltar i en strukturerad 3-rundors debatt.

## Fullständigt Flöde

```
coordinator (enable_debate_mode=True)
  ↓
debate_planner (skapar 4-stegs debattplan)
  ↓
human_feedback (användare godkänner plan)
  ↓
debate_orchestrator (startar och hanterar rundor)
  ↓
╔══════════════════════════════════════════╗
║ FÖR VARJE RUNDA (1, 2, 3):               ║
╠══════════════════════════════════════════╣
║ external_ai_caller                        ║
║   → Anropar Grok, Gemini, ChatGPT,       ║
║     DeepSeek, OneSeek sekventiellt       ║
║   ↓                                       ║
║ fact_checker                              ║
║   → Verifierar alla AI-påståenden        ║
║     med web_search + crawl_tool          ║
║   ↓                                       ║
║ synthesizer                               ║
║   → Integrerar alla perspektiv           ║
║     för överlägsen syntes                ║
║   ↓                                       ║
║ moderator                                 ║
║   → Sammanfattar rundan                  ║
║   → Ger poäng (0-3) per modell           ║
║   ↓                                       ║
║ debate_orchestrator                       ║
║   → Loopar till nästa runda              ║
╚══════════════════════════════════════════╝
  ↓
debate_orchestrator (efter runda 3)
  → Sätter debate_complete=True
  ↓
reporter (skapar slutlig sammanfattning)
  ↓
human_feedback (kontrollerar debate_complete)
  ↓
END (aldrig via research_team!)
```

## Noder och Deras Prompter

### 1. debate_planner
**Fil:** `backend/deer_flow/prompts/debate_planner.sv_SE.md`

**Roll:** Skapar strukturerad 4-stegs debattplan

**Steg som skapas:**
1. Runda 1: Initiala argument
2. Runda 2: Utveckling och motargument
3. Runda 3: Slutliga positioner och syntes
4. Röstning: Demokratiskt val

**Output:** JSON-plan med 4 steg

**Verktyg:** Inga (genererar bara plan)

---

### 2. debate_orchestrator
**Fil:** `backend/deer_flow/prompts/debate_orchestrator.sv_SE.md`

**Roll:** Dirigent som hanterar debattflödet

**Ansvar:**
- Koordinerar varje runda (1, 2, 3)
- Tar emot strukturerat svar från moderatorn
- Uppdaterar poängställning
- Avgör när debatten ska avslutas

**Exit-kriterier:**
- 3 rundor uppnått (standard)
- Knockout-argument från moderator
- Betydande poängledning

**Routing:**
- Nästa runda: `goto="external_ai_caller"`
- Debatt klar: `goto="reporter"`

**Verktyg:** Inga (koordinerar bara flödet)

---

### 3. external_ai_caller
**Fil:** `backend/deer_flow/prompts/external_ai_caller.sv_SE.md`

**Roll:** Orchestrerar sekventiella anrop till alla AI-modeller

**Ansvar:**
- Anropar modeller EN I TAGET (inte parallellt)
- Varje runda: slumpad ordning
- Bygger chain-of-thought: varje modell ser tidigare svar i rundan

**Modeller:**
- `gpt-3.5-turbo` (ChatGPT)
- `gemini-2.5-flash` (Gemini)
- `deepseek-chat` (DeepSeek)
- `grok-4-fast-reasoning` (Grok)
- `oneseek-local` (OneSeek)

**Verktyg (från debate_tools.py):**
1. `start_debate_round(round_number, user_query, locale)` - Startar runda
2. `query_model_in_round(model_key, user_query, locale)` - Anropar specifik modell
3. `collect_debate_votes(user_query)` - Samlar röster (efter runda 3)
4. `get_debate_summary()` - Hämtar slutlig sammanfattning

**Routing:** `goto="fact_checker"`

---

### 4. fact_checker
**Fil:** `backend/deer_flow/prompts/fact_checker.sv_SE.md`

**Roll:** Verifierar fakta från ALLA externa AI-modeller

**Ansvar:**
- Kontrollerar påståenden från Grok, Gemini, ChatGPT, DeepSeek
- Söker aktivt efter verifiering
- Markerar varje påstående som:
  - ✅ VERIFIERAD
  - ⚠️ DELVIS VERIFIERAD
  - ❌ FALSKT/VILSELEDANDE
  - ❔ OKÄNT

**Verktyg:**
1. `web_search(query)` - Sök efter bekräftelse/motbevis
2. `crawl_tool(url)` - Läs originalkällor

**Output:** Verifierad lista med källor för varje AI-modells påståenden

**Routing:** `goto="synthesizer"`

---

### 5. synthesizer
**Fil:** `backend/deer_flow/prompts/synthesizer.sv_SE.md`

**Roll:** Integrerar alla AI-perspektiv till överlägsen syntes

**Ansvar:**
- Ta det bästa från Grok, Gemini, ChatGPT, DeepSeek
- Skapa en position bättre än någon enskild AI
- Balansera styrkor och svagheter
- Lägg till nya insikter baserade på verifierade fakta

**Verktyg:**
1. `web_search(query)` - Hitta nyanserade analyser
2. `crawl_tool(url)` - Läs djupgående källor

**Output:** Strukturerad syntes som integrerar alla perspektiv

**Routing:** `goto="moderator"`

---

### 6. moderator
**Fil:** `backend/deer_flow/prompts/moderator.sv_SE.md`

**Roll:** Neutral bedömare av rundan

**Ansvar:**
- Sammanfattar rundan objektivt
- Ger poäng (0-3) till varje AI-modell
- Identifierar starkaste argument
- Avgör knockout-argument (om tillämpligt)

**Bedömningskriterier:**
1. Evidensstyrka
2. Logisk koherens
3. Relevans
4. Övertygelseförmåga
5. Faktakvalitet (från fact_checker)
6. Originalitet

**Output:** JSON med poäng, vinnare, sammanfattning

**Verktyg:** Inga (bedömer bara)

**Routing:** `goto="debate_orchestrator"`

---

### 7. reporter
**Fil:** `backend/deer_flow/prompts/reporter.sv_SE.md` (generisk reporter)

**Roll:** Skapar slutlig sammanfattning efter alla 3 rundor

**Ansvar:**
- Sammanställer alla rundor
- Visar slutliga poäng
- Deklarerar vinnare
- Inkluderar källor och verifierade fakta

**Verktyg:** Inga (sammanställer bara)

**Routing:** `goto="human_feedback"`

---

## OneSeek:s Roll i Debatten

**OBS:** OneSeek deltar SOM EN AV DEBATTÖRERNA, inte som neutral part!

**När OneSeek svarar:**
- OneSeek anropas via `query_model_in_round(model_key="oneseek-local", ...)`
- OneSeek får samma kontext som andra modeller (tidigare rundor + chain_so_far)
- OneSeek får OCKSÅ verifierade fakta från fact_checker (från tidigare rundor)
- OneSeek får OCKSÅ syntetiserad insikt från synthesizer (från tidigare rundor)

**Prompt för OneSeek:** 
OneSeek använder INTE en separat debatt-prompt. Istället används:
- Debattverktygets prompt-formattering (i `debate_flow.py` lines 140-184)
- Kontext inkluderar: användarfråga, tidigare rundor, chain_so_far
- OneSeek har tillgång till verifierad information från tidigare rundor

---

## Verktygsanvändning

### Verktyg som används av varje nod:

| Nod | Verktyg | Syfte |
|-----|---------|-------|
| **debate_planner** | Inga | Skapar bara plan |
| **debate_orchestrator** | Inga | Koordinerar flöde |
| **external_ai_caller** | `start_debate_round`<br>`query_model_in_round`<br>`collect_debate_votes`<br>`get_debate_summary` | Orchestrerar AI-anrop |
| **fact_checker** | `web_search`<br>`crawl_tool` | Verifierar fakta |
| **synthesizer** | `web_search`<br>`crawl_tool` | Söker ytterligare perspektiv |
| **moderator** | Inga | Bedömer bara |
| **reporter** | Inga | Sammanställer bara |

### Verktygsnamn (MÅSTE vara konsekventa!):

✅ **KORREKT:**
- `web_search(query)` - Standard webbsökning
- `crawl_tool(url)` - Crawlar specifik URL

❌ **FEL (gamla namnet):**
- ~~`debater_web_search(query)`~~ - Detta ska INTE användas!

---

## Kontextflöde

### Runda 1:
```
User Query → external_ai_caller
  → Grok svarar (ser bara user query)
  → Gemini svarar (ser user query + Grok)
  → ChatGPT svarar (ser user query + Grok + Gemini)
  → DeepSeek svarar (ser user query + Grok + Gemini + ChatGPT)
  → OneSeek svarar (ser user query + alla ovanstående)
  ↓
fact_checker verifierar alla påståenden
  ↓
synthesizer integrerar alla perspektiv
  ↓
moderator ger poäng
```

### Runda 2:
```
User Query + HELA RUNDA 1 + verifierad info → external_ai_caller
  → Modeller svarar i ny slumpad ordning
  → Varje modell ser: user query + runda 1 + chain_so_far i runda 2
  ↓
fact_checker verifierar (inklusive nya påståenden)
  ↓
synthesizer integrerar (bygger på tidigare syntes)
  ↓
moderator ger poäng
```

### Runda 3:
```
User Query + RUNDA 1 + RUNDA 2 + verifierad info → external_ai_caller
  → Modeller svarar i ny slumpad ordning
  → Slutliga positioner
  ↓
fact_checker verifierar
  ↓
synthesizer skapar final syntes
  ↓
moderator ger slutpoäng
  ↓
debate_orchestrator → reporter
```

---

## Röstning

**Efter Runda 3:**
- `external_ai_caller` anropar `collect_debate_votes(user_query)`
- Externa modeller (Grok, Gemini, ChatGPT, DeepSeek) röstar
- OneSeek röstar INTE (själv deltagare)
- Ingen modell får rösta på sig själv
- Röster sammanställs och vinnare deklareras

---

## Sammanfattning: Prompt-till-Nod-Mapping

| Prompt-fil | Nod i builder.py | Verktyg | Routing |
|------------|------------------|---------|---------|
| `debate_planner.sv_SE.md` | `debate_planner` | Inga | → human_feedback |
| `debate_orchestrator.sv_SE.md` | `debate_orchestrator` | Inga | → external_ai_caller ELLER reporter |
| `external_ai_caller.sv_SE.md` | `external_ai_caller` | debate_tools | → fact_checker |
| `fact_checker.sv_SE.md` | `fact_checker` | web_search, crawl_tool | → synthesizer |
| `synthesizer.sv_SE.md` | `synthesizer` | web_search, crawl_tool | → moderator |
| `moderator.sv_SE.md` | `moderator` | Inga | → debate_orchestrator |
| `reporter.sv_SE.md` | `reporter` | Inga | → human_feedback |

---

## Viktiga Noteringar

1. **Separat kedja:** Debatt använder ALDRIG research_team noder (researcher, analyst, coder, tester)
2. **Sekventiell AI-anrop:** Modeller anropas EN I TAGET för chain-of-thought
3. **Verktygsnamn:** Använd `web_search`, INTE `debater_web_search`
4. **OneSeek deltar:** OneSeek är EN AV debattörerna, inte neutral observatör
5. **Faktakoll varje runda:** fact_checker körs EFTER VARJE RUNDA, inte efter alla rundor
6. **Syntes varje runda:** synthesizer integrerar EFTER VARJE RUNDA
7. **Poäng ackumuleras:** moderator ger poäng varje runda, slutpoäng är summan av alla rundor

---

## Uppdateringar Behövs

### Prompter som behöver fixas:
1. ✅ `external_ai_caller.sv_SE.md` - Ta bort `debater_web_search`, det är fel verktyg
2. ✅ `debate_orchestrator.sv_SE.md` - Uppdatera flöde: inte "debate_team", utan direkt till nodes
3. ⚠️ `fact_checker.sv_SE.md` - OK, men måste klargöra att den körs efter VARJE runda
4. ⚠️ `synthesizer.sv_SE.md` - OK, men måste klargöra att den körs efter VARJE runda
5. ⚠️ `moderator.sv_SE.md` - OK, men refererar till gamla noder (proponent/opponent)

### Kod som behöver fixas:
- Inget! Flödet är korrekt i builder.py efter commit d50c82b
