# Frontend Integration Guide for Source Display

This guide explains how to implement the "Web search completed · X sources" feature with an expandable sidebar, matching the oneseek.ai design system.

## Backend Data Format

When streaming responses, the backend sends metadata in Vercel AI SDK format:

```
2:[{"steps": [...], "retrieved": [...], "source_count": 10}]
```

### Retrieved Document Format

Each document in the `retrieved` array contains:

```json
{
  "title": "Article Title",
  "content": "Article content or excerpt...",
  "url": "https://example.com/article",
  "relevance": 0.95,
  "source": "tavily_search"  // Optional: which tool provided this
}
```

## Frontend Implementation

### 1. Update chat-list.tsx

Add state for tracking sources in the ChatList component:

```typescript
// Add to ChatList interface
interface ChatListProps {
  messages: Message[];
  isLoading: boolean;
  sourceInfo?: { count: number; sources: any[] };
  onSourceClick?: () => void;
}

// In the assistant message section, after MessageToolbar:
{message.role === "assistant" && sourceInfo && sourceInfo.count > 0 && (
  <button
    onClick={onSourceClick}
    className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground border border-border rounded-md hover:bg-accent/50 transition-colors"
  >
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
    Web search completed · {sourceInfo.count} sources
  </button>
)}
```

### 2. Create Source Sidebar Component

Create a new file `src/components/chat/source-sidebar.tsx`:

```tsx
import React from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ExternalLink } from 'lucide-react';

interface Source {
  title: string;
  content: string;
  url?: string;
  relevance?: number;
  source?: string;
}

interface SourceSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  sources: Source[];
  count: number;
}

export default function SourceSidebar({ isOpen, onClose, sources, count }: SourceSidebarProps) {
  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Sources ({count})</SheetTitle>
        </SheetHeader>
        
        <div className="mt-6 space-y-4">
          {sources.map((source, index) => (
            <Card key={index} className="hover:bg-accent/50 transition-colors">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold line-clamp-2">
                  {source.title}
                </CardTitle>
                {source.url && (
                  <CardDescription className="flex items-center gap-1 text-xs">
                    <ExternalLink className="w-3 h-3" />
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline truncate"
                    >
                      {new URL(source.url).hostname}
                    </a>
                  </CardDescription>
                )}
              </CardHeader>
              
              <CardContent className="pb-4">
                <p className="text-sm text-muted-foreground line-clamp-4">
                  {source.content}
                </p>
                
                <div className="mt-3 flex items-center justify-between text-xs">
                  {source.relevance && (
                    <span className="text-muted-foreground">
                      Relevance: {(source.relevance * 100).toFixed(0)}%
                    </span>
                  )}
                  {source.source && (
                    <span className="px-2 py-0.5 bg-secondary rounded-sm text-secondary-foreground">
                      {source.source.replace('_', ' ')}
                    </span>
                  )}
                </div>
                
                {source.url && (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-3 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                  >
                    Visit source
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

### 3. Update chat.tsx

Add state management for sources:

```tsx
import { useState } from 'react';
import SourceSidebar from './source-sidebar';

export default function Chat({ ... }: ChatProps & ChatTopbarProps) {
  const [sourceInfo, setSourceInfo] = useState<{ count: number; sources: any[] }>({ 
    count: 0, 
    sources: [] 
  });
  const [showSourceSidebar, setShowSourceSidebar] = useState(false);

  return (
    <div className="flex flex-col justify-between w-full h-full">
      <ChatTopbar ... />
      
      <ChatList
        messages={messages}
        isLoading={isLoading}
        sourceInfo={sourceInfo}
        onSourceClick={() => setShowSourceSidebar(true)}
      />
      
      <ChatBottombar ... />
      
      <SourceSidebar
        isOpen={showSourceSidebar}
        onClose={() => setShowSourceSidebar(false)}
        sources={sourceInfo.sources}
        count={sourceInfo.count}
      />
    </div>
  );
}
```

### 4. Update chat-page.tsx

Parse metadata from the streaming response:

```tsx
const { messages, input, handleInputChange, handleSubmit, isLoading, stop, error, data } = 
  useChat({
    api: "/api/chat",
    // ... other options
    onFinish: (message, { data }) => {
      if (data && data[0]) {
        const metadata = data[0];
        setSourceInfo({
          count: metadata.source_count || 0,
          sources: metadata.retrieved || []
        });
      }
    }
  });
```

## Design System Compliance

The implementation follows oneseek.ai's existing design patterns:

**Colors & Theming:**
- Uses Tailwind CSS with shadcn/ui components
- Respects light/dark mode via `dark:` prefixes
- Uses design tokens: `text-muted-foreground`, `border-border`, `bg-accent`

**Typography:**
- Font sizes: `text-sm` (14px), `text-xs` (12px), `text-base` (16px)
- Font weights: `font-semibold` for titles
- Line clamping: `line-clamp-2`, `line-clamp-4` for truncation

**Spacing:**
- Consistent padding: `px-3 py-1.5` for buttons, `p-6` for cards
- Gap spacing: `gap-1`, `gap-1.5`, `gap-3`, `gap-4`
- Margin: `mt-2`, `mt-3`, `mt-6` for vertical rhythm

**Borders & Radius:**
- Border radius: `rounded-md` (1rem base)
- Border color: `border-border`
- Subtle borders on cards and buttons

**Interactions:**
- Hover states: `hover:bg-accent/50`, `hover:text-foreground`
- Transitions: `transition-colors`
- Focus rings: handled by shadcn/ui components

**Components:**
- Uses existing `Sheet` component for sidebar
- Uses existing `Card` components for source items
- Matches `Button` variants and styling
- Consistent with `MessageToolbar` placement

## Backend API Enhancements Already Implemented

1. **source_count**: Number of sources returned (for easy display)
2. **url field**: Each source includes its URL for linking
3. **source field**: Identifies which tool (tavily_search, browse_page, etc.) provided the result
4. **Metadata in stream**: Sources sent as data annotation before content starts

## Notes

- The backend sends metadata BEFORE the content starts streaming
- Parse the `2:` data event to extract source information
- Store source data in component state for display
- The Sheet component provides the sidebar with proper animations
- Uses existing shadcn/ui components for consistency
- All styling matches the current oneseek.ai design system
