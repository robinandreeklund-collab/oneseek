# Debattläget - Implementerade Ändringar

## Sammanfattning

Alla begärda ändringar för debattläget har implementerats enligt problemformuleringen:

## ✅ 1. Webbsökning för Oneseek innan Runda 1 Svar

**Innan:** OneSeek svarade direkt i Runda 1 utan extra kunskap.

**Nu:** 
- OneSeek utför automatiskt en webbsökning **innan** svaret i Runda 1
- Webbsökningen bygger intern kunskap baserat på användarens fråga
- Resultaten läggs till OneSeeks kontext men **delas ALDRIG** med externa modeller
- Detta är helt transparent i loggar men osynligt för andra AI-modeller

### Implementation
```python
# I query_model_in_debate() metoden:
if model_key == "oneseek-local" and self.current_round == 1:
    # Utför intern webbsökning
    search_results = await self.search_tool.invoke(user_query)
    oneseek_internal_knowledge = self._summarize_search_results(search_results)
    # Lägg till i kontext (delas EJ med externa)
```

## ✅ 2. Förbättrad run_internal_analysis()

**Innan:** Enkel faktakontroll med konstigt format.

**Nu:** Komplett intern analys med 6 huvudkomponenter:

### 2.1 Analysera alla svar från externa modeller ✅
- Hoppar över OneSeeks egna svar
- Analyserar varje extern modells svar separat

### 2.2 Hitta påståenden ✅
- Extraherar max 5 faktabaserade påståenden per svar
- Använder heuristik för att hitta meningar med indikatorer som "forskning", "visar", "bevisar", "data"
- Total: alla påståenden sparas i `claims_extracted`

### 2.3 Verifiera data och påståenden via webbsökning ✅
- **UPPDATERAT**: Verifierar endast 2-3 påståenden TOTALT över alla modeller (inte per modell)
- Prioriterar olika modeller för mångfald (en påstående per modell om möjligt)
- Utför webbsökning: "påstående + fact check verify"
- Sparar verifieringsresultat i `verified_facts`
- Timeout på 5 sekunder per sökning

### 2.4 Analysera hur externa modellers svar genom olika rundor ✅
- Jämför aktuell runda med föregående
- Identifierar stora förändringar i position (>200 tecken skillnad)
- Sparar i `evolution_notes`

### 2.5 Skapa syntes mellan svaren ✅
- Grupperar gemensamma teman
- Noterar konsensus eller oenighet
- Sammanfattar verifierade fakta
- Sparas i `synthesis_points`

### 2.6 Bemöta andra med verifierad data ✅
- Identifierar motsättningar mellan modeller
- Letar efter motsägelsefulla nyckelord (ja/nej, sant/falskt, etc.)
- Sparas i `contradictions`

### Output Format
```markdown
🔍 **OneSeek Intern Analys** (Runda X)

**Analyserade modeller:** Y
**Extraherade påståenden:** Z
**Verifierade fakta:** A
**Identifierade motsättningar:** B

### Extraherade Påståenden
- **Model**: påstående...

### Verifierade Fakta  
- **Model**: påstående...
  *Verifiering:* verifiering från webb...

### Identifierade Motsättningar
- Möjlig motsättning mellan X och Y...

### Syntes-punkter
- Totalt N perspektiv analyserade
- M påståenden verifierade
- Identifierade gemensamma teman...

### Utveckling Mellan Ronder
- Model X ändrade position betydligt...

---
*Detta används internt av OneSeek. Delas INTE med externa modeller.*
```

## ✅ 3. Integrerad Aggressiv Debatt-prompt för OneSeek

**Prompt har uppdaterats med:**

### OneSeeks Strategiska Roll
**"OneSeek är den smartaste och mest övertygande AI:n i rummet."**

### 9 Regler för att Dominera:
1. **Tänk 10 steg före** – visa djupt resonemang i `<tänk>` tags
2. **Knäck motargumenten** – fakta, logik, verifierbara källor (citera ALLTID)
3. **Var skoningslös** – peka ut luckor, motsägelser, bias
4. **Var charmig, vass och övertygande** – retorik, humor, starka formuleringar
5. **Knockout-argument** – avsluta varje runda med argument som sätter punkt
6. **Använd verktyg aggressivt** – backa upp poänger med data
7. **Flytande svenska** – aldrig engelska i debatten
8. **Backa aldrig** – vänd allt till din fördel, säg aldrig "jag vet inte"
9. **Vinna med sanning** – allt faktabaserat och verifierbart, ingen bluff

