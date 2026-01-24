# OneSeek.ai MVP v0.3 – Lokal AI-chat med Multi-Tool Search & Transparens

**OneSeek.ai** är en agent-plattform i tidig MVP-fas med fokus på:
- Lokal LLM-inference via vLLM (på RTX 5090)
- **Multi-tool web search** med Tavily, DuckDuckGo och Vespa (NYTT!)
- Snygg ChatGPT-liknande frontend
- Retrieval-Augmented Generation (RAG) via Vespa Cloud
- Agent-flöde med LangGraph (tool calling → parallel execution → berikad prompt → generera svar)
- Full transparens: visa retrieved källor, steg och metadata i UI

Målet är att bygga mot en unik plattform med **debatt/compare mellan modeller**, **blockchain-logging för verifierbarhet** och **multi-step agenter** – men denna MVP är minimal och körbar lokalt.

## 🚀 Kom igång snabbt

**→ [📖 QUICKSTART.md - Komplett steg-för-steg guide för nybörjare](QUICKSTART.md)**

Denna guide täcker allt från installation av Python och Node.js till att köra din första AI-chat!

---

## Funktioner i denna MVP
- **Multi-tool web search** (NYTT v0.3!): Tavily, DuckDuckGo och Vespa söker samtidigt för bästa resultat
- **Parallel tool execution**: Agenten kan köra flera sökverktyg samtidigt (2-5× snabbare)
- **DeerFlow Integration** (NYTT!): Multi-agent architecture från ByteDance's DeerFlow för deep research
- **Streaming chat** med lokal LLM – token-by-token response i realtid (aktiverat som default)
- **RAG-berikning**: Hämtar relevanta snippets från Vespa Cloud innan svar genereras
- **Transparens i UI**: Accordion med källor, retrieved docs och processing steps
- **LangGraph-orkestrering**: Intelligent tool-calling workflow med conditional edges
- **Progressiv visning**: Steps och källor visas live under generering
- **Cancel-support**: Avbryt requests mitt i streaming
- **Backward compatible**: Gamla RAG-only läget fungerar fortfarande

