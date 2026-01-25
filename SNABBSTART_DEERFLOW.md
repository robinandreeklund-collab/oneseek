# 🦌 Snabbstart: DeerFlow med VLLM

Detta repo innehåller nu ByteDance's DeerFlow integrerat med OneSeek's VLLM-setup.

## Vad har kopierats?

✅ **DeerFlow's kompletta kodbas**:
- `backend/deer_flow/` - Hela DeerFlow backend (tidigare `src/`)
- `web/` - DeerFlow's moderna Web UI (Next.js)
- `main.py` - Konsol-läge för DeerFlow
- `server.py` - FastAPI server för DeerFlow
- `conf.yaml` - Konfiguration (redan inställd för VLLM)

## Steg-för-steg: Kom igång på 5 minuter

**Ingen databas behövs!** DeerFlow fungerar direkt utan MongoDB eller PostgreSQL. Konversationer sparas inte mellan sessioner, men det behövs inga extra dependencies.

### 1️⃣ Starta VLLM (Terminal 1)

```bash
vllm serve Qwen/Qwen2.5-14B-Instruct-AWQ \
  --dtype auto \
  --quantization awq \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.92 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --host 0.0.0.0 --port 8000
```

**Vänta tills du ser**: `"Application startup complete"`

### 2️⃣ Installera Python-dependencies

**REKOMMENDERAT: Komplett installation med alla dependencies:**
```bash
cd /home/runner/work/oneseek/oneseek
pip install -r requirements-deerflow.txt
```

Detta installerar ALLA DeerFlow dependencies inklusive:
- ✅ Alla LLM providers (DeepSeek, Google, OpenAI)
- ✅ MCP (Model Context Protocol) adapters
- ✅ RAG/Vector stores (Milvus, Qdrant)
- ✅ Checkpoint persistence (MongoDB, PostgreSQL)
- ✅ Search engines och research tools

**Alternativ 1: Minimal installation (färre dependencies, kan ge "No module" fel):**
```bash
pip install -r requirements-minimal.txt
```
Endast core packages. Vissa features fungerar inte.

**Alternativ 2: Med uv (snabbaste):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

### 3️⃣ Starta DeerFlow Backend (Terminal 2)

```bash
python server.py --host 0.0.0.0 --port 8001
```

Backend körs nu på **http://localhost:8001**

### 4️⃣ Installera Web UI dependencies (Terminal 3)

```bash
cd web
pnpm install  # eller: npm install
```

### 5️⃣ Starta Web UI

```bash
cd web
pnpm dev  # eller: npm run dev
```

**Öppna**: http://localhost:3000 🎉

## Testa direkt!

1. Gå till http://localhost:3000
2. Skriv: **"Vad är de senaste AI-trenderna?"**
3. DeerFlow kommer att:
   - Använda din lokala VLLM (RTX 5090)
   - Söka på DuckDuckGo
   - Generera ett omfattande svar med källor

## Konfiguration

### conf.yaml (redan klar!)

```yaml
BASIC_MODEL:
  base_url: "http://localhost:8000/v1"
  model: "Qwen/Qwen2.5-14B-Instruct-AWQ"
  api_key: "EMPTY"
```

### .env (valfria tillägg)

För bättre sök-resultat, lägg till Tavily:
```bash
SEARCH_API=tavily
TAVILY_API_KEY=din_nyckel_här
```

**Valfritt: Spara konversationer (kräver databas)**

Om du vill spara konversationer mellan sessioner:
```bash
# I .env
LANGGRAPH_CHECKPOINT_SAVER=true
LANGGRAPH_CHECKPOINT_DB_URL=mongodb://localhost:27017
# eller
LANGGRAPH_CHECKPOINT_DB_URL=postgresql://user:pass@localhost:5432/db

# Du behöver också installera:
# För MongoDB: pip install langgraph-checkpoint-mongodb motor
# För PostgreSQL: pip install langgraph-checkpoint-postgres psycopg[binary,pool]
```