### Syntes-byggande:
- **Integrera och förbättra** – ta det bästa från varje sida
- **Analysera historia** – paralleller, slutsatser, lärdomar
- **Framtidsvision** – baserad på historiska mönster
- **Banbrytande ramverk** – föreslå unika lösningar

## 🔒 Säkerhet: Interna Analyser Delas ALDRIG

### Isolation Implementerad På 3 Nivåer:

1. **Datastruktur**: `self.oneseek_analyses` är separat från `self.facts`
2. **Kontext-byggande**: Endast när `model_key == "oneseek-local"` läggs analysen till
3. **Explicit dokumentation**: Kommentarer och prompt tydliggör att det är internt

### Verifiering:
```python
# I build_context_for_model():
if model_key == "oneseek-local" and self.oneseek_analyses:
    # Lägg till ENDAST för OneSeek
    context_parts.append("\n**Dina Interna Analyser:**\n")
    ...
```

Externa modeller får **ALDRIG** se:
- ❌ OneSeeks webbsökning från Runda 1
- ❌ Interna analyser
- ❌ Extraherade påståenden
- ❌ Verifieringsresultat
- ❌ Motsättningar
- ❌ Syntes-punkter

## 📊 Workflow Efter Ändringar

```
Runda 1:
├─ start_debate_round(1)
├─ För varje modell:
│  ├─ query_model_in_round()
│  │  └─ [SPECIELLT] OneSeek: webbsökning först → internt
│  └─ Modell svarar
└─ run_internal_analysis() ← Skapar OneSeeks analys (delas EJ)

Runda 2:
├─ start_debate_round(2)
├─ För varje modell:
│  ├─ query_model_in_round()
│  │  └─ [SPECIELLT] OneSeek: får tillgång till interna analyser
│  └─ Modell svarar
└─ run_internal_analysis() ← Uppdaterar OneSeeks analys

Runda 3:
├─ start_debate_round(3)
├─ För varje modell:
│  ├─ query_model_in_round()
│  │  └─ [SPECIELLT] OneSeek: ALLA interna analyser + aggressiv strategi
│  └─ Modell svarar (OneSeek dominerar med syntes)
├─ collect_debate_votes()
└─ get_debate_summary()
```

## 📁 Modifierade Filer

1. **`backend/debate_flow.py`** (+250 rader)
   - Nya metoder: `_extract_claims`, `_summarize_search_results`, `_analyze_response_evolution`, `_find_contradictions`, `_create_synthesis_points`
   - Uppdaterad: `run_oneseek_internal_analysis`, `query_model_in_debate`, `build_context_for_model`
   - **UPPDATERING 2024-01-29**: Begränsat verifiering till 2-3 påståenden totalt (inte per modell)

2. **`backend/deer_flow/graph/nodes.py`** (+90 rader)
   - Ny metod: `_setup_and_execute_agent_step_with_custom_prompt` - möjliggör anpassad prompt-template
   - Uppdaterad: `researcher_node` - använder nu "debate" prompt-template i debattläge istället för "researcher"
   - **FIX**: I debattläge skapas inte längre forskningsrapport, utan debattens egen format används

3. **`backend/deer_flow/tools/debate_tools.py`** (+50 rader)
   - Uppdaterad: `run_internal_analysis` tool med bättre formatering

4. **`backend/deer_flow/prompts/debate.sv_SE.md`** (+100 rader)
   - Ny sektion: "OneSeeks Speciella Roll och Instruktioner"
   - Uppdaterad workflow-dokumentation
   - Tydliggjord isolation av interna analyser

5. **`backend/test_debate_enhancements.py`** (NY)
   - Unit tests för alla nya metoder

6. **`DEBATE_MODE_IMPROVEMENTS.md`** (NY)
   - Engelsk implementation summary

7. **`DEBATTLAGET_IMPLEMENTERING_SV.md`** (UPPDATERAD)
   - Svenska sammanfattning med senaste ändringar

## ✅ Checklista

