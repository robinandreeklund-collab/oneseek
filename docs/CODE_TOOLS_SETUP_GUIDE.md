# Code Router & Development Tools - Komplett Setup Guide

En steg-för-steg guide för att sätta upp och använda de nya kodverktygen i OneSeek.

## 📋 Innehållsförteckning

1. [Översikt](#översikt)
2. [Systemkrav](#systemkrav)
3. [Installation - Steg för steg](#installation---steg-för-steg)
4. [Konfiguration](#konfiguration)
5. [Testning](#testning)
6. [Felsökning](#felsökning)
7. [Avancerad användning](#avancerad-användning)

---

## Översikt

De nya kodverktygen ger OneSeek förmågan att:
- ✅ Identifiera och hantera kodrelaterade frågor automatiskt
- ✅ Exekvera kod i isolerade sandlådemiljöer (WSL/Docker)
- ✅ Hantera filer och projekt i säkra workspace-kataloger
- ✅ Skapa och förhandsgranska Next.js/React-applikationer i realtid

### Arkitektur

```
Kodfråga → Coordinator → Coder → Direkt Svar
(3 noder, snabb och direkt respons)
```

Detta är **50% snabbare** än den vanliga research-flödet som går genom Planner → Research Team → Reporter.

---

## Systemkrav

### ✅ Obligatoriskt

| Komponent | Version | Syfte |
|-----------|---------|-------|
| **Python** | 3.11+ | Backend |
| **OneSeek Backend** | Senaste | Huvudsystem |
| **Node.js** | 18+ | React Sandbox |
| **npm** eller **yarn** | Senaste | Pakethantering |

### 🔧 Valfritt (för full funktionalitet)

| Komponent | Plattform | Syfte |
|-----------|-----------|-------|
| **WSL 2** | Windows | Linux Sandbox |
| **Docker** | Alla | Alternativ/ytterligare sandbox |
| **Git Bash** | Windows | Shell-kommandon |

---

## Installation - Steg för steg

### Steg 1: Verifiera befintlig installation

Kontrollera att OneSeek backend fungerar:

```bash
# Navigera till backend-katalogen
cd /path/to/oneseek/backend

# Kontrollera att Python-miljön är korrekt
python --version  # Ska visa 3.11 eller högre

# Verifiera att dependencies är installerade
pip list | grep langchain
pip list | grep langgraph
```

**Förväntat resultat**: Du ska se langchain och langgraph i listan.

---

### Steg 2: Installera WSL (Windows-användare)

Om du använder Windows och vill ha Linux Sandbox:

#### 2.1 Öppna PowerShell som administratör

```powershell
# Installera WSL 2
wsl --install
```

#### 2.2 Starta om datorn

Efter omstart, öppna PowerShell igen:

```powershell
# Verifiera installation
wsl --status

# Installera Ubuntu (rekommenderad distribution)
wsl --install -d Ubuntu
```

#### 2.3 Konfigurera Ubuntu

Första gången du startar Ubuntu:
- Skapa användarnamn och lösenord
- Uppdatera paket: `sudo apt update && sudo apt upgrade -y`

**Test att WSL fungerar**:
```powershell
wsl echo "WSL fungerar!"
```

---

### Steg 3: Installera Docker (Valfritt)

Docker är ett alternativ till WSL eller kan användas tillsammans med WSL.

#### 3.1 Windows

1. Ladda ner [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Installera och starta Docker Desktop
3. I Docker Desktop inställningar:
   - Aktivera "Use WSL 2 based engine" (om du har WSL)
   - Tilldela minst 4GB RAM

#### 3.2 Linux

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Lägg till din användare i docker-gruppen
sudo usermod -aG docker $USER

# Logga ut och in igen, testa sedan
docker --version
docker run hello-world
```

#### 3.3 macOS

1. Ladda ner [Docker Desktop för Mac](https://www.docker.com/products/docker-desktop)
2. Installera och starta
3. Verifiera: `docker --version`

---

### Steg 4: Verifiera Node.js och npm

React Sandbox kräver Node.js:

```bash
# Kontrollera version
node --version  # Ska vara 18 eller högre
npm --version

# Om Node.js saknas, installera:

# Windows (med Chocolatey)
choco install nodejs

# Linux (Ubuntu/Debian)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS (med Homebrew)
brew install node
```

---

## Konfiguration

### Steg 5: Konfigurera miljövariabler

#### 5.1 Kopiera exempelkonfiguration

```bash
cd /path/to/oneseek/backend

# Kopiera exempel-filen
cp .env.code_tools_example .env
```

**Obs**: Om du redan har en `.env`-fil, öppna den och lägg till de nya variablerna.

#### 5.2 Redigera .env-filen

Öppna `backend/.env` i din texteditor och konfigurera:

```bash
# ============================================================
# STEG 1: Aktivera Python REPL (alltid rekommenderat)
# ============================================================
ENABLE_PYTHON_REPL=true

# ============================================================
# STEG 2: Aktivera Linux Sandbox
# ============================================================
# Kräver: WSL (Windows) eller Docker
# Sätt till true om du har WSL eller Docker installerat
ENABLE_LINUX_SANDBOX=true

# ============================================================
# STEG 3: Aktivera File System Tool
# ============================================================
# Låter agenten läsa/skriva filer i en säker workspace
ENABLE_FILE_SYSTEM_TOOL=true

# ============================================================
# STEG 4: Aktivera React Sandbox
# ============================================================
# Kräver: Node.js och npm
# Sätt till true om du vill kunna skapa Next.js-appar
ENABLE_REACT_SANDBOX=true

# ============================================================
# STEG 5: Konfigurera workspace-kataloger
# ============================================================

# Skapa dessa kataloger först!
# Windows: C:/Users/DittNamn/oneseek_workspace
# Linux/Mac: /home/dittnamn/oneseek_workspace

CODE_WORKSPACE_ROOT=/path/to/your/workspace
REACT_SANDBOX_ROOT=/path/to/react/sandboxes

# ============================================================
# STEG 6: Docker-konfiguration (om du använder Docker)
# ============================================================
DOCKER_SANDBOX_IMAGE=ubuntu:latest
```

#### 5.3 Skapa workspace-kataloger

```bash
# Windows (PowerShell)
New-Item -ItemType Directory -Path "C:\Users\$env:USERNAME\oneseek_workspace"
New-Item -ItemType Directory -Path "C:\Users\$env:USERNAME\oneseek_react_sandboxes"

# Linux/Mac
mkdir -p ~/oneseek_workspace
mkdir -p ~/oneseek_react_sandboxes
```

Uppdatera sedan din `.env`:

```bash
# Windows
CODE_WORKSPACE_ROOT=C:/Users/DittNamn/oneseek_workspace
REACT_SANDBOX_ROOT=C:/Users/DittNamn/oneseek_react_sandboxes

# Linux/Mac
CODE_WORKSPACE_ROOT=/home/dittnamn/oneseek_workspace
REACT_SANDBOX_ROOT=/home/dittnamn/oneseek_react_sandboxes
```

---

### Steg 6: Starta om backend

För att ändringarna ska träda i kraft:

```bash
cd /path/to/oneseek/backend

# Stoppa backend om den körs (Ctrl+C)

# Starta backend igen
uvicorn app:app --reload --port 8001
```

**Förväntat resultat**: Backend startar utan fel och du ser:
```
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## Testning

### Steg 7: Testa verktyg individuellt

#### Test 1: Python REPL

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Skriv Python-kod för att beräkna fakulteten av 5"
      }
    ],
    "stream": false
  }'
```

**Förväntat resultat**: Agenten skriver och kör Python-kod som beräknar `5! = 120`.

---

#### Test 2: Linux Sandbox

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Kör kommandot uname -a för att visa systeminformation"
      }
    ],
    "stream": false
  }'
```

**Förväntat resultat**: Agenten kör kommandot i WSL/Docker och visar Linux-systeminfo.

**Om det misslyckas**: Kontrollera att WSL eller Docker är installerat och `ENABLE_LINUX_SANDBOX=true`.

---

#### Test 3: File System Tool

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Skapa en fil hello.txt med innehållet Hello, OneSeek!"
      }
    ],
    "stream": false
  }'
```

**Förväntat resultat**: Agenten skapar filen i din workspace-katalog.

**Verifiera**:
```bash
# Windows
type C:\Users\DittNamn\oneseek_workspace\hello.txt

# Linux/Mac
cat ~/oneseek_workspace/hello.txt
```

Du ska se: `Hello, OneSeek!`

---

#### Test 4: React Sandbox

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Skapa en enkel Next.js-app med en räknare-komponent"
      }
    ],
    "stream": false
  }'
```

**Förväntat resultat**: Agenten skapar ett Next.js-projekt i `REACT_SANDBOX_ROOT`.

**Verifiera**:
```bash
# Navigera till sandbox-katalogen
cd /path/to/react/sandboxes

# Lista projekt
ls -la

# Starta projektet manuellt (om agenten gav instruktioner)
cd mitt-projekt
npm install
npm run dev
```

Öppna `http://localhost:3000` i webbläsare för att se appen.

---

### Steg 8: Test komplett workflow

Testa det direkta routing-flödet:

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Skriv en Python-funktion som sorterar en lista och testa den med [3,1,4,1,5,9,2,6]"
      }
    ],
    "stream": false
  }'
