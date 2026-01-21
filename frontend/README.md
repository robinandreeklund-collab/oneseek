# OneSeek.ai Frontend

Next.js frontend för OneSeek.ai, baserad på [yoziru/nextjs-vllm-ui](https://github.com/yoziru/nextjs-vllm-ui) och anpassad för att fungera med FastAPI backend istället för direkt vLLM-integration.

## Funktioner

- ✅ **Streaming chat interface** med real-time token-visning
- ✅ **Dark/Light mode** med localStorage-persistens
- ✅ **Chat history** sparas lokalt i webbläsaren
- ✅ **Transparens-accordion** visar:
  - Hämtade dokument från Vespa
  - LangGraph processteg
  - Raw prompt och LLM-svar
- ✅ **shadcn/ui components** för konsistent design
- ✅ **Responsive design** fungerar på desktop och mobile

## Anpassningar från Original

### 1. API Route (`/api/chat`)
- **Före**: Kallade direkt vLLM via OpenAI SDK
- **Efter**: Forwarding till FastAPI backend på `http://localhost:8001/chat`
- **Fördel**: RAG-funktionalitet via Vespa + LangGraph orchestration

### 2. Ny Komponent: TransparensAccordion
- Visar retrieved documents från Vespa
- Visar LangGraph workflow steps
- Kollapserbar för att inte ta upp för mycket plats

### 3. Environment Variables
- `NEXT_PUBLIC_BACKEND_URL`: FastAPI backend URL (default: http://localhost:8001)

## Installation

### Förutsättningar

- Node.js 18+ och yarn/npm
- FastAPI backend igång på port 8001

### Snabbstart

```bash
# Installera dependencies
yarn install
# eller
npm install

# Kopiera environment-filen
cp .example.env .env.local

# Starta development server
yarn dev
# eller
npm run dev
```

Öppna [http://localhost:3000](http://localhost:3000) i din webbläsare.

## Konfiguration

### Environment Variables

Skapa `.env.local` från `.example.env`:

```bash
# Backend URL för OneSeek.ai FastAPI server
NEXT_PUBLIC_BACKEND_URL="http://localhost:8001"

# (Optional) vLLM URL om du vill köra direkt mot vLLM
VLLM_URL="http://localhost:8000"
```

## Utveckling

### Projektstruktur

```
frontend/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   └── chat/
│   │   │       └── route.ts          # Forwarding till FastAPI backend
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── chat/                     # Chat-komponenter från original
│   │   ├── ui/                       # shadcn/ui komponenter
│   │   ├── transparens-accordion.tsx # NY: Visar källor och steg
│   │   ├── sidebar.tsx
│   │   ├── settings.tsx
│   │   └── ...
│   ├── lib/
│   │   └── utils.ts
│   └── providers/
│       └── theme-provider.tsx
├── public/
├── package.json
└── tailwind.config.ts
```

### Lägga till Nya Funktioner

#### Exempel: Anpassa TransparensAccordion

```typescript
// src/components/transparens-accordion.tsx
export function TransparensAccordion({
  retrieved = [],
  steps = [],
  prompt,
  response,
}: TransparensAccordionProps) {
  // Din anpassning här
}
```

#### Exempel: Modifiera Chat API Call

```typescript
// src/app/api/chat/route.ts
export async function POST(req: Request) {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8001";
  
  const response = await fetch(`${backendUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages: messages,
      stream: true,
      // Lägg till fler parametrar här
    }),
  });
  
  return new Response(response.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
    },
  });
}
```

## Bygga för Produktion

```bash
# Bygg optimerad production build
yarn build
# eller
npm run build

# Starta production server
yarn start
# eller
npm start
```

## Docker

Kör frontend i Docker-container:

```bash
# Bygg image
docker build -t oneseek-frontend .

# Kör container
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_BACKEND_URL=http://backend:8001 \
  oneseek-frontend
```

## Felsökning

### Problem: "Cannot connect to backend"

**Lösning:**
1. Kontrollera att FastAPI backend kör på port 8001:
   ```bash
   curl http://localhost:8001/health
   ```
2. Verifiera `.env.local` har rätt `NEXT_PUBLIC_BACKEND_URL`

### Problem: "Streaming fungerar inte"

**Lösning:**
1. Kontrollera att backend returnerar `Content-Type: text/event-stream`
2. Verifiera att `stream: true` skickas i request body

### Problem: "TransparensAccordion visas inte"

**Lösning:**
Backend måste returnera SSE events med följande format:
```
event: retrieved
data: {"docs": [...]}

event: step
data: {"step": "retrieve"}

event: token
data: {"token": "Hello"}
```

## Attribution

Detta projekt är baserat på [yoziru/nextjs-vllm-ui](https://github.com/yoziru/nextjs-vllm-ui) (MIT License) och anpassat för OneSeek.ai med RAG-funktionalitet via Vespa och LangGraph.

## License

MIT License - Se LICENSE-filen i root-katalogen.
