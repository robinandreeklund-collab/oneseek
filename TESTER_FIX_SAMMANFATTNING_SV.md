# Lösning: Tester Installerar Automatiskt Nödvändiga Paket

## ⚠️ OBLIGATORISKT: Aktivera Testverktyg Först!

**KRITISKT**: Innan Tester-agenten kan fungera MÅSTE du aktivera testverktygen via miljövariabler.

Lägg till dessa i din `backend/.env` fil:

```bash
# Aktivera Python-testverktyg (pytest, pylint, mypy)
ENABLE_PYTHON_TEST_TOOL=true

# Aktivera JavaScript-testverktyg (jest, vitest, eslint, tsc)
ENABLE_JAVASCRIPT_TEST_TOOL=true
```

**Snabb Installation:**
```bash
# Kopiera exempelkonfigurationen
cp backend/.env.code_tools_example backend/.env

# Eller lägg till manuellt
echo "ENABLE_PYTHON_TEST_TOOL=true" >> backend/.env
echo "ENABLE_JAVASCRIPT_TEST_TOOL=true" >> backend/.env

# Starta om backend-servern
```

Utan dessa miljövariabler inställda på `true` kommer testverktygen att vara inaktiverade och Tester-agenten kan inte fungera!

---

## Problem

När tester-agenten försökte köra tester fick den fel eftersom nödvändiga testverktyg (pytest, pylint, mypy för Python; jest, eslint, tsc för JavaScript) inte var installerade i utvecklingsmiljön.

### Från problemrapporten:
> "Problemet med pytest - Det verkar som att pytest inte är installerat i vår miljö"
> "Problemet med pylint och mypy - Det verkar som att både pylint och mypy saknas"
> "modellen skapade en venv miljö. men ser inte ut som den försökte installera dom"

## Lösning

Jag har uppdaterat tester-prompterna så att agenten nu **automatiskt kontrollerar och installerar** nödvändiga testverktyg innan den kör några tester.

### Vad Har Ändrats

#### 1. Ny sektion: "Paketinstallation och Miljöinställning"
- **KRITISK** instruktion att kontrollera verktyg först
- Steg-för-steg guide för att kontrollera Python-verktyg
- Steg-för-steg guide för att kontrollera JavaScript-verktyg
- Komplett installationskod som agenten kan köra
- Riktlinjer för installation

#### 2. Uppdaterad Testprocess
- **Steg 0: Kontrollera och Installera Nödvändiga Verktyg** (FÖRSTA STEGET)
- Agenten måste verifiera verktyg innan den kör några tester

#### 3. Nya Riktlinjer
1. Kontrollera verktygsinstallation FÖRST
2. Installera saknade verktyg automatiskt

### Hur Det Fungerar

**Före testning kontrollerar agenten:**
```python
# 1. Kollar om verktyg är installerade
import subprocess
result = subprocess.run([sys.executable, "-m", "pip", "show", "pytest"], ...)

# 2. Installerar saknade verktyg
if not installed:
    subprocess.run([sys.executable, "-m", "pip", "install", "pytest"], ...)
    print("✓ Framgångsrikt installerade pytest")
```

### Vad Händer Nu

#### Scenario 1: Inga Verktyg Installerade
```
⚠ Testverktyg hittades inte. Installerar nödvändiga paket...

Installerar: pytest, pylint, mypy
✓ Framgångsrikt installerade testverktyg

Fortsätter med testkörning...
```

#### Scenario 2: Vissa Verktyg Saknas
```
Kontrollerar för nödvändiga testverktyg...

pytest installerat: True
pylint installerat: False
mypy installerat: True

Installerar saknade paket: pylint
✓ Framgångsrikt installerade: pylint

Fortsätter med testkörning...
```

#### Scenario 3: Alla Verktyg Installerade
```
✓ Alla nödvändiga Python-testverktyg är redan installerade

Kör tester...
```

## Nyckel Funktioner

### ✅ Automatisk Detektion
Agenten kontrollerar automatiskt om verktyg är installerade.

### ✅ Automatisk Installation
Om verktyg saknas installerar agenten dem utan manuell åtgärd.

### ✅ Miljöisolering
Använder `python_repl_tool` som respekterar virtuella miljöer:
- Om koden använder en venv, sker installationer inom den venv:en
- Korrekt miljöisolering bibehålls

### ✅ Batch-installation
Installerar alla saknade verktyg samtidigt (mer effektivt).

### ✅ Tydlig Rapportering
Rapporterar installationsstatus tydligt:
- Vad som installeras
- Framgång eller misslyckande
- Felmeddelanden om något går fel

### ✅ Fungerar för Båda Språken
- **Python**: pytest, pylint, mypy
- **JavaScript**: jest, eslint, typescript

## Vad Har Uppdaterats

**Filer:**
1. ✅ `backend/deer_flow/prompts/tester.md` (Engelska)
2. ✅ `backend/deer_flow/prompts/tester.sv_SE.md` (Svenska)
3. ✅ `TESTER_PACKAGE_INSTALLATION_FIX.md` (Detaljerad dokumentation)

**Ändringar:**
- +130 rader i varje prompt-fil
- Ny "Paketinstallation och Miljöinställning" sektion
- Uppdaterad testprocess med Steg 0
- Nya riktlinjer
- Nytt kantfall

## Testa Lösningen

För att verifiera att det fungerar:

1. **Skapa en tom miljö** utan pytest/pylint/mypy
2. **Be tester-agenten validera Python-kod**
3. **Verifiera** att agenten automatiskt installerar verktyg
4. **Bekräfta** att tester körs framgångsrikt

## Fördelar

**Före:**
- ❌ Tester misslyckades med "command not found"
- ❌ Användaren var tvungen att installera verktyg manuellt
- ❌ Arbetsflödet avbröts

**Efter:**
- ✅ Automatisk verktygsdetektering
- ✅ Automatisk installation
- ✅ Sömlös testning
- ✅ Ingen manuell åtgärd behövs
- ✅ Fungerar med virtuella miljöer

## Din Förfrågan Uppfylld

> "Kan vi även promta modellen att det får installera vad den vill för att kunna använda de verktyg och tester den vill utföra? t.ex kolla din befintliga utveckingsmiljö om den innehåller de tänka paketet. om inte istallerar du dom direkt."

**Svar: JA! ✅**

Tester-agenten:
- ✅ Kollar utvecklingsmiljön
- ✅ Upptäcker saknade paket
- ✅ Installerar dem direkt
- ✅ Fungerar med alla testverktyg (pytest, pylint, mypy, jest, eslint, tsc)

## Sammanfattning

Problemet där tester-agenten försökte köra pytest, pylint och mypy utan att först installera dem är nu löst. Agenten kommer nu automatiskt att:

1. **Kontrollera** om nödvändiga verktyg är installerade
2. **Installera** saknade verktyg
3. **Rapportera** vad som installerades
4. **Fortsätta** med testning

Detta gör testprocessen smidig och eliminerar behovet av manuell paketinstallation!

---

**Datum**: 2026-01-28
**Status**: ✅ LÖST
**Commit**: Add package installation instructions to tester prompts
