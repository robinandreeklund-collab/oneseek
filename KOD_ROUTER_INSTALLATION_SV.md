# Kod Router och Live Utvecklingsverktyg - Installation och Setup

En komplett guide för att integrera ny router för kodrelaterade frågor och utöka verktyg i LangGraph med live-kodförhandsvisning.

## Översikt

Detta pull request inkluderar flera stora förbättringar och nya funktioner i `deep-oneseek` för att stödja hantering av kodrelaterade frågor och förhandsvisning i realtid:

## 1. Ny Router för Kodrelaterade Frågor

- **Alla kodfrågor i LangGraph hanteras nu av en ny dedikerad router**
- **Routing-logik:**
  - Frågor som är tydligt kodningsspecifika routas direkt till noden **Coder**
  - Om frågan är otydlig, dirigeras den till en ny nod, **Human in the Loop**, innan den eventuellt skickas vidare till **Coder**

### Hur det fungerar

```
Användarfråga
    ↓
Coordinator (upptäcker kodfrågor)
    ↓
handoff_to_coder verktyg kallas
    ↓
├─ [clarity="clear"] → Planner (skapar kodexekveringsplan)
│                          ↓
│                      Research Team
│                          ↓
│                      Coder Node (kör med utökade verktyg)
│                          ↓
│                      Reporter
│
└─ [clarity="unclear"] → Human Feedback
                             ↓
                         Planner (efter förtydligande)
                             ↓
                         ... (fortsätter som ovan)
```

### Koddetektion

Coordinator använder `handoff_to_coder`-verktyget när den upptäcker:
- Programmeringsspråk (Python, JavaScript, Java, etc.)
- Utvecklingstermer (kod, programmering, debug, kompilera, etc.)
- Ramverksnamn (React, Django, Next.js, etc.)
- Utvecklingsaktioner (skriv kod, skapa app, bygga, deploya, etc.)

## 2. Utökning av Verktyg för Coder-noden

För att förbättra funktionalitet och effektivitet, har följande verktyg integrerats:

### Linux Sandbox Environment

- **Isolerade, säkra utvecklingsmiljöer** skapas med hjälp av WSL (Windows Subsystem for Linux) och Docker
- Sandboxarna genereras dynamiskt ("on-demand") för att stödja komplex exekvering av Linux-baserad kod
- 30-sekunders timeout för säkerhet
- Kör bash-kommandon, kompilera kod, testa applikationer

**Funktioner:**
```bash
# Kör kommandon i sandlåda
linux_sandbox_tool(
    command="gcc -o program program.c && ./program",
    working_dir="/tmp/build"
)
```

### File System Management

- **Agenten får tillgång till lokala filsystem** i WSL för att läsa, skriva och manipulera filer
- Stöd för att integrera verktyg som kan hantera projektrelaterad data inom plattformen
- Säkerhetsrestriktioner: alla operationer begränsade till workspace

**Operationer:**
- `read`: Läs filinnehåll
- `write`: Skapa eller uppdatera filer
- `list`: Lista kataloginnehåll
- `delete`: Ta bort filer eller kataloger
- `create_dir`: Skapa nya kataloger

### Live React Sandbox

- **Realtidsförhandsvisning och interaktiv utveckling** för Next.js-applikationer
- Preview integreras i plattformens frontend för att visa resultaten av kod i realtid
- Automatisk projektstruktur
- Hot-reload vid filändringar

**Aktioner:**
- `create`: Initiera nytt Next.js-projekt
- `update`: Modifiera projektfiler
- `preview`: Starta utvecklingsserver
- `stop`: Stoppa preview-server

## 3. Integration till Plattformens Frontend

- **Live-kodförhandsvisning är fullt integrerad** med frontend för att stödja realtidsuppdateringar av kod som skickas via LangGraph
- Utför utveckling och testning direkt via plattformens UI utan behov av externa integrationer
- Tabbed interface för Preview, Code och Terminal
- Iframe sandbox för säker kodexekvering

## Installation och Setup

### Förutsättningar

#### Nödvändiga
- **Python 3.11+**
- **Node.js 18+** (för React sandbox)
- **OneSeek backend** redan installerad och körande

#### Valfria (för full funktionalitet)
- **Windows med WSL 2** (för Linux sandbox på Windows)
- **Docker** (alternativ till WSL eller för ytterligare containerisering)
- **npm/yarn** (för React/Next.js-utveckling)

### Steg 1: Installera Python-beroenden

Kodverktygen ingår redan i DeerFlow-paketet. Inga ytterligare Python-paket krävs utöver befintlig `requirements.txt`.

### Steg 2: Aktivera kodverktyg

Skapa eller uppdatera din `.env`-fil i `backend/`-katalogen:

```bash
# Aktivera Python REPL (redan tillgänglig)
ENABLE_PYTHON_REPL=true

# Aktivera Linux Sandbox Environment
ENABLE_LINUX_SANDBOX=true

# Aktivera File System Management Tool
ENABLE_FILE_SYSTEM_TOOL=true

# Aktivera React Sandbox för Next.js preview
ENABLE_REACT_SANDBOX=true

# Valfritt: Workspace-kataloger
CODE_WORKSPACE_ROOT=/sökväg/till/din/workspace
REACT_SANDBOX_ROOT=/sökväg/till/react/sandboxes
```

### Steg 3: Setup WSL (Windows-användare)

Om du är på Windows och vill använda Linux sandbox:

