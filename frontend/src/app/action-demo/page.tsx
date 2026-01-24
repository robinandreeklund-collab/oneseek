/**
 * Demo page showcasing all action transparency design proposals
 * 
 * This page demonstrates how tool actions (web_search, browse_page, smhi_api)
 * are displayed in different design variations, all using the existing
 * OneSeek design system and ThinkBlock styling.
 */

"use client";

import React, { useState } from "react";
import ActionBlock, { ToolAction } from "@/components/action-transparency/ActionBlock";
import ActionTimeline from "@/components/action-transparency/ActionTimeline";
import ActionCards from "@/components/action-transparency/ActionCards";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// Example tool actions
const exampleActions: ToolAction[] = [
  {
    tool: "web_search",
    status: "complete",
    input: "latest AI safety research 2026",
    output: "Hittade 127 relevanta källor:\n\n**Top resultat:**\n- arxiv.org: 42 publikationer\n- ai-safety.org: 38 artiklar\n- anthropic.com: 21 blogginlägg\n- Övriga källor: 26\n\nViktigaste upptäckter:\n1. Nya säkerhetsstandarder för LLM-utvärdering\n2. Framsteg inom interpretability och transparency\n3. Regulatoriska utvecklingar i EU och USA",
    duration: 1.24,
    metadata: {
      "källor": "127",
      "API-anrop": "3",
      "cachade": "15"
    }
  },
  {
    tool: "browse_page",
    status: "complete",
    input: "https://arxiv.org/abs/2024.12345",
    output: "**Titel:** Advanced Safety Protocols for Large Language Models\n\n**Sammanfattning:** Denna artikel presenterar nya metoder för att säkerställa säkerhet och transparens i stora språkmodeller. Forskarna föreslår en rad protokoll som inkluderar...\n\n**Huvudresultat:**\n- 95% förbättring i säkerhetsdetektering\n- Ny metod för real-time monitoring\n- Open source implementation tillgänglig",
    duration: 0.87,
    metadata: {
      "tecken": "15,234",
      "länkar": "12",
      "bilder": "5"
    }
  },
  {
    tool: "smhi_api",
    status: "complete",
    input: "Stockholm, 5 dagars prognos",
    output: "**Väderprognos Stockholm (5 dagar):**\n\n📅 **Måndag 23 Jan:** ☀️ Soligt, 2°C\n📅 **Tisdag 24 Jan:** ⛅ Delvis molnigt, 1°C\n📅 **Onsdag 25 Jan:** 🌧️ Regn, 4°C\n📅 **Torsdag 26 Jan:** ⛅ Delvis molnigt, 3°C\n📅 **Fredag 27 Jan:** ☀️ Soligt, 1°C\n\n💨 **Vind:** 3-5 m/s från sydväst\n💧 **Nederbörd:** 15mm onsdag",
    duration: 0.42,
    metadata: {
      "plats": "Stockholm",
      "lat": "59.3293",
      "lon": "18.0686",
      "datapunkter": "120"
    }
  }
];

const runningAction: ToolAction = {
  tool: "web_search",
  status: "running",
  input: "weather forecast Stockholm",
  duration: 2.5
};

const pendingAction: ToolAction = {
  tool: "browse_page",
  status: "pending",
  input: "https://example.com/article"
};

export default function ActionTransparencyDemo() {
  const [showLive, setShowLive] = useState(false);

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Action Transparency - Designförslag</h1>
        <p className="text-muted-foreground">
          Dessa komponenter visar hur verktygsanrop (web_search, browse_page, smhi_api) 
          kan visas i chatten med samma stil som den befintliga "Thoughts"-sektionen.
        </p>
      </div>

      <Tabs defaultValue="inline" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="inline">Design 1: Inline</TabsTrigger>
          <TabsTrigger value="timeline">Design 2: Timeline</TabsTrigger>
          <TabsTrigger value="cards">Design 3: Cards</TabsTrigger>
        </TabsList>

        <TabsContent value="inline" className="space-y-6">
          <div className="rounded-lg border border-border p-6 bg-card">
            <h2 className="text-xl font-semibold mb-4">Design 1: Inline Actions (ThinkBlock-stil)</h2>
            <p className="text-sm text-muted-foreground mb-6">
              Varje verktygsanrop visas inline med chatten, precis som "Thoughts"-blocken. 
              Stöder live-läge för pågående anrop och kollapsbar för slutförda anrop.
            </p>

            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold mb-2">Slutförda anrop:</h3>
                {exampleActions.map((action, idx) => (
                  <ActionBlock key={idx} action={action} />
                ))}
              </div>

              <div>
                <h3 className="text-sm font-semibold mb-2">Pågående anrop:</h3>
                <ActionBlock action={runningAction} live={true} />
              </div>

              <div>
                <h3 className="text-sm font-semibold mb-2">Väntande anrop:</h3>
                <ActionBlock action={pendingAction} />
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="timeline" className="space-y-6">
          <div className="rounded-lg border border-border p-6 bg-card">
            <h2 className="text-xl font-semibold mb-4">Design 2: Timeline View</h2>
            <p className="text-sm text-muted-foreground mb-6">
              Visar alla verktygsanrop i en vertikal tidslinje med visuella kopplingar. 
              Bra för att se kronologisk ordning och dataflöde mellan olika steg.
            </p>

            <ActionTimeline actions={[...exampleActions, runningAction, pendingAction]} />
          </div>
        </TabsContent>

        <TabsContent value="cards" className="space-y-6">
          <div className="rounded-lg border border-border p-6 bg-card">
            <h2 className="text-xl font-semibold mb-4">Design 3: Compact Cards</h2>
            <p className="text-sm text-muted-foreground mb-6">
              Visar verktygsanrop som kompakta kort i ett responsivt rutnät. 
              Perfekt när flera verktyg körs parallellt. Klicka på kort för att expandera detaljer.
            </p>

            <ActionCards actions={[...exampleActions, runningAction, pendingAction]} />
          </div>
        </TabsContent>
      </Tabs>

      <div className="mt-12 rounded-lg border border-border p-6 bg-muted/20">
        <h2 className="text-lg font-semibold mb-3">Implementeringsdetaljer</h2>
        <div className="space-y-2 text-sm text-muted-foreground">
          <p><strong>Designsystem:</strong> Använder befintliga shadcn/ui komponenter och Tailwind CSS</p>
          <p><strong>Stil:</strong> Matchar exakt samma visuella språk som ThinkBlock-komponenten</p>
          <p><strong>Verktyg:</strong> Stödjer web_search, browse_page och smhi_api med unika färger</p>
          <p><strong>Status:</strong> Visar pending, running, complete och error states med animationer</p>
          <p><strong>Interaktivitet:</strong> Kollapsbar innehåll, live-uppdateringar, timing-information</p>
        </div>
      </div>

      <div className="mt-6 rounded-lg border border-blue-500/50 bg-blue-50 dark:bg-blue-950/20 p-4">
        <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
          <span>💡</span>
          <span>Integration med befintlig kod</span>
        </h3>
        <div className="text-xs text-muted-foreground space-y-1">
          <p>• Lägg till ActionBlock i chat-list.tsx precis som ThinkBlock används idag</p>
          <p>• Backend skickar tool_calls i message.data liknande hur thoughts skickas</p>
          <p>• Samma parse-logik som för &lt;think&gt; tags, men för &lt;action&gt; tags</p>
          <p>• Stöder streaming för live-uppdateringar av pågående verktygsanrop</p>
        </div>
      </div>
    </div>
  );
}