## Tech Stack
- **Inference**: vLLM (lokal på NVIDIA RTX 5090)
- **Frontend**: Next.js 14+ (App Router), shadcn/ui, Tailwind (baserat på [nextjs-vllm-ui](https://github.com/yoziru/nextjs-vllm-ui))
- **Backend / Agent**: FastAPI 0.115+, LangGraph 0.2+, LangChain 0.3+ (senaste säkerhetspatchar)
- **Retrieval**: Vespa Cloud (hybrid BM25 + semantic search)
- **Embeddings**: all-MiniLM-L6-v2 (lokal via sentence-transformers)

## Krav
- NVIDIA GPU med ≥24 GB VRAM (RTX 5090 rekommenderas)
- Python 3.11+
- Node.js 18+ / 20+
- Docker (valfritt, för Vespa-test lokalt)
- Vespa Cloud-konto (gratis trial med $300 krediter – ingen kreditkort krävs initialt)

## Snabbstart (5–15 minuter efter setup)

### 1. Klona repot
```bash
git clone https://github.com/robinandreeklund-collab/oneseek.git
cd oneseek
```

### 2. Starta vLLM (separat terminal)

Skapa venv om du vill:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install vllm
```

Starta server (exempel med bra balans för RTX 5090):
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

**OBS:** Flaggorna `--enable-auto-tool-choice` och `--tool-call-parser hermes` är **nödvändiga** för att multi-tool sökning ska fungera!

Alternativt snabb modell:
```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --port 8000
```

### 3. Setup Vespa Cloud & Search Tools

1. Gå till https://console.vespa-cloud.com → skapa konto & tenant (t.ex. "oneseek-mvp")
2. Hämta data-plane cert & key från Console → Security
3. (Valfritt) Skaffa Tavily API key från https://tavily.com/ för bästa web search
4. I `backend/` – kopiera `.env.example` till `.env` och fyll i:

```bash
# vLLM Configuration
VLLM_URL=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ

# Vespa Cloud (för RAG)
VESPA_URL=https://ditt-app.ditt-tenant.vespa-cloud.net
VESPA_CERT_PATH=/path/to/certificate.pem
VESPA_KEY_PATH=/path/to/private-key.pem

# Tavily API (valfritt - för premium web search)
TAVILY_API_KEY=your-api-key-here
```

**OBS:** DuckDuckGo fungerar utan konfiguration! Tavily och Vespa är valfria.

5. Deploya schema & feed testdata (om du använder Vespa):
```bash
cd backend
pip install -r requirements.txt
python deploy_vespa.py
```

### 4. Starta backend (FastAPI + LangGraph)

```bash
cd backend
uvicorn app:app --reload --port 8001
```

Backend körs nu på http://localhost:8001

### 5. Starta frontend

```bash
cd frontend
npm install    # eller yarn install
npm run dev    # eller yarn dev
```

Öppna http://localhost:3000

Skriv en fråga och få svar berikade med web search! Exempel:
- "Vad är de senaste nyheterna om AI?"
- "Förklara quantum computing för en nybörjare"
- "Vilka AI-risker diskuteras nu?"

Agenten väljer automatiskt rätt verktyg och kan söka i flera källor samtidigt!

## Projektstruktur

```
oneseek/
├── backend/
│   ├── app.py                    # FastAPI-server med multi-tool support
│   ├── agent.py                  # Legacy LangGraph RAG agent
│   ├── agent_graph.py            # NEW: Multi-tool LangGraph agent
│   ├── tools.py                  # NEW: Search tool definitions
│   ├── deploy_vespa.py           # Vespa Cloud deploy & feed
│   ├── test_integration.py       # NEW: Integration tests
│   ├── INTEGRATION_GUIDE.md      # NEW: Detailed documentation
│   ├── requirements.txt
│   ├── .env.example
│   ├── Dockerfile
│   └── README.md
├── frontend/                     # Next.js (baserat på yoziru/nextjs-vllm-ui)
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── TransparensAccordion.tsx
│   │   │   └── ThemeToggle.tsx
│   │   └── lib/
│   ├── .env.local.example
│   ├── Dockerfile
│   ├── package.json
│   └── README.md
├── docker-compose.yml
├── .gitignore
└── README.md
```
## Vanliga problem & lösningar

- **vLLM startar inte** → Kolla `nvidia-smi`, prova mindre modell eller `--quantization gptq`
- **Vespa 401/403** → Kontrollera cert/key-paths i `.env`
- **Inga relevanta källor** → Feed mer data i `deploy_vespa.py` eller testa med queries som matchar innehållet
- **Frontend hittar inte backend** → Kontrollera `NEXT_PUBLIC_API_BASE_URL=http://localhost:8001` i `frontend/.env.local`

## Docker (Valfritt)

För att köra hela stacken med Docker Compose:

```bash
# Skapa .env file med dina Vespa credentials
cp backend/.env.example backend/.env
# Redigera backend/.env med dina uppgifter

# Starta alla services
docker-compose up -d

# Se logs
docker-compose logs -f

# Stoppa
docker-compose down
```

**OBS:** vLLM måste köras separat på host-maskinen för GPU-åtkomst.

## API Endpoints

### Backend (http://localhost:8001)

- `GET /` - Health check
- `GET /health` - Detaljerad health check med tool availability
- `GET /config` - Visa aktuell konfiguration och tools
- `POST /chat` - Main chat endpoint med multi-tool search

Exempel med nya features:
```bash
# Standard request med alla tools aktiverade
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Vad är de senaste AI-nyheterna?"}
    ],
    "use_tools": true,
    "stream": true
  }'

# Legacy mode (endast Vespa RAG)
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Vad är AI-risker?"}
    ],
    "use_tools": false
  }'
```

## Roadmap – nästa steg

- [x] Multi-tool web search (Tavily, DuckDuckGo, Vespa) ✅ v0.3
- [x] Parallel tool execution med LangGraph ✅ v0.3
- [x] Streaming responses från vLLM till frontend ✅ v0.2
- [x] DeerFlow integration - Multi-agent architecture ✅ deep-oneseek branch
- [ ] Lägg till multi-LLM compare/debatt (parallella noder i LangGraph)
- [ ] Blockchain-logging (hasha steg → Sepolia testnet)
- [ ] Fler verktyg: X/Twitter search, code execution, calculator
- [ ] Användarnycklar & rate limiting
- [ ] Deploy till cloud (Railway/Fly.io för backend, Vercel för frontend)
- [ ] Bättre felhantering och retry-logik med exponential backoff

## Dokumentation

- [📖 QUICKSTART.md](QUICKSTART.md) - Nybörjarguide för installation
- [🔧 backend/INTEGRATION_GUIDE.md](backend/INTEGRATION_GUIDE.md) - Detaljerad guide för multi-tool integration
- [🦌 backend/DEER_FLOW_INTEGRATION.md](backend/DEER_FLOW_INTEGRATION.md) - DeerFlow integration och multi-agent patterns
- [🏗️ ARCHITECTURE.md](ARCHITECTURE.md) - Systemarkitektur och data flow
- [🐛 TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Vanliga problem och lösningar
- [📄 DEER_FLOW_ATTRIBUTION.md](DEER_FLOW_ATTRIBUTION.md) - DeerFlow license och attribution

## Licens

MIT (baserat på [nextjs-vllm-ui](https://github.com/yoziru/nextjs-vllm-ui) och öppen kod från LangChain/Vespa)

Integrerar arkitektoniska koncept från [ByteDance's DeerFlow](https://github.com/bytedance/deer-flow) (MIT License) - se [DEER_FLOW_ATTRIBUTION.md](DEER_FLOW_ATTRIBUTION.md) för detaljer.

Skapad med ❤️ i Karlsborg, Sverige – [@r_frojd](https://github.com/r_frojd)

Lycka till med bygget – feedback välkommen!
