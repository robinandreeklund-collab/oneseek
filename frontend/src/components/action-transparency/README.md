# Action Transparency Design Proposals

## Översikt

Dessa designförslag visar hur verktygsanrop (web_search, browse_page, smhi_api) kan visualiseras i OneSeek-chatten med samma stil och designspråk som den befintliga "Thoughts"-sektionen.

## Designprinciper

Alla designs följer dessa principer:

✅ **Konsekvent med befintlig design** - Använder samma visuella språk som ThinkBlock-komponenten
✅ **Samma designsystem** - shadcn/ui komponenter + Tailwind CSS
✅ **Samma animationer** - Spinner, fade-in, kollapsbar funktionalitet
✅ **Samma färgpalett** - HSL-baserade färger från globals.css
✅ **Live-uppdateringar** - Stödjer streaming och real-time status

## Designförslag

### Design 1: Inline Actions (ActionBlock)

**Fil:** `frontend/src/components/action-transparency/ActionBlock.tsx`

**Beskrivning:**
Varje verktygsanrop visas inline med chatten, precis som "Thoughts"-blocken. Detta är den mest integrerade lösningen som passar naturligt in i konversationsflödet.

**Funktioner:**
- 🎨 Unika färger per verktyg (blå för web_search, grön för browse_page, lila för smhi_api)
- ⏱️ Live-läge med timer för pågående anrop
- 📦 Kollapsbar för slutförda anrop
- 🔄 Stöder alla statusar: pending, running, complete, error
- 📊 Visar input, output och metadata

**Användning:**
```tsx
<ActionBlock 
  action={{
    tool: "web_search",
    status: "complete",
    input: "latest AI research",
    output: "Found 127 sources...",
    duration: 1.24,
    metadata: { sources: "127", cached: "15" }
  }}
/>
```

**När passar den:**
- Perfekt för att visa enskilda verktygsanrop inline med konversationen
- Bäst när verktyg körs sekventiellt, ett i taget
- Ger mest konsistent upplevelse med befintliga "Thoughts"

---

### Design 2: Timeline View (ActionTimeline)

**Fil:** `frontend/src/components/action-transparency/ActionTimeline.tsx`

**Beskrivning:**
Visar alla verktygsanrop i en vertikal tidslinje med visuella kopplingar. Bra för att visa kronologisk ordning och dataflöde.

**Funktioner:**
- 📍 Visuell tidslinje med kopplingslinjer
- 🎯 Färgkodade ikoner för varje verktyg
- 📝 Kompakt visning av alla anrop
- ⏰ Visar timing och status för varje steg
- 🔗 Tydligt visar sekventiellt flöde

**Användning:**
```tsx
<ActionTimeline 
  actions={[
    { tool: "web_search", status: "complete", ... },
    { tool: "browse_page", status: "running", ... },
    { tool: "smhi_api", status: "pending", ... }
  ]}
/>
```

**När passar den:**
- När flera verktyg körs i sekvens
- För att visa kompletta arbetsflöden
- När användare vill se alla steg på en gång
- Bra för "replay" av slutförda konversationer

---

### Design 3: Compact Cards (ActionCards)

**Fil:** `frontend/src/components/action-transparency/ActionCards.tsx`

**Beskrivning:**
Visar verktygsanrop som kompakta kort i ett responsivt rutnät. Perfekt för parallella verktygsanrop.

**Funktioner:**
- 🎴 Kompakta kort i responsivt rutnät
- 🖱️ Klickbara för att expandera detaljer
- 🎭 Animerade statusikoner
- 📱 Responsiv layout (1-3 kolumner)
- ⚡ Bra för många samtidiga verktyg

**Användning:**
```tsx
<ActionCards 
  actions={[
    { tool: "web_search", status: "complete", ... },
    { tool: "browse_page", status: "complete", ... },
    { tool: "smhi_api", status: "running", ... }
  ]}
/>
```

**När passar den:**
- När flera verktyg körs parallellt
- För att spara vertikalt utrymme
- När man vill ge snabb översikt
- Bra för desktop med mycket skärmutrymme

---

## Verktyg och färgkodning

Varje verktyg har sin unika färg för enkel identifiering:

| Verktyg | Ikon | Färg | Användning |
|---------|------|------|-----------|
| `web_search` | 🔍 | Blå | Söker på webben efter information |
| `browse_page` | 🌐 | Grön | Läser och analyserar webbsidor |
| `smhi_api` | 🌤️ | Lila | Hämtar väderdata från SMHI |

