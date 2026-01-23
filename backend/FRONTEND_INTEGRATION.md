# Frontend Integration Guide for Source Display

This guide explains how to implement the "Web search completed · X sources" feature with an expandable sidebar, similar to qwen.ai.

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

### 1. Parse Metadata

Listen for the data event (type `2:`) from the streaming response:

```typescript
const handleStreamData = (data: any[]) => {
  const metadata = data[0];
  const sourceCount = metadata.source_count || 0;
  const sources = metadata.retrieved || [];
  
  if (sourceCount > 0) {
    setSourceInfo({
      count: sourceCount,
      sources: sources
    });
  }
};
```

### 2. Display Source Badge

Show a badge when sources are available:

```tsx
{sourceInfo.count > 0 && (
  <button 
    onClick={() => setShowSidebar(true)}
    className="source-badge"
  >
    Web search completed · {sourceInfo.count} sources
  </button>
)}
```

### 3. Expandable Sidebar

When the badge is clicked, show a sidebar with source details:

```tsx
<Sidebar isOpen={showSidebar} onClose={() => setShowSidebar(false)}>
  <h2>Sources ({sourceInfo.count})</h2>
  {sourceInfo.sources.map((source, index) => (
    <SourceCard key={index}>
      <h3>{source.title}</h3>
      {source.url && (
        <a href={source.url} target="_blank" rel="noopener noreferrer">
          {source.url}
        </a>
      )}
      <p>{source.content.substring(0, 200)}...</p>
      {source.relevance && (
        <span className="relevance">
          Relevance: {(source.relevance * 100).toFixed(0)}%
        </span>
      )}
    </SourceCard>
  ))}
</Sidebar>
```

### 4. Styling Example

```css
.source-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  background: #f0f0f0;
  border: 1px solid #ddd;
  border-radius: 16px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.source-badge:hover {
  background: #e0e0e0;
  border-color: #ccc;
}

.sidebar {
  position: fixed;
  right: 0;
  top: 0;
  height: 100vh;
  width: 400px;
  background: white;
  box-shadow: -2px 0 8px rgba(0,0,0,0.1);
  transform: translateX(100%);
  transition: transform 0.3s ease;
  overflow-y: auto;
}

.sidebar.open {
  transform: translateX(0);
}
```

## Example: Complete React Component

```tsx
import { useState } from 'react';
import { useChat } from 'ai/react';

export default function ChatWithSources() {
  const [sourceInfo, setSourceInfo] = useState({ count: 0, sources: [] });
  const [showSidebar, setShowSidebar] = useState(false);
  
  const { messages, input, handleInputChange, handleSubmit } = useChat({
    api: '/api/chat',
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

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map(message => (
          <div key={message.id} className={`message ${message.role}`}>
            <div className="content">{message.content}</div>
            {message.role === 'assistant' && sourceInfo.count > 0 && (
              <button 
                onClick={() => setShowSidebar(true)}
                className="source-badge"
              >
                🔍 Web search completed · {sourceInfo.count} sources
              </button>
            )}
          </div>
        ))}
      </div>
      
      <form onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="Ask anything..."
        />
        <button type="submit">Send</button>
      </form>
      
      <SourceSidebar 
        isOpen={showSidebar}
        sources={sourceInfo.sources}
        onClose={() => setShowSidebar(false)}
      />
    </div>
  );
}
```

## Backend API Enhancements Already Implemented

1. **source_count**: Number of sources returned (for easy display)
2. **url field**: Each source includes its URL for linking
3. **source field**: Identifies which tool (tavily_search, browse_page, etc.) provided the result
4. **Metadata in stream**: Sources sent as data annotation before content starts

## Notes

- The backend sends metadata BEFORE the content starts streaming
- Parse the `2:` data event to extract source information
- Store source data in component state for display
- The sidebar can be toggled independently of the chat
- Sources include full content for preview (truncated on frontend if needed)