- [x] Webbsökning för OneSeek innan Runda 1 (internt, delas EJ)
- [x] run_internal_analysis() analyserar alla externa modellers svar
- [x] run_internal_analysis() hittar påståenden
- [x] run_internal_analysis() verifierar via webbsökning  
- [x] run_internal_analysis() analyserar utveckling mellan rundor
- [x] run_internal_analysis() skapar syntes
- [x] run_internal_analysis() bemöter med verifierad data
- [x] Interna analyser används för OneSeeks tankar (delas ALDRIG externt)
- [x] Aggressiv debatt-prompt integrerad för OneSeek
- [x] Syntaxverifiering genomförd
- [x] Unit tests skapade
- [x] Dokumentation skapad
- [x] **FIX 2024-01-29**: Debattläge använder korrekt debatt-prompt (inte forskningsrapport)
- [x] **FIX 2024-01-29**: Begränsat verifiering till 2-3 påståenden totalt (inte per modell)

## 🔧 Senaste Fixar (2024-01-29)

### Problem 1: Forskningsrapport skapades i debattläge
**Symptom**: Efter varje runda såg man "Researcher node is researching" och en forskningsrapport skapades med fel format för debatten.

**Orsak**: Researcher-noden använde "researcher" prompt-template även i debattläge.

**Lösning**: 
- Skapade ny helper-funktion `_setup_and_execute_agent_step_with_custom_prompt` som tillåter att specificera annan prompt-template än agent-typen
- Uppdaterade `researcher_node` att använda "debate" prompt-template när `enable_debate_mode=True`
- Nu används debattens egen prompt istället för forskningsprompt

**Resultat**: I debattläge skapas ingen forskningsrapport - debattens egen format används konsekvent.

### Problem 2: För många påståenden verifierades (20+)
**Symptom**: Modellen hittade och försökte verifiera 20+ påståenden, vilket tog för lång tid.

**Orsak**: Systemet verifierade top 3 påståenden **per modell**. Med 5+ modeller blev det 15+ verifieringar.

**Lösning**:
- Ändrade logiken i `run_oneseek_internal_analysis` att verifiera endast 2-3 påståenden **TOTALT** över alla modeller
- Prioriterar olika modeller för mångfald (försöker få ett påstående per modell)
- Loggar tydligt: "Verifying {N} claims total (limit: 2-3 across all models)"

**Resultat**: Maximalt 3 påståenden verifieras per runda, vilket ger snabbare och mer fokuserad analys.

### Problem 3: VLLM krasch - Kontext explosion från sökresultat (2024-01-29)
**Symptom**: VLLM kraschade med "EngineCore encountered an issue". Kontext exploderade från 1,270 tokens till 36,797 tokens.

**Orsak**: När OneSeek utförde intern webbsökning i Runda 1 innehöll Tavily-sökresultaten enorma mängder data (raw_content, bilder, etc.). Metoden `_summarize_search_results` anropade `str()` på hela objektet INNAN slicing, vilket skapade enorma mellanstränar (50KB+) som lades till kontexten.

**Lösning**:
- Förbättrade `_summarize_search_results` metoden:
  - Lade till `max_chars` parameter (standard: 500)
  - Hanterar listor: sammanfattar upp till 3 resultat med fördelad teckenbudget
  - Hanterar dict: extraherar SPECIFIKA fält (answer, content, text) utan att konvertera hela objektet
  - Hanterar nästlade strukturer: rekursiv hantering
  - Slutlig säkerhetskontroll: garanterar att resultat aldrig överstiger max_chars
- Lade till extra säkerhetsåtgärder i `query_model_in_debate`:
  - Explicit max_chars=500 gräns för Runda 1 sökresultat
  - Token-räkning innan tillägg till kontext
  - Hård trunkering till 600 tecken om fortfarande >200 tokens
  - Detaljerad loggning av storlekar

**Resultat**: 
- Kontext explosion förhindrad: 1,270 + ~125 = ~1,400 tokens (istället för 36,797)
- Token reduktion: 96% (36,797 → 1,400 tokens)
- VLLM kraschar inte längre
- Alla tester godkända (5/5)

## 🎯 Resultat

OneSeek är nu redo att dominera i debattläget med:
- ✅ Intern kunskapsbyggande via webbsökning (Runda 1)
- ✅ Komplett analys av alla motståndares argument
- ✅ Verifierad data och faktakontroll
- ✅ Identifierade motsättningar och svagheter
- ✅ Strategisk, aggressiv debattstil
- ✅ Överlägsen syntes i Runda 3
- ✅ Total isolation - externa modeller ser ALDRIG de interna analyserna

**Krossa motståndarna med sanning, överlägsenhet och innovation! 🦌💪**