## Status och visuella indikatorer

Varje verktygsanrop kan ha följande statusar:

| Status | Ikon | Beteende |
|--------|------|----------|
| `pending` | ⏳ | Väntar på att köras, ingen timer |
| `running` | ⚙️ | Körs just nu, visar live timer + spinner |
| `complete` | ✅ | Slutförd, visar total tid |
| `error` | ❌ | Misslyckades, röd färg |

## Integration med befintlig kod

### 1. Lägg till i chat-list.tsx

```tsx
import ActionBlock from "@/components/action-transparency/ActionBlock";

// I render-funktionen, liknande hur ThinkBlock används:
function processActionTags(content: string, isLoading: boolean) {
  const actionOpen = content.indexOf("<action>");
  const actionClose = content.indexOf("</action>");
  
  if (actionOpen !== -1 && actionClose !== -1) {
    const before = content.slice(0, actionOpen);
    const actionData = content.slice(actionOpen + 8, actionClose);
    const after = content.slice(actionClose + 9);
    
    // Parse action JSON
    const action = JSON.parse(actionData);
    
    return [
      before,
      <ActionBlock key="action" action={action} live={isLoading} />,
      after
    ];
  }
  
  return [content];
}
```

### 2. Backend skickar verktygsdata

I `backend/agent.py`, när ett verktyg körs:

```python
# När ett verktyg startar
action_data = {
    "tool": "web_search",
    "status": "running",
    "input": query,
    "duration": 0
}
yield f"<action>{json.dumps(action_data)}</action>"

# När det slutförs
action_data["status"] = "complete"
action_data["output"] = result
action_data["duration"] = elapsed_time
action_data["metadata"] = {"sources": len(sources)}
yield f"<action>{json.dumps(action_data)}</action>"
```

### 3. Streaming support

Komponenten stödjer live-uppdateringar:
- När `live=true` eller `status="running"` visas en live timer
- Spinner animation körs automatiskt
- Komponenten är kollapsbar när den är klar

## Demo

För att se alla designs i aktion, navigera till:

```
http://localhost:3000/action-demo
```

Denna sida visar:
- Alla tre designförslagen
- Exempel med olika verktyg
- Olika statusar (pending, running, complete)
- Live-uppdateringar
- Implementeringsexempel

## Rekommendation

**För OneSeek rekommenderar vi Design 1 (Inline Actions)** eftersom:

1. ✅ **Mest konsistent** - Matchar exakt hur "Thoughts" fungerar idag
2. ✅ **Enklast integration** - Drop-in replacement liknande ThinkBlock
3. ✅ **Bästa UX** - Följer naturligt konversationsflöde
4. ✅ **Flexibel** - Fungerar för både sekventiella och parallella verktyg
5. ✅ **Beprövad** - Samma mönster som redan används

Men alla tre designs kan användas - eller kombineras för olika use cases!

## Tekniska detaljer

### Dependencies

Alla komponenter använder:
- React (från befintlig Next.js setup)
- Tailwind CSS (befintlig konfiguration)
- shadcn/ui komponenter (Collapsible, Tabs, etc.)
- react-markdown för output-rendering
- lucide-react för ikoner (ChevronDown)

Inga nya dependencies behövs!

### Filstruktur

```
frontend/src/
├── components/
│   └── action-transparency/
│       ├── ActionBlock.tsx       # Design 1: Inline
│       ├── ActionTimeline.tsx    # Design 2: Timeline
│       └── ActionCards.tsx       # Design 3: Cards
└── app/
    └── action-demo/
        └── page.tsx              # Demo page
```

### TypeScript interface

```typescript
export interface ToolAction {
  tool: "web_search" | "browse_page" | "smhi_api";
  status: "pending" | "running" | "complete" | "error";
  input?: string;
  output?: string;
  duration?: number;
  metadata?: Record<string, any>;
}
```

## Nästa steg

1. ✅ **Granska designs** - Öppna `/action-demo` och testa alla tre
2. ⏭️ **Välj design** - Bestäm vilken som passar bäst
3. ⏭️ **Integrera backend** - Lägg till `<action>` tags i LangGraph responses
4. ⏭️ **Uppdatera frontend** - Lägg till parsing i chat-list.tsx
5. ⏭️ **Testa med riktiga verktyg** - Kör med faktiska web_search, browse_page, smhi_api anrop

## Frågor?

Alla komponenter är färdiga att användas direkt i din befintliga frontend. De följer exakt samma mönster som ThinkBlock och integreras sömlöst med din nuvarande kod!
