# OneSeek.ai MVP v0.2 – Lokal AI-chat med RAG & Transparens

**OneSeek.ai** är en agent-plattform i tidig MVP-fas med fokus på:
- Lokal LLM-inference via vLLM (på RTX 5090)
- Snygg ChatGPT-liknande frontend
- Retrieval-Augmented Generation (RAG) via Vespa Cloud
- Agent-flöde med LangGraph (hämta kontext → berika prompt → generera svar)
- Full transparens: visa retrieved källor, steg och metadata i UI

Målet är att bygga mot en unik plattform med **debatt/compare mellan modeller**, **blockchain-logging för verifierbarhet** och **multi-step agenter** – men denna MVP är minimal och körbar lokalt.

## Funktioner i denna MVP
- Streaming chat med lokal LLM (t.ex. Qwen2.5-14B-Instruct-AWQ eller Llama-3.1-8B)
- RAG-berikning: Hämtar relevanta snippets från Vespa Cloud innan svar genereras
- Transparens i UI: Accordion med källor, retrieved docs och raw prompt
- Enkel backend med FastAPI + LangGraph för orkestrering
- Inga externa API:er krävs för core (bara vLLM + Vespa Cloud dev-tier)

## Tech Stack
- **Inference**: vLLM (lokal på NVIDIA RTX 5090)
- **Frontend**: Next.js 14+ (App Router), shadcn/ui, Tailwind, Vercel AI SDK (baserat på [nextjs-vllm-ui](https://github.com/yoziru/nextjs-vllm-ui))
- **Backend / Agent**: FastAPI, LangGraph, LangChain
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
git clone https://github.com/ditt-användarnamn/oneseek-mvp.git
cd oneseek-mvp
2. Starta vLLM (separat terminal)
Skapa venv om du vill:
Bashpython -m venv venv
source venv/bin/activate
pip install vllm
Starta server (exempel med bra balans för RTX 5090):
Bashvllm serve Qwen/Qwen2.5-14B-Instruct-AWQ \
  --dtype auto \
  --quantization awq \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.92 \
  --host 0.0.0.0 --port 8000
Alternativt snabb modell:
Bashvllm serve meta-llama/Llama-3.1-8B-Instruct --port 8000
3. Setup Vespa Cloud

Gå till https://console.vespa-cloud.com → skapa konto & tenant (t.ex. "oneseek-mvp")
Hämta data-plane cert & key från Console → Security
I backend/ – kopiera .env.example till .env och fyll i:textVESPA_URL=https://ditt-app.ditt-tenant.vespa-cloud.net
VESPA_CERT_PATH=/path/to/certificate.pem
VESPA_KEY_PATH=/path/to/private-key.pem
VLLM_URL=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ
Deploya schema & feed testdata:Bashcd backend
pip install -r requirements.txt
python deploy_vespa.py

4. Starta backend (FastAPI + LangGraph)
Bashcd backend
uvicorn app:app --reload --port 8001
5. Starta frontend
Bashcd ../frontend
yarn install    # eller npm install
yarn dev        # eller npm run dev
Öppna http://localhost:3000
Skriv en fråga som matchar din testdata (t.ex. "Vad säger experter om AI-risker?") → svaret ska nu vara berikat med källor från Vespa.
Projektstruktur
textoneseek-mvp/
├── backend/
│   ├── app.py               # FastAPI-server
│   ├── agent.py             # LangGraph-definition
│   ├── deploy_vespa.py      # Vespa Cloud deploy & feed
│   ├── requirements.txt
│   └── .env.example
├── frontend/                # Next.js (klonad & anpassad från yoziru/nextjs-vllm-ui)
│   ├── src/
│   ├── .env.local
│   └── ...
├── README.md
└── .gitignore
Vanliga problem & lösningar

vLLM startar inte → Kolla nvidia-smi, prova mindre modell eller --quantization gptq
Vespa 401/403 → Kontrollera cert/key-paths i .env
Inga relevanta källor → Feed mer data i deploy_vespa.py eller testa med queries som matchar innehållet
Frontend hittar inte backend → Kontrollera NEXT_PUBLIC_API_BASE_URL=http://localhost:8001 i frontend/.env.local

Roadmap – nästa steg

Lägg till multi-LLM compare/debatt (parallella noder i LangGraph)
Blockchain-logging (hasha steg → Sepolia testnet)
Verktyg/tools i agenten (web search, code exec, etc.)
Användarnycklar & rate limiting
Deploy till cloud (Railway/Fly.io för backend, Vercel för frontend)

Licens
MIT (baserat på nextjs-vllm-ui och öppen kod från LangChain/Vespa)
Skapad med ❤️ i Karlsborg, Sverige – @r_frojd
Lycka till med bygget – feedback välkommen!
