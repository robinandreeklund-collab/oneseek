# OneSeek Frontend

This is the Next.js frontend for OneSeek.ai, based on the nextjs-vllm-ui project (MIT license) and adapted for RAG-enhanced chat via FastAPI backend.

## Features

- **Modern UI**: Built with Next.js 14+, shadcn/ui, and Tailwind CSS
- **Dark/Light Mode**: Toggle between themes with localStorage persistence
- **Chat History**: Automatic localStorage persistence of conversations
- **Transparency**: Accordion showing retrieved sources from Vespa and processing steps
- **Streaming Support**: Ready for streaming responses (currently using standard fetch)

## Setup

1. Install dependencies:
```bash
npm install
# or
yarn install
```

2. Create `.env.local` from the example:
```bash
cp .env.local.example .env.local
```

3. Start the development server:
```bash
npm run dev
# or
yarn dev
```

4. Open [http://localhost:3000](http://localhost:3000)

## Configuration

Edit `.env.local`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── layout.tsx          # Root layout with metadata
│   │   ├── page.tsx            # Main chat page
│   │   └── globals.css         # Global styles with CSS variables
│   ├── components/
│   │   ├── ChatInterface.tsx   # Main chat component
│   │   ├── TransparensAccordion.tsx  # Sources & steps accordion
│   │   └── ThemeToggle.tsx     # Dark/light mode toggle
│   └── lib/
│       └── utils.ts            # Utility functions (cn)
├── package.json
├── tailwind.config.ts
└── tsconfig.json
```

## Components

### ChatInterface
Main chat component with:
- Message display with role-based styling
- Input field with submit button
- localStorage persistence
- API integration with error handling

### TransparensAccordion
Expandable accordion showing:
- Processing steps from LangGraph
- Retrieved documents from Vespa with relevance scores
- Title and content preview for each source

### ThemeToggle
Simple toggle between light and dark mode with:
- System preference detection
- localStorage persistence
- Icon switching (Moon/Sun)

## API Integration

The frontend expects the following response format from `/chat`:

```typescript
{
  content: string;           // AI response text
  retrieved: Array<{         // Documents from Vespa
    title: string;
    content: string;
    relevance?: number;
  }>;
  steps: string[];           // Processing steps from agent
}
```

## License

Based on [nextjs-vllm-ui](https://github.com/yoziru/nextjs-vllm-ui) (MIT License)