1. **Installera WSL 2**:
   ```powershell
   wsl --install
   ```

2. **Verifiera att WSL fungerar**:
   ```powershell
   wsl --status
   ```

3. **Installera Ubuntu** (eller din föredragna distro):
   ```powershell
   wsl --install -d Ubuntu
   ```

### Steg 4: Setup Docker (Alternativ eller Ytterligare)

För containeriserad exekvering:

1. **Installera Docker Desktop**: https://www.docker.com/products/docker-desktop

2. **Verifiera att Docker körs**:
   ```bash
   docker --version
   docker run hello-world
   ```

3. **Valfritt**: Sätt anpassad Docker-bild:
   ```bash
   # I din .env-fil
   DOCKER_SANDBOX_IMAGE=ubuntu:latest
   ```

### Steg 5: Starta om Backend

Starta om OneSeek backend för att ladda den nya konfigurationen:

```bash
cd backend
uvicorn app:app --reload --port 8001
```

## Testning

### Testa kodroutning

Skicka en kodrelaterad fråga för att testa routningen:

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Skriv en Python-funktion för att beräkna fibonacci-tal"}
    ],
    "stream": false
  }'
```

### Testa Linux Sandbox

Med `ENABLE_LINUX_SANDBOX=true`, fråga:
> "Kör kommandot 'uname -a' för att visa systeminformation"

### Testa File System

Med `ENABLE_FILE_SYSTEM_TOOL=true`, fråga:
> "Skapa en fil som heter hello.txt med innehållet 'Hej, Världen!'"

### Testa React Sandbox

Med `ENABLE_REACT_SANDBOX=true`, fråga:
> "Skapa en enkel Next.js-app med en räknarkomponent"

## Hur testades detta?

- Samtliga ändringar har testats lokalt i en miljö som använder:
  - **Windows-server:** Backendplattform
  - **WSL och Docker:** För att simulera Linux-miljöer och hantera isolering i modeller
- Verktygen har integrerats och verifierats individuellt:
  - Linux Sandbox och File System direkt via WSL och filinteraktion
  - Live React Sandbox testad med Next.js-projekt i realtid

## Felsökning

### Problem: "WSL eller Docker hittades inte"

**Lösning**: 
- På Windows: Installera WSL 2
- På Linux/Mac: Installera Docker
- Eller inaktivera Linux sandbox: `ENABLE_LINUX_SANDBOX=false`

### Problem: "Verktyget inaktiverat"-meddelanden

**Lösning**: Kontrollera din `.env`-fil och se till att relevanta `ENABLE_*`-variabler är satta till `true`.

### Problem: "Sökväg utanför workspace"-fel

**Lösning**: Filsystemverktyget begränsar operationer till workspace-katalogen av säkerhetsskäl. Sätt `CODE_WORKSPACE_ROOT` till en lämplig plats.

### Problem: React sandbox "npm hittades inte"

**Lösning**: Installera Node.js och npm:
```bash
# Windows (med Chocolatey)
choco install nodejs

# Linux
sudo apt install nodejs npm

# Mac
brew install node
```

## Säkerhetsöverväganden

### Sandlådehantering

- **Linux Sandbox**: Kommandon körs i isolerade WSL/Docker-miljöer
- **File System**: Alla operationer begränsade till workspace-katalog
- **Timeouts**: 30-sekunders körningsgräns förhindrar oändliga loopar
- **Sökvägsvalidering**: Förhindrar directory traversal-attacker

### Bästa praxis

1. **Aktivera inte verktyg i produktion** om du inte helt förstår säkerhetskonsekvenserna
2. **Använd dedikerade workspace-kataloger** separata från kritiska systemfiler
3. **Övervaka resursanvändning** - sandbox-miljöer kan konsumera betydande resurser
4. **Städa regelbundet workspaces** för att förhindra diskutrymme problem
5. **Granska genererad kod** innan körning i produktionsmiljöer

## Framtida Utveckling

### Planerade funktioner

- [ ] Förbättra routing-logik med heuristisk analys eller ML för att mer exakt identifiera oklara frågor
- [ ] Utveckla containerbaserad skalbarhet för ökad prestanda hos Linux Sandbox Environment
- [ ] Frontend live preview komponent fullt integrerad i chatgränssnittet
- [ ] Multi-språk REPL-stöd (Node.js, Ruby, Go, etc.)
- [ ] Git-integration för versionskontroll
- [ ] Container-resursgränser (CPU, minne)
- [ ] Persistenta sandbox-sessioner
- [ ] Kodgranskning och säkerhetsskanningsverktyg

## Dokumentation

### Engelska guider
- [CODE_ROUTER_SETUP.md](CODE_ROUTER_SETUP.md) - Komplett setup-guide
- [frontend/CODE_PREVIEW_INTEGRATION.md](frontend/CODE_PREVIEW_INTEGRATION.md) - Frontend-integrationsguide

### Vanliga OneSeek-dokumentation
- [README.md](README.md) - Huvuddokumentation
- [QUICKSTART.md](QUICKSTART.md) - Snabbstartsguide
- [ARCHITECTURE.md](ARCHITECTURE.md) - Systemarkitektur

## Licens

MIT - Se [LICENSE](LICENSE)-filen

## Support

För frågor eller problem:
- GitHub Issues: [oneseek/issues](https://github.com/robinandreeklund-collab/oneseek/issues)
- Dokumentation: Se [README.md](README.md)

---

Skapad med ❤️ i Karlsborg, Sverige