```

**Förväntat resultat**: 
1. Coordinator identifierar detta som en kodfråga
2. Routar direkt till Coder-noden
3. Coder skriver Python-kod
4. Kör koden med Python REPL
5. Returnerar resultatet direkt (utan att gå via Reporter)

**Backend-loggar** ska visa:
```
INFO: Coordinator talking.
INFO: Handing off to coder for code-related task
INFO: Code task is clear, routing directly to coder
INFO: Coder node is coding.
INFO: Coder was called directly from coordinator, responding to user (__end__)
```

---

## Felsökning

### Problem 1: "WSL eller Docker hittades inte"

**Symptom**: Linux Sandbox-verktyget returnerar felmeddelande.

**Lösning**:
1. Verifiera WSL: `wsl --status` (Windows)
2. Verifiera Docker: `docker --version`
3. Om ingen är installerad, följ [Steg 2](#steg-2-installera-wsl-windows-användare) eller [Steg 3](#steg-3-installera-docker-valfritt)
4. Alternativt: Sätt `ENABLE_LINUX_SANDBOX=false` i `.env`

---

### Problem 2: "Tool disabled" meddelanden

**Symptom**: Agenten säger att verktyget är inaktiverat.

**Lösning**:
1. Öppna `backend/.env`
2. Kontrollera att relevant `ENABLE_*` variabel är `true`
3. Starta om backend: `uvicorn app:app --reload --port 8001`
4. Testa igen

**Exempel**:
```bash
# Om File System Tool är disabled
ENABLE_FILE_SYSTEM_TOOL=true  # Ska vara true, inte false
```

---

### Problem 3: "Path outside workspace" fel

**Symptom**: File System Tool nekar åtkomst till filer.

**Lösning**:
Detta är en **säkerhetsfunktion**. Alla filoperationer måste vara inom workspace.

1. Kontrollera `CODE_WORKSPACE_ROOT` i `.env`
2. Se till att katalogen existerar:
   ```bash
   # Windows
   New-Item -ItemType Directory -Force -Path "C:\Users\DittNamn\oneseek_workspace"
   
   # Linux/Mac
   mkdir -p ~/oneseek_workspace
   ```
3. Uppdatera sökvägen i `.env` om den är fel
4. Starta om backend

---

### Problem 4: "npm not found" för React Sandbox

**Symptom**: React Sandbox kan inte hitta npm.

**Lösning**:
1. Installera Node.js (se [Steg 4](#steg-4-verifiera-nodejs-och-npm))
2. Verifiera: `npm --version`
3. Om installerad men inte hittas, lägg till i PATH:
   ```bash
   # Windows: Lägg till i System Environment Variables
   # C:\Program Files\nodejs
   
   # Linux: Lägg till i ~/.bashrc
   export PATH=$PATH:/usr/local/bin
   ```
4. Starta om terminalen och backend

---

### Problem 5: Kod-frågor går inte till Coder

**Symptom**: Kod-frågor behandlas som vanliga research-frågor.

**Lösning**:
Detta kan bero på att frågan inte innehåller kodrelaterade nyckelord.

**Testa med tydligare formulering**:
- ❌ "Kan du hjälpa mig?"
- ✅ "Skriv Python-kod för att..."
- ✅ "Skapa en React-komponent som..."
- ✅ "Debug min JavaScript-funktion"

**Kodrelaterade nyckelord** som identifieras:
- Programmeringsspråk: python, javascript, java, typescript, c++, c#, etc.
- Kodtermer: kod, programmering, function, class, algorithm, etc.
- Ramverk: react, django, nextjs, express, etc.
- Åtgärder: skriv kod, skapa app, bygg, debug, kompilera, etc.

---

### Problem 6: AttributeError 'NoneType' object has no attribute 'title'

**Symptom**: Backend kraschar med traceback som innehåller:
```
AttributeError: 'NoneType' object has no attribute 'title'
  File "backend/deer_flow/graph/nodes.py", line 1429, in _execute_agent_step
    plan_title = current_plan.title
