# Debate Sidebar Implementation Guide

## Overview
Create a dedicated debate sidebar (like CoderSidebar in PR #23) to visualize multi-round AI debates in real-time.

## Reference Implementation
Based on CoderSidebar from PR #23:
- `web/src/app/chat/components/coder-sidebar.tsx`
- `web/src/app/chat/components/coder-card.tsx`
- Store updates in `web/src/core/store/store.ts`

## Architecture

### Debate Data Flow
```
Backend (debate_tools.py)
  → start_debate_round(1) [randomized order]
  → query_model_in_round("gpt-3.5-turbo")
  → query_model_in_round("gemini-2.5-flash")
  → query_model_in_round("deepseek-chat")
  → query_model_in_round("grok-4-fast-reasoning")
  → query_model_in_round("oneseek-local")
  → Round 2, Round 3...
  → collect_debate_votes()
  → get_debate_summary()

Frontend (DebateSidebar)
  → Display rounds in real-time
  → Show model responses
  → Visualize scores and voting
  → Present final summary
```

## Files to Create/Update

### 1. Create `web/src/app/chat/components/debate-sidebar.tsx`

```tsx
// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { MessageSquare, Trophy, Users, FileText, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { ScrollContainer } from "~/components/deer-flow/scroll-container";
import { Button } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { closeDebate, useStore } from "~/core/store";
import { cn } from "~/lib/utils";

export function DebateSidebar({
  className,
  sessionId = null,
}: {
  className?: string;
  sessionId: string | null;
}) {
  const t = useTranslations("chat.debate");
  const [activeTab, setActiveTab] = useState("rounds");
  
  // Get debate data from store
  const debateRounds = useStore((state) => state.debateRounds);
  const debateScores = useStore((state) => state.debateScores);
  const debateVoting = useStore((state) => state.debateVoting);
  const debateSummary = useStore((state) => state.debateSummary);

  return (
    <div className={cn("h-full w-full", className)}>
      <Card className={cn("relative h-full w-full pt-4", className)}>
        <div className="absolute right-4 flex h-9 items-center justify-center">
          <Button
            className="text-gray-400"
            size="sm"
            variant="ghost"
            onClick={() => closeDebate()}
          >
            <X />
          </Button>
        </div>
        
        <Tabs
          className="flex h-full w-full flex-col"
          value={activeTab}
          onValueChange={(value) => setActiveTab(value)}
        >
          <div className="flex w-full justify-center">
            <TabsList>
              <TabsTrigger value="rounds">
                <MessageSquare className="mr-2 h-4 w-4" />
                {t("rounds")}
              </TabsTrigger>
              <TabsTrigger value="models">
                <Users className="mr-2 h-4 w-4" />
                {t("models")}
              </TabsTrigger>
              <TabsTrigger value="voting">
                <Trophy className="mr-2 h-4 w-4" />
                {t("voting")}
              </TabsTrigger>
              <TabsTrigger value="summary">
                <FileText className="mr-2 h-4 w-4" />
                {t("summary")}
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Rounds Tab */}
          <TabsContent
            className="h-full min-h-0 flex-grow px-8"
            value="rounds"
            forceMount
            hidden={activeTab !== "rounds"}
          >
            <ScrollContainer
              className="h-full"
              scrollShadowColor="var(--card)"
              autoScrollToBottom
            >
              {sessionId && <DebateRoundsBlock rounds={debateRounds} />}
            </ScrollContainer>
          </TabsContent>

          {/* Models Tab */}
          <TabsContent
            className="h-full min-h-0 flex-grow px-8"
            value="models"
            forceMount
            hidden={activeTab !== "models"}
          >
            <ScrollContainer className="h-full" scrollShadowColor="var(--card)">
              <DebateModelsBlock rounds={debateRounds} scores={debateScores} />
            </ScrollContainer>
          </TabsContent>

          {/* Voting Tab */}
          <TabsContent
            className="h-full min-h-0 flex-grow px-8"
            value="voting"
            forceMount
            hidden={activeTab !== "voting"}
          >
            <ScrollContainer className="h-full" scrollShadowColor="var(--card)">
              <DebateVotingBlock voting={debateVoting} />
            </ScrollContainer>
          </TabsContent>

          {/* Summary Tab */}
          <TabsContent
            className="h-full min-h-0 flex-grow px-8"
            value="summary"
            forceMount
            hidden={activeTab !== "summary"}
          >
            <ScrollContainer className="h-full" scrollShadowColor="var(--card)">
              <DebateSummaryBlock summary={debateSummary} />
            </ScrollContainer>
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
}

// Sub-components for each tab
function DebateRoundsBlock({ rounds }) {
  // Display all rounds chronologically
  // Show model responses in order they were queried
  return <div>Rounds content...</div>;
}

function DebateModelsBlock({ rounds, scores }) {
  // Group responses by model
  // Show score for each model
  return <div>Models content...</div>;
}

function DebateVotingBlock({ voting }) {
  // Show voting results
  // Display winner
  return <div>Voting content...</div>;
}

function DebateSummaryBlock({ summary }) {
  // Show complete debate summary
  return <div>Summary content...</div>;
}
```

### 2. Create `web/src/app/chat/components/debate-card.tsx`

```tsx
// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { MessageSquare } from "lucide-react";
import { useTranslations } from "next-intl";

import { Card } from "~/components/ui/card";
import { openDebate, useStore } from "~/core/store";
import { cn } from "~/lib/utils";

export function DebateCard({
  sessionId,
  roundNumber,
  status,
}: {
  sessionId: string;
  roundNumber: number;
  status: "running" | "complete";
}) {
  const t = useTranslations("chat.debate");
  const isDebateSidebarOpen = useStore((state) => state.isDebateSidebarOpen);

  return (
    <Card
      className={cn(
        "cursor-pointer p-4 transition-all hover:bg-accent",
        isDebateSidebarOpen && "border-primary"
      )}
      onClick={() => openDebate(sessionId)}
    >
      <div className="flex items-center gap-3">
        <MessageSquare className="h-5 w-5 text-primary" />
        <div>
          <div className="font-medium">{t("debateRound", { round: roundNumber })}</div>
          <div className="text-sm text-muted-foreground">
            {status === "running" ? t("inProgress") : t("complete")}
          </div>
        </div>
      </div>
    </Card>
  );
}
```

### 3. Update `web/src/core/store/store.ts`

Add debate state:

```typescript
interface Store {
  // ... existing state ...
  
  // Debate state
  debateSessionId: string | null;
  isDebateSidebarOpen: boolean;
  debateRounds: DebateRound[];
  debateScores: Record<string, number>;
  debateVoting: VotingResult | null;
  debateSummary: string | null;
}

interface DebateRound {
  roundNumber: number;
  modelResponses: Array<{
    model: string;
    response: string;
    timestamp: number;
  }>;
  status: "running" | "complete";
}

interface VotingResult {
  votes: Record<string, string>; // voter -> voted_for
  winner: string;
  totalVotes: number;
}

// Actions
export const openDebate = (sessionId: string) => {
  useStore.setState({
    debateSessionId: sessionId,
    isDebateSidebarOpen: true,
  });
};

export const closeDebate = () => {
  useStore.setState({
    isDebateSidebarOpen: false,
  });
};

export const updateDebateRound = (round: DebateRound) => {
  const currentRounds = useStore.getState().debateRounds;
  const existingIndex = currentRounds.findIndex(
    (r) => r.roundNumber === round.roundNumber
  );
  
  if (existingIndex >= 0) {
    currentRounds[existingIndex] = round;
  } else {
    currentRounds.push(round);
  }
  
  useStore.setState({ debateRounds: [...currentRounds] });
};
```

### 4. Update `web/src/app/chat/main.tsx`

Add DebateSidebar column:

```typescript
import { DebateSidebar } from "./components/debate-sidebar";

export function ChatPage() {
  const isDebateSidebarOpen = useStore((state) => state.isDebateSidebarOpen);
  const debateSessionId = useStore((state) => state.debateSessionId);
  
  return (
    <div className="flex h-full">
      {/* Main chat */}
      <div className={cn(
        "flex-1",
        isDebateSidebarOpen && "mr-[400px]"
      )}>
        {/* ... chat content ... */}
      </div>
      
      {/* Debate Sidebar */}
      {isDebateSidebarOpen && (
        <div className="fixed right-0 top-0 h-full w-[400px]">
          <DebateSidebar sessionId={debateSessionId} />
        </div>
      )}
    </div>
  );
}
```

### 5. Update `web/src/app/chat/components/message-list-view.tsx`

Detect debate start and show DebateCard:

```typescript
import { DebateCard } from "./debate-card";

export function MessageListView() {
  // In message rendering logic
  if (message.role === "assistant" && message.enable_debate_mode) {
    return (
      <DebateCard
        sessionId={message.debate_session_id}
        roundNumber={message.debate_round}
        status={message.debate_status}
      />
    );
  }
}
```

### 6. Add i18n Strings

**web/messages/en.json:**
```json
{
  "chat": {
    "debate": {
      "rounds": "Rounds",
      "models": "Models",
      "voting": "Voting",
      "summary": "Summary",
      "debateRound": "Debate Round {round}",
      "inProgress": "In Progress",
      "complete": "Complete",
      "close": "Close Debate"
    }
  }
}
```

**web/messages/sv.json:**
```json
{
  "chat": {
    "debate": {
      "rounds": "Runder",
      "models": "Modeller",
      "voting": "Röstning",
      "summary": "Sammanfattning",
      "debateRound": "Debattrunda {round}",
      "inProgress": "Pågår",
      "complete": "Klar",
      "close": "Stäng Debatt"
    }
  }
}
```

## Backend Integration

Backend should emit debate data in format:

```python
{
  "event": "debate_round_start",
  "data": {
    "round_number": 1,
    "model_order": ["gpt-3.5-turbo", "gemini-2.5-flash", ...]
  }
}

{
  "event": "model_response",
  "data": {
    "round_number": 1,
    "model": "gpt-3.5-turbo",
    "response": "..."
  }
}

{
  "event": "debate_voting",
  "data": {
    "votes": {"gemini": "gpt-3.5-turbo", ...},
    "winner": "gpt-3.5-turbo"
  }
}
```

## Testing

1. Enable debate mode
2. Start debate query
3. Verify DebateCard appears in chat
4. Verify clicking card opens DebateSidebar
5. Verify rounds appear in real-time
6. Verify voting results displayed
7. Verify summary shown

## Implementation Priority

1. ✅ Token limit fix (DONE - commit 09c2207)
2. 🔄 Create basic DebateSidebar structure
3. 🔄 Add store state management
4. 🔄 Implement layout integration
5. 🔄 Add i18n strings
6. 🔄 Test with real debate flow

This creates a professional, dedicated debate visualization sidebar!
