# Kodplanerare - Implementeringssammanfattning

Detta dokument sammanfattar implementeringen av Kodplanerare-arkitekturen för strukturerad kodutveckling i OneSeek.

## Översikt

Kodplaneraren ger ett strukturerat, planerat tillvägagångssätt för kodutveckling med dedikerade faser för planering, implementering, testning och validering.

## Huvudfunktioner

### 1. Kodplanerare (Code Planner)
- Skapar detaljerade planer för kodutvecklingsuppgifter
- Identifierar forskningsbehov (dokumentation, exempel)
- Specificerar teststrategi
- Stöder svenska och engelska

### 2. Testare (Tester)
- Validerar kodkvalitet och funktionalitet
- Kör automatiserade tester (pytest, jest)
- Utför linting (pylint, eslint)
- Typkontroll (mypy, tsc)

### 3. Strukturerat Flöde

```
Användare → Koordinator → Kodplanerare → Mänsklig Feedback
                    ↓
            Forskningsteam → Kodare/Testare → Rapportör
```

## Användningsexempel

### Exempel 1: Komplex Koduppgift

**Förfrågan:**
```
Skapa ett Python REST API med Flask och autentisering
```

**Flöde:**
1. Koordinator → Kodplanerare
2. Kodplanerare skapar plan:
   - Forska Flask-autentisering
   - Implementera användarmodell
   - Skapa autentiseringsendpunkter
   - Kör tester (pytest, pylint, mypy)
   - Säkerhetsgranskning
3. Användaren godkänner planen
4. Kodare implementerar
5. Testare validerar
6. Rapportör sammanfattar

### Exempel 2: Enkel Koduppgift

**Förfrågan:**
```
Skriv en funktion för att sortera en lista
```

**Flöde:**
1. Koordinator → Kodare (direkt)
2. Kodare implementerar funktionen
3. Svar med kod

## Konfiguration

### Miljövariabler

```bash
# Aktivera Python-testverktyg
ENABLE_PYTHON_TEST_TOOL=true

# Aktivera JavaScript-testverktyg
ENABLE_JAVASCRIPT_TEST_TOOL=true
```

### Stegtyper

1. **RESEARCH** (Forskning)
   - Samla dokumentation och exempel
   - Körs av Researcher-agent

2. **PROCESSING** (Bearbetning)
   - Faktisk kodimplementering
   - Körs av Coder-agent

3. **TESTING** (Testning)
   - Kör enhetstester och linters
   - Körs av Tester-agent

4. **ANALYSIS** (Analys)
   - Kodgranskning och arkitekturbedömning
   - Körs av Analyst-agent

## Testverktyg

### Python-testverktyg

```python
python_test_tool(
    test_type="pytest",    # eller "pylint", "mypy"
    path="tests/",
    verbose=True
)
```

**Testtyper:**
- `pytest` - Enhetstester
- `pylint` - Kodkvalitet
- `mypy` - Typkontroll

### JavaScript-testverktyg

```python
javascript_test_tool(
    test_type="jest",      # eller "vitest", "eslint", "tsc"
    path="tests/",
    verbose=True
)
```

**Testtyper:**
- `jest`/`vitest` - Enhetstester
- `eslint` - Linting
- `tsc` - TypeScript-typkontroll

## Fördelar

### ✅ Konsistent
Samma planeringsmönster för alla koduppgifter

### ✅ Transparent
Användaren ser hela planen före exekvering

### ✅ Kontrollerat
Mänskligt godkännande före implementering

### ✅ Kvalitet
Obligatorisk testfas med kvalitetskontroller

### ✅ Skalbart
Enkelt att lägga till fler stegtyper och verktyg

## När Använda Vad?

### Använd Kodplanerare för:
- ✅ Flerstegsutvecklingsuppgifter
- ✅ Projekt som kräver dokumentationsforskning
- ✅ Kod som behöver omfattande testning
- ✅ Komplexa applikationer (API:er, webbappar)

### Använd Direkt Kodare för:
- ✅ Enkla funktionsimplementeringar
- ✅ Snabba kodsnippets
- ✅ Enkla algoritmer
- ✅ Felsökningshjälp

## Mänsklig Feedback

Mänsklig feedback styrs av administratörsinställningar (aktiverad som standard):

1. **Plangranskning**: Efter att Kodplaneraren skapat plan, granskar användaren den
2. **Godkännandealternativ**:
   - `[ACCEPTED]` - Fortsätt med planexekvering
   - `[EDIT_PLAN] <ändringar>` - Begär planändringar
3. **Auto-acceptläge**: Kan inaktiveras i inställningar för automatisk exekvering

## Felsökning

### Testverktyg Inte Tillgängliga

**Fel:** "Tool disabled: Python test tool is disabled"

**Lösning:**
```bash
export ENABLE_PYTHON_TEST_TOOL=true
```

### Testramverk Inte Installerat

**Fel:** "Error: pytest is not installed"

**Lösning:**
```bash
pip install pytest pylint mypy
# eller
npm install -D jest eslint typescript
```

## Dokumentation

- [CODE_PLANNER_ARCHITECTURE.md](./CODE_PLANNER_ARCHITECTURE.md) - Fullständig arkitekturdokumentation (engelska)
- [CODE_PLANNER_CONFIGURATION.md](./CODE_PLANNER_CONFIGURATION.md) - Användning och konfiguration (engelska)

## Implementerade Filer

**Skapade:**
- `backend/deer_flow/prompts/code_planner.md` - Engelsk prompt
- `backend/deer_flow/prompts/code_planner.sv_SE.md` - Svensk prompt
- `backend/deer_flow/prompts/tester.md` - Engelsk prompt
- `backend/deer_flow/prompts/tester.sv_SE.md` - Svensk prompt
- `backend/deer_flow/tools/test_tools.py` - Testverktygsimplementering

**Modifierade:**
- `backend/deer_flow/graph/nodes.py` - Lagt till code_planner_node, tester_node
- `backend/deer_flow/graph/builder.py` - Uppdaterad grafstruktur
- `backend/deer_flow/prompts/planner_model.py` - Lagt till TESTING stegtyp
- `backend/deer_flow/config/agents.py` - Lagt till LLM-mappningar
- `backend/deer_flow/tools/__init__.py` - Exporterar testverktyg

**Totalt:** ~1,245 rader kod, 10 filer ändrade

---

**Senast Uppdaterad:** 2026-01-28
**Version:** 1.0.0