```

**Lösning**:
Detta problem har åtgärdats i den senaste versionen (commit e983323).

**Om du fortfarande får felet**:
1. **Uppdatera koden**: Hämta senaste versionen
   ```bash
   git pull origin copilot/integrera-ny-router-kodfror
   ```

2. **Verifiera fix finns**: Kontrollera att `backend/deer_flow/graph/nodes.py` innehåller null-check (rad ~1429-1458)

3. **Starta om backend**: 
   ```bash
   cd backend
   uvicorn app:app --reload --port 8001
   ```

**Teknisk förklaring**: 
När coder_node anropas direkt från coordinator (ny direkt routing), finns ingen `current_plan` i state. Den uppdaterade koden detekterar detta automatiskt och skapar en syntetisk plan:
- Använder research_topic som plantitel
- Skapar ett enda steg med typ PROCESSING
- Tar bort [CODE]-prefix om det finns
- Resten av exekveringen fortsätter normalt

**Bekräfta fix fungerar**:
```bash
# Testa en kodfråga
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Skriv Python-kod för att beräkna 2+2"}]}'

# Förväntat: Inget AttributeError, kod körs normalt
```

---

## Avancerad användning

### Anpassa Docker-bild

Om du vill ha specifika verktyg i Linux Sandbox:

#### 1. Skapa en Dockerfile

```dockerfile
# Skapa fil: oneseek-sandbox.Dockerfile

