# DeerFlow Integration med OneSeek VLLM

Detta är en integration av ByteDance's DeerFlow med OneSeek's lokala VLLM-setup.

## Snabbstart

### 1. Starta VLLM (i separat terminal)

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

### 2. Konfigurera DeerFlow

Konfigurationsfilen `conf.yaml` är redan konfigurerad för VLLM:

```yaml
BASIC_MODEL:
  base_url: "http://localhost:8000/v1"
  model: "Qwen/Qwen2.5-14B-Instruct-AWQ"
  api_key: "EMPTY"
```

### 3. Installera Python-dependencies

```bash
# Installera uv (rekommenderat)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Eller använd pip
pip install -r backend/requirements.txt
```

För DeerFlow-specifika dependencies, se `pyproject.toml`.

### 4. Installera Web UI dependencies

```bash
cd web
pnpm install  # eller npm install
```

### 5. Starta Backend

```bash
# Konsol-läge (utan Web UI)
python main.py

# Eller server-läge (för Web UI)
python server.py
# Eller med uvicorn
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Starta Web UI (i separat terminal)

```bash
cd web
pnpm dev  # eller npm run dev
```

Web UI är tillgänglig på http://localhost:3000

### 7. Alternativt: Använd bootstrap-skript

```bash
# Starta både backend och frontend i development-läge
./bootstrap.sh -d

# Windows
bootstrap.bat -d
```

## Filstruktur

```
oneseek/
├── conf.yaml              # DeerFlow konfiguration (VLLM)
├── .env                   # Miljövariabler
├── main.py                # DeerFlow konsol-läge
├── server.py              # DeerFlow FastAPI server
├── backend/
│   ├── deer_flow/         # DeerFlow source (src/)
│   ├── app.py             # OneSeek's original backend
│   └── agent_graph.py     # OneSeek's original agent
├── web/                   # DeerFlow Web UI
│   ├── src/
│   ├── package.json
│   └── ...
└── frontend/              # OneSeek's original frontend

```

## Viktiga skillnader från standard DeerFlow

1. **LLM Provider**: Använder lokal VLLM istället för OpenAI/Doubao
2. **Modell**: Qwen/Qwen2.5-14B-Instruct-AWQ (AWQ-quantized för RTX 5090)
3. **API Key**: "EMPTY" - ingen autentisering behövs för lokal VLLM
4. **Search**: DuckDuckGo som standard (fungerar utan API key)

## Konfiguration

### conf.yaml

Huvudkonfiguration för LLM-modeller. Redan konfigurerad för VLLM.

### .env

Miljövariabler för search APIs, RAG providers, etc.

För Tavily search (rekommenderat):
```bash
SEARCH_API=tavily
TAVILY_API_KEY=your_key_here
```

## Testa integration

1. Öppna http://localhost:3000 i webbläsaren
2. Skriv en fråga, t.ex: "What are the latest AI trends?"
3. DeerFlow kommer att:
   - Använda din lokala VLLM för inference
   - Söka information via DuckDuckGo
   - Generera ett omfattande svar med källor

## Felsökning

### Backend startar inte

- Kontrollera att VLLM körs på port 8000
- Testa: `curl http://localhost:8000/v1/models`

### Web UI kan inte ansluta

- Kontrollera att backend körs på port 8000 (server.py)
- Kontrollera CORS-inställningar i `.env`

### Import errors

- Installera alla dependencies: `pip install -r backend/requirements.txt`
- För DeerFlow: se `pyproject.toml` för fullständig lista

## Dokumentation

- [DeerFlow Original](https://github.com/bytedance/deer-flow)
- [DeerFlow Docs](https://deerflow.tech/)
- [DEER_FLOW_ATTRIBUTION.md](DEER_FLOW_ATTRIBUTION.md) - License information

## Licens

DeerFlow är licensierad under MIT License av Bytedance Ltd.
Se [DEER_FLOW_ATTRIBUTION.md](DEER_FLOW_ATTRIBUTION.md) för fullständiga detaljer.