**OBS:** Detta är helt valfritt! DeerFlow fungerar utan databas.

## Alternativ: Bootstrap-skript

Starta både backend och web UI samtidigt:

```bash
./bootstrap.sh -d
```

## Felsökning

### ❌ "Connection refused" på port 8000

**Problem**: VLLM är inte igång eller använder fel port

**Lösning**:
```bash
# Testa VLLM
curl http://localhost:8000/v1/models

# Borde returnera: {"object":"list","data":[...]}
```

### ❌ "No module named 'langgraph.checkpoint.mongodb'"

**Problem**: Du har aktiverat checkpoint saver men saknar MongoDB packages

**Lösning**:
```bash
# Antingen installera MongoDB support:
pip install langgraph-checkpoint-mongodb motor

# ELLER inaktivera checkpoint saver i .env:
LANGGRAPH_CHECKPOINT_SAVER=false
```

**Viktigt:** Checkpoint saver är **INTE** nödvändig för att köra DeerFlow! Den är bara för att spara konversationer mellan sessioner.

### ❌ "ModuleNotFoundError: No module named 'backend.deer_flow'"

**Problem**: Dependencies inte installerade

**Lösning**:
```bash
cd /home/runner/work/oneseek/oneseek
pip install -r backend/requirements.txt
```

### ❌ Web UI startar inte

**Problem**: Dependencies inte installerade eller fel Node-version

**Lösning**:
```bash
cd web
rm -rf node_modules
pnpm install  # eller npm install
```

### ❌ Backend port 8001 redan upptagen

**Lösning**: Använd annan port
```bash
python server.py --host 0.0.0.0 --port 8002
```

Uppdatera sedan `web/.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8002
```

## Vad funkar nu?

✅ **DeerFlow's Web UI** - Komplett med alla features
✅ **VLLM Integration** - Din RTX 5090 används för inference
✅ **DuckDuckGo Search** - Ingen API-nyckel behövs
✅ **Multi-agent Workflow** - Researcher, Analyst, Reporter
✅ **Citation System** - Automatisk källhantering
✅ **Streaming Responses** - Token-by-token

## Optional: Lägg till fler features

### Tavily Search (bättre resultat)
```bash
# I .env
SEARCH_API=tavily
TAVILY_API_KEY=din_nyckel  # Från https://tavily.com
```

### Vespa RAG (från OneSeek)
```bash
# I .env
RAG_PROVIDER=vespa
VESPA_URL=https://din-app.vespa-cloud.net
VESPA_CERT_PATH=/path/to/cert.pem
VESPA_KEY_PATH=/path/to/key.pem
```

## Nästa steg

Nu när DeerFlow fungerar med VLLM, kan du:

1. **Testa deras Web UI** - Se om den är bättre än OneSeek's frontend
2. **Utvärdera features** - Multi-agent, citations, report generation
3. **Anpassa för era behov** - Ändra prompts, lägg till verktyg
4. **Utveckla vidare** - Om den funkar bra, bygg vidare på DeerFlow

## Dokumentation

- [📘 DeerFlow Original Docs](https://github.com/bytedance/deer-flow)
- [📖 DEERFLOW_VLLM_SETUP.md](DEERFLOW_VLLM_SETUP.md) - Detaljerad setup
- [📄 DEER_FLOW_ATTRIBUTION.md](DEER_FLOW_ATTRIBUTION.md) - License info
- [🔧 backend/DEER_FLOW_INTEGRATION.md](backend/DEER_FLOW_INTEGRATION.md) - Integration detaljer

## Support

Om något inte fungerar:
1. Kolla att VLLM körs: `curl http://localhost:8000/v1/models`
2. Kolla backend logs: `python server.py` (se error messages)
3. Kolla web UI logs: `cd web && pnpm dev` (se console)

**Lycka till med testningen!** 🚀
