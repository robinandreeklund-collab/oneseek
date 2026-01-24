# ActionBlock Integration - UI Preview

## Visual Design

### 1. Completed Tool Actions (Collapsed by Default)

```
┌────────────────────────────────────────────────────────────────┐
│ > Actions                                   3 tool(s) used     │
└────────────────────────────────────────────────────────────────┘
```

### 2. Expanded Tool Actions

```
┌────────────────────────────────────────────────────────────────┐
│ ∨ Actions                                   3 tool(s) used     │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ╭────────────────────────────────────────────────────────╮   │
│  │ 🔍  web_search                                  2.34s  │   │
│  │     Input: query="weather in Stockholm"               │   │
│  │     Output: 5 result(s)                               │   │
│  ╰────────────────────────────────────────────────────────╯   │
│                                                                │
│  ╭────────────────────────────────────────────────────────╮   │
│  │ 🌐  browse_page                                 1.87s  │   │
│  │     Input: url="https://smhi.se/en/weather"           │   │
│  │     Output: 1 result(s)                               │   │
│  ╰────────────────────────────────────────────────────────╯   │
│                                                                │
│  ╭────────────────────────────────────────────────────────╮   │
│  │ 🌤️  smhi_api                                    0.56s  │   │
│  │     Input: location="Stockholm"                       │   │
│  │     Output: 1 result                                  │   │
│  ╰────────────────────────────────────────────────────────╯   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 3. Live Mode (Tools Running)

```
┌────────────────────────────────────────────────────────────────┐
│ ∨ Actions                                   2 tool(s) invoked  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ╭────────────────────────────────────────────────────────╮   │
│  │ 🔍  web_search  ⟳ Running...                          │   │
│  │     Input: query="weather in Stockholm"               │   │
│  ╰────────────────────────────────────────────────────────╯   │
│                                                                │
│  ╭────────────────────────────────────────────────────────╮   │
│  │ 🌐  browse_page  ⟳ Running...                         │   │
│  │     Input: url="https://smhi.se/en/weather"           │   │
│  ╰────────────────────────────────────────────────────────╯   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Color Scheme

### Tool Type Colors (Tailwind CSS)
- **🔍 web_search** (blue): `border-blue-400`, `text-blue-400`, `bg-blue-400/10`
- **🌐 browse_page** (green): `border-green-400`, `text-green-400`, `bg-green-400/10`
- **🌤️ smhi_api** (purple): `border-purple-400`, `text-purple-400`, `bg-purple-400/10`
- **Default** (gray): `border-gray-400`, `text-gray-400`, `bg-gray-400/10`

## Component Structure

```
ActionBlock
├── Header (collapsible button)
│   ├── Chevron icon (rotates on expand/collapse)
│   ├── "Actions" label
│   └── Status text ("X tool(s) used" or "X tool(s) invoked")
│
└── Body (conditional on isOpen)
    └── For each tool action:
        ├── Tool card (with color-coded border & background)
        │   ├── Icon + Display name + Status
        │   ├── Duration (if completed)
        │   ├── Spinner (if running)
        │   ├── Input parameters (formatted)
        │   └── Output summary (if completed)
```

## Behavior

1. **During Tool Execution:**
   - Block is automatically expanded
   - Shows spinner next to running tools
   - Updates in real-time as tools complete

2. **After Completion:**
   - Block can be collapsed/expanded by user
   - Shows final timing for each tool
   - Displays output summary

3. **Empty State:**
   - Block does not render if no tools were invoked

## Integration Points

1. **Backend (agent_graph.py):**
   - Tracks tool invocations with `_map_tool_name()`
   - Stores in `tool_actions` array in state
   - Includes timing, input, output, status

2. **Backend (app.py):**
   - Sends `tool_actions` in metadata stream
   - Format: `2:{json.dumps([metadata])}\n`

3. **Frontend (chat-page.tsx):**
   - Parses `tool_actions` from stream data
   - Stores in `messageToolActions` state
   - Passes to ChatList

4. **Frontend (chat-list.tsx):**
   - Renders `<ActionBlock>` for each message
   - Sets `live` prop based on isLoading state

5. **Frontend (action-block.tsx):**
   - Displays tool invocations with styling
   - Handles expand/collapse
   - Shows live updates during streaming
