# Code Preview Integration Guide

This guide shows how to integrate the `CodePreview` component into the chat interface.

## Component Location

The component is located at: `frontend/src/components/code-preview.tsx`

## Basic Usage

```tsx
import CodePreview from "@/components/code-preview";

// In your chat message renderer:
<CodePreview
  projectName="My Next.js App"
  previewUrl="http://localhost:3001"
  code={generatedCode}
  language="javascript"
  live={true}
/>
```

## Integration into Chat Messages

### Step 1: Detect Code Tool Usage

When processing chat messages, check if the agent used any code tools:

```tsx
// In your message processing logic
const hasCodeTools = message.tool_calls?.some(tool => 
  ['linux_sandbox_tool', 'file_system_tool', 'react_sandbox_tool'].includes(tool.name)
);
```

### Step 2: Extract Preview Information

Parse tool call results to extract preview information:

```tsx
const getPreviewInfo = (toolCalls) => {
  const reactSandboxCall = toolCalls?.find(
    call => call.name === 'react_sandbox_tool' && call.args?.action === 'preview'
  );
  
  if (reactSandboxCall) {
    return {
      projectName: reactSandboxCall.args.project_name,
      previewUrl: `http://localhost:${reactSandboxCall.args.port || 3001}`,
    };
  }
  
  return null;
};
```

### Step 3: Render Preview Component

Add the component to your message display:

```tsx
// In chat-list.tsx or similar
import CodePreview from "@/components/code-preview";

function MessageWithCodePreview({ message }) {
  const previewInfo = getPreviewInfo(message.tool_calls);
  
  return (
    <div className="message">
      {/* Regular message content */}
      <div className="message-content">
        {message.content}
      </div>
      
      {/* Code preview if available */}
      {previewInfo && (
        <div className="mt-4">
          <CodePreview
            projectName={previewInfo.projectName}
            previewUrl={previewInfo.previewUrl}
            live={message.is_streaming}
          />
        </div>
      )}
      
      {/* Action blocks */}
      {message.actions && (
        <ActionBlock actions={message.actions} />
      )}
    </div>
  );
}
```

## Advanced: Multi-File Display

For showing multiple code files:

```tsx
import { MultiFileCodePreview } from "@/components/code-preview";

const codeFiles = [
  {
    name: "app/page.tsx",
    content: "export default function Home() { ... }",
    language: "typescript"
  },
  {
    name: "app/layout.tsx",
    content: "export default function RootLayout() { ... }",
    language: "typescript"
  }
];

<MultiFileCodePreview files={codeFiles} />
```

## Styling

The component uses Tailwind CSS and shadcn/ui components. It's styled to match the existing chat interface with:

- Consistent card styling
- Dark mode support
- Responsive layout
- Animated loading states

## Props Reference

### CodePreview

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `projectName` | `string` | `"Preview"` | Name displayed in header |
| `previewUrl` | `string` | `undefined` | URL of the live preview |
| `code` | `string` | `undefined` | Source code to display |
| `language` | `string` | `"javascript"` | Syntax highlighting language |
| `live` | `boolean` | `false` | Show live indicator |
| `onRefresh` | `() => void` | `undefined` | Custom refresh handler |

### MultiFileCodePreview

| Prop | Type | Description |
|------|------|-------------|
| `files` | `CodeFile[]` | Array of file objects with `name`, `content`, `language` |

## Example: Full Integration

```tsx
// frontend/src/components/chat/chat-list.tsx

import React from "react";
import CodePreview from "@/components/code-preview";
import ActionBlock from "@/components/action-block";

interface Message {
  role: string;
  content: string;
  tool_calls?: ToolCall[];
  is_streaming?: boolean;
}

interface ToolCall {
  name: string;
  args: Record<string, any>;
  result?: string;
}

function ChatMessage({ message }: { message: Message }) {
  // Check if message contains code tool usage
  const codeToolCall = message.tool_calls?.find(
    call => call.name === 'react_sandbox_tool'
  );
  
  // Extract preview URL from result
  const previewMatch = codeToolCall?.result?.match(/http:\/\/localhost:\d+/);
  const previewUrl = previewMatch ? previewMatch[0] : undefined;
  
  // Extract code from file_system_tool write operations
  const codeWrite = message.tool_calls?.find(
    call => call.name === 'file_system_tool' && call.args?.operation === 'write'
  );
  
  return (
    <div className="flex flex-col gap-4 p-4">
      {/* Message content */}
      <div className="prose dark:prose-invert">
        {message.content}
      </div>
      
      {/* Code preview if React sandbox was used */}
      {previewUrl && (
        <CodePreview
          projectName={codeToolCall?.args?.project_name || "Preview"}
          previewUrl={previewUrl}
          code={codeWrite?.args?.content}
          language="typescript"
          live={message.is_streaming}
        />
      )}
      
      {/* Tool actions */}
      {message.tool_calls && message.tool_calls.length > 0 && (
        <ActionBlock 
          actions={message.tool_calls.map(call => ({
            tool_name: call.name,
            display_name: call.name,
            status: "completed",
            input: call.args,
            result: call.result
          }))}
        />
      )}
    </div>
  );
}

export default ChatMessage;
```

## Testing the Integration

1. Start the backend with code tools enabled
2. Ask a code-related question: "Create a simple React counter app"
3. The message should display with the CodePreview component
4. Click the tabs to see Preview, Code, and Terminal views
5. Use the refresh button to reload the preview
6. Click external link to open in new tab

## Notes

- The iframe sandbox attribute restricts execution for security
- Preview URLs should be localhost for development
- Production deployment would need proper CORS and security headers
- Terminal output is currently simulated (real-time logging would need WebSocket integration)

## Future Enhancements

- Real-time terminal output via WebSocket
- Code editor with live editing
- Multiple preview windows
- Preview history/snapshots
- Collaborative editing support
