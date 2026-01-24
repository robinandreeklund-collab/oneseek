# Visual Overview - Action Transparency Designs

## Design 1: ActionBlock (Inline-stil) - REKOMMENDERAD ✨

Denna design integreras perfekt med befintlig "Thoughts"-funktionalitet.

### Slutförd webbsökning
```
┌─────────────────────────────────────────────────────────────┐
│ ▼  🔍 Webbsökning       Slutförde på 1.24s                 │
├─────────────────────────────────────────────────────────────┤
│   Input:                                                     │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ latest AI safety research 2026                      │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                              │
│   Resultat:                                                  │
│   Hittade 127 relevanta källor:                             │
│                                                              │
│   **Top resultat:**                                         │
│   - arxiv.org: 42 publikationer                            │
│   - ai-safety.org: 38 artiklar                             │
│   - anthropic.com: 21 blogginlägg                          │
│                                                              │
│   källor: 127    API-anrop: 3    cachade: 15              │
└─────────────────────────────────────────────────────────────┘
```

### Pågående anrop (Live)
```
┌─────────────────────────────────────────────────────────────┐
│ ▼  🌐 Läser sida        Kör i 2.50 sekunder  ⚙️            │
├─────────────────────────────────────────────────────────────┤
│   Input:                                                     │
│   ┌─────────────────────────────────────────────────────┐  │
│   │ https://arxiv.org/abs/2024.12345                    │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                              │
│   [Laddar innehåll...]                                      │
└─────────────────────────────────────────────────────────────┘
```

### Väntande anrop
```
┌─────────────────────────────────────────────────────────────┐
│ ▶  🌤️ SMHI Väder        Väntar...                          │
└─────────────────────────────────────────────────────────────┘
```

## Design 2: ActionTimeline (Tidslinje)

Visar kronologiskt flöde av alla verktygsanrop.

```
    │
    ├─ 🔍  Webbsökning
    │      ┌───────────────────────────────────┐
    │      │ ✅ Complete · 1.24s               │
    │      │ Input: latest AI research         │
    │      │ Found 127 sources                 │
    │      │ källor: 127  API-anrop: 3        │
    │      └───────────────────────────────────┘
    │
    ├─ 🌐  Läser sida
    │      ┌───────────────────────────────────┐
    │      │ ✅ Complete · 0.87s               │
    │      │ Input: https://arxiv.org/...      │
    │      │ Extracted: Advanced Safety...     │
    │      │ tecken: 15,234  länkar: 12       │
    │      └───────────────────────────────────┘
    │
    ├─ 🌤️  SMHI Väder
    │      ┌───────────────────────────────────┐
    │      │ ⚙️ Running                        │
    │      │ Input: Stockholm, 5 days          │
    │      │ Fetching data...                  │
    │      └───────────────────────────────────┘
    │
    ▼
```

## Design 3: ActionCards (Kompakta kort)

Responsivt rutnät, perfekt för parallella anrop.

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ 🔍           │  │ 🌐           │  │ 🌤️          │
│ Webbsökning  │  │ Läser sida   │  │ SMHI Väder   │
│ 1.24s        │  │ 0.87s        │  │ 0.42s        │
│ ✅ Klar  ▼  │  │ ✅ Klar  ▼  │  │ ✅ Klar  ▼  │
└──────────────┘  └──────────────┘  └──────────────┘