FROM ubuntu:22.04

# Installera verktyg
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    nodejs \
    npm \
    gcc \
    g++ \
    make \
    git \
    && rm -rf /var/lib/apt/lists/*

# Installera Python-paket
RUN pip3 install numpy pandas matplotlib

WORKDIR /workspace
```

#### 2. Bygg imagen

```bash
docker build -f oneseek-sandbox.Dockerfile -t oneseek-sandbox:latest .
```

#### 3. Uppdatera .env

```bash
DOCKER_SANDBOX_IMAGE=oneseek-sandbox:latest
```

#### 4. Starta om backend

Nu kommer Linux Sandbox att använda din anpassade bild med alla verktyg installerade.

---

### Säkerhetsåtgärder för produktion

Om du planerar att använda verktygen i produktion:

#### 1. Begränsa workspace-storlek

```bash
# Linux: Sätt disk quota
sudo setquota -u oneseek_user 1000000 1100000 0 0 /home/oneseek_workspace

# Windows: Högerklicka på katalog → Properties → Quota
```

#### 2. Monitorera resursanvändning

```bash
# Skapa ett monitor-script
cat > monitor_tools.sh << 'EOF'
#!/bin/bash
while true; do
  echo "=== $(date) ==="
  echo "Disk usage:"
  du -sh /path/to/oneseek_workspace
  echo "Docker containers:"
  docker ps --format "{{.Names}}\t{{.Status}}\t{{.Size}}"
  echo ""
  sleep 300  # Var 5:e minut
done
EOF

chmod +x monitor_tools.sh
./monitor_tools.sh > monitor.log 2>&1 &
```

#### 3. Automatisk städning

```bash
# Skapa cleanup-script
cat > cleanup_workspace.sh << 'EOF'
#!/bin/bash
# Radera filer äldre än 7 dagar
find /path/to/oneseek_workspace -type f -mtime +7 -delete
find /path/to/oneseek_react_sandboxes -type d -mtime +7 -exec rm -rf {} +
EOF

# Lägg till i crontab (kör dagligen kl 02:00)
(crontab -l 2>/dev/null; echo "0 2 * * * /path/to/cleanup_workspace.sh") | crontab -
```

#### 4. Implementera rate limiting

I `backend/app.py`, lägg till rate limiting för kod-endpoints.

---

### Integration med Frontend

För att visa live kodförhandsvisning i frontend:

#### 1. Importera komponenten

```typescript
// I din chat-komponent
import CodePreview from "@/components/code-preview";
```

#### 2. Detektera kod-tool användning

```typescript
const hasReactSandbox = message.tool_calls?.some(
  call => call.name === 'react_sandbox_tool' && call.args?.action === 'preview'
);

const previewUrl = hasReactSandbox 
  ? `http://localhost:${message.tool_calls[0].args.port || 3001}`
  : undefined;
```

#### 3. Rendera preview

```typescript
{previewUrl && (
  <CodePreview
    projectName={message.tool_calls[0].args.project_name}
    previewUrl={previewUrl}
    live={message.is_streaming}
  />
)}
```

Se `frontend/CODE_PREVIEW_INTEGRATION.md` för fullständig guide.

---

## Konfigurationsreferens

### Miljövariabler - Komplett lista

| Variabel | Standard | Beskrivning |
|----------|----------|-------------|
| `ENABLE_PYTHON_REPL` | `false` | Aktivera Python-kodexekvering |
| `ENABLE_LINUX_SANDBOX` | `false` | Aktivera Linux-kommandoexekvering |
| `ENABLE_FILE_SYSTEM_TOOL` | `false` | Aktivera fil-operationer |
| `ENABLE_REACT_SANDBOX` | `false` | Aktivera React/Next.js-projekt |
| `CODE_WORKSPACE_ROOT` | `/tmp/oneseek_workspace` | Root för filoperationer |
| `REACT_SANDBOX_ROOT` | `/tmp/oneseek_react_sandboxes` | Root för React-projekt |
| `DOCKER_SANDBOX_IMAGE` | `ubuntu:latest` | Docker-bild för sandbox |
| `SANDBOX_TIMEOUT` | `30` | Timeout i sekunder |
| `MAX_FILE_SIZE_MB` | `10` | Max filstorlek för läsning |

### Filplatser i projektet

```
oneseek/
├── backend/
│   ├── .env                              # ← KONFIG: Huvudkonfiguration
│   ├── .env.code_tools_example           # ← MALL: Exempel på konfiguration
│   └── deer_flow/
│       ├── tools/
│       │   ├── code_tools.py             # ← KOD: Verktygsimplementation
│       │   └── __init__.py               # ← KOD: Tool exports
│       └── graph/
│           ├── nodes.py                  # ← KOD: Router-logik
│           └── builder.py                # ← KOD: Graph-struktur
│
├── frontend/
│   └── src/
│       └── components/
│           └── code-preview.tsx          # ← UI: Preview-komponent
│
├── docs/
│   └── CODE_TOOLS_SETUP_GUIDE.md         # ← DOK: Denna guide
│
├── CODE_ROUTER_SETUP.md                  # ← DOK: Teknisk dokumentation
├── KOD_ROUTER_INSTALLATION_SV.md         # ← DOK: Installation (svenska)
└── CODE_ROUTER_ARCHITECTURE.md           # ← DOK: Arkitektur-diagram
```

---

## Snabbreferens - Kommandon

### Starta/Stoppa Backend
```bash
# Starta
cd backend && uvicorn app:app --reload --port 8001

# Stoppa
Ctrl+C
```

### Testa verktyg
```bash
# Python REPL
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Skriv Python-kod för att beräkna 2+2"}]}'

# Linux Sandbox
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Kör kommandot ls -la"}]}'

# File System
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Skapa en fil test.txt"}]}'

# React Sandbox
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Skapa en Next.js räknare-app"}]}'
```

### Kontrollera status
```bash
# Backend körs?
curl http://localhost:8001/health

# WSL funkar?
wsl echo "test"

# Docker funkar?
docker run hello-world

# Node.js installerat?
node --version && npm --version
```

### Rensa workspace
```bash
# Windows
Remove-Item -Recurse -Force C:\Users\DittNamn\oneseek_workspace\*

# Linux/Mac
rm -rf ~/oneseek_workspace/*
rm -rf ~/oneseek_react_sandboxes/*
```

---

## Support & Hjälp

### Dokumentation
- 📖 **Denna guide**: `docs/CODE_TOOLS_SETUP_GUIDE.md`
- 🇬🇧 **Engelsk teknisk guide**: `CODE_ROUTER_SETUP.md`
- 🇸🇪 **Svensk installation**: `KOD_ROUTER_INSTALLATION_SV.md`
- 🏗️ **Arkitektur**: `CODE_ROUTER_ARCHITECTURE.md`
- 💻 **Frontend integration**: `frontend/CODE_PREVIEW_INTEGRATION.md`

### Frågor?
- GitHub Issues: [oneseek/issues](https://github.com/robinandreeklund-collab/oneseek/issues)
- Diskussioner: [oneseek/discussions](https://github.com/robinandreeklund-collab/oneseek/discussions)

---

## Changelog

### v1.0.0 (2025-01-28)
- ✅ Initial release av Code Router
- ✅ Linux Sandbox Tool (WSL/Docker)
- ✅ File System Tool
- ✅ React Sandbox Tool
- ✅ Direkt routing-arkitektur
- ✅ Frontend CodePreview-komponent
- ✅ Komplett dokumentation

---

**Skapad**: 2025-01-28  
**Version**: 1.0.0  
**Status**: Produktionsklar för utvecklingsmiljö