När expanderad:
┌──────────────────────────────────┐
│ 🔍 Webbsökning                   │
│ 1.24s                ✅ Klar  ▲ │
├──────────────────────────────────┤
│ Input:                           │
│ latest AI safety research 2026   │
│                                  │
│ Resultat:                        │
│ Hittade 127 relevanta källor... │
│                                  │
│ källor: 127  API-anrop: 3       │
└──────────────────────────────────┘
```

## Färgkodning

Varje verktyg har sin unika färg:

- **🔍 web_search** - Blå (#60a5fa)
  - För webbsökningar och informationshämtning
  
- **🌐 browse_page** - Grön (#4ade80)
  - För att läsa och analysera specifika webbsidor
  
- **🌤️ smhi_api** - Lila (#a855f7)
  - För väderprognoser från SMHI

## Status-indikatorer

| Status | Symbol | Färg | Animation |
|--------|--------|------|-----------|
| pending | ⏳ | Gul | - |
| running | ⚙️ | Blå | Spinner + timer |
| complete | ✅ | Grön | - |
| error | ❌ | Röd | - |

## Jämförelse med befintlig ThinkBlock

### ThinkBlock (Befintlig)
```
┌─────────────────────────────────────────────────────────────┐
│ ▼  Thoughts         Thought for 3.45 seconds               │
├─────────────────────────────────────────────────────────────┤
│   Let me analyze this question...                           │
│   1. First, I need to consider...                           │
│   2. Then, I should evaluate...                             │
│   3. Finally, I can conclude...                             │
└─────────────────────────────────────────────────────────────┘
```

### ActionBlock (Ny)
```
┌─────────────────────────────────────────────────────────────┐
│ ▼  🔍 Webbsökning   Slutförde på 1.24s                     │
├─────────────────────────────────────────────────────────────┤
│   Input: latest AI safety research 2026                     │
│   Resultat: Hittade 127 relevanta källor...                │
│   källor: 127    API-anrop: 3                              │
└─────────────────────────────────────────────────────────────┘
```

**Likheter:**
- ✅ Samma border-stil (dashed)
- ✅ Samma kollapsbar mekanism
- ✅ Samma padding och spacing
- ✅ Samma typografi
- ✅ Samma animationer
- ✅ Samma färgschema

**Skillnader:**
- 🎨 Verktygsspecifika färger (blå/grön/lila istället för alltid blå)
- 🏷️ Verktygsikon istället för "Thoughts"
- 📊 Strukturerad data (input/output/metadata) istället för fri text

## Integration i chat-flöde

Så här ser det ut när både Thoughts och Actions visas tillsammans:

```
[User]
What's the weather in Stockholm and what's the latest AI research?

[Assistant]

┌─────────────────────────────────────────────────────────────┐
│ ▼  Thoughts         Thinking for 0.50 seconds ⚙️           │
├─────────────────────────────────────────────────────────────┤
│   I need to:                                                 │
│   1. Get weather data from SMHI API                         │
│   2. Search for latest AI research                          │
│   3. Combine the information in a helpful response          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ▼  🌤️ SMHI Väder   Slutförde på 0.42s                     │
├─────────────────────────────────────────────────────────────┤
│   Input: Stockholm, 5 dagars prognos                        │
│   Resultat: [Väderdata för 5 dagar...]                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ▼  🔍 Webbsökning   Slutförde på 1.24s                     │
├─────────────────────────────────────────────────────────────┤
│   Input: latest AI research 2026                            │
│   Resultat: Hittade 127 källor...                          │
└─────────────────────────────────────────────────────────────┘

Here's what I found:

**Weather in Stockholm:**
The next 5 days will be mostly sunny with temperatures...

**Latest AI Research:**
There are several important developments in 2026...
```

## Teknisk implementation

### I chat-list.tsx

```tsx
// Precis som <think> tags processas idag
function processActionTags(content: string, isLoading: boolean) {
  const actionOpen = content.indexOf("<action>");
  const actionClose = content.indexOf("</action>");
  
  if (actionOpen !== -1 && actionClose !== -1) {
    const actionData = JSON.parse(
      content.slice(actionOpen + 8, actionClose)
    );
    return <ActionBlock action={actionData} live={isLoading} />;
  }
  return content;
}
```

### Från backend

```python
# Skicka action tags i response stream
yield f"<action>{json.dumps({
  'tool': 'web_search',
  'status': 'running',
  'input': query
})}</action>"

# När klar
yield f"<action>{json.dumps({
  'tool': 'web_search', 
  'status': 'complete',
  'output': results,
  'duration': 1.24
})}</action>"
```

## Fördelar med denna approach

✅ **Drop-in replacement** - Fungerar precis som ThinkBlock
✅ **Ingen brytande förändring** - Läggs till utan att påverka befintlig kod
✅ **Konsistent UX** - Användare känner igen mönstret
✅ **Flexibel** - Kan visa 1 eller 100 verktygsanrop
✅ **Framtidssäker** - Enkelt att lägga till fler verktyg
✅ **Responsiv** - Fungerar på mobil och desktop
✅ **Tillgänglig** - Samma accessibility som ThinkBlock

## Nästa steg för implementation

1. ✅ Komponenter skapade
2. ⏭️ Testa demo-sidan (`/action-demo`)
3. ⏭️ Lägg till `<action>` parsing i chat-list.tsx
4. ⏭️ Uppdatera backend för att skicka action tags
5. ⏭️ Testa med riktiga verktygsanrop
6. ⏭️ Fine-tune styling och animationer
7. ⏭️ Deploy till produktion

---

**Alla komponenter finns i:** `frontend/src/components/action-transparency/`
**Demo finns på:** `/action-demo`
**Dokumentation:** `frontend/src/components/action-transparency/README.md`
