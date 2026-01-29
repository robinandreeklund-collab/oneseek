// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { MessageSquare, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { RainbowText } from "~/components/deer-flow/rainbow-text";
import { ScrollContainer } from "~/components/deer-flow/scroll-container";
import { Tooltip } from "~/components/deer-flow/tooltip";
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
  const [activeTab, setActiveTab] = useState("activities");
  const debateActivityIds = useStore((state) => state.debateActivityIds);
  const activityIds = sessionId ? debateActivityIds.get(sessionId) ?? [] : [];

  return (
    <div className={cn("h-full w-full", className)}>
      <Card className={cn("relative h-full w-full pt-4", className)}>
        <div className="absolute right-4 flex h-9 items-center justify-center">
          <Tooltip title={t("close")}>
            <Button
              className="text-gray-400"
              size="sm"
              variant="ghost"
              onClick={() => {
                closeDebate();
              }}
            >
              <X />
            </Button>
          </Tooltip>
        </div>
        <Tabs
          className="flex h-full w-full flex-col"
          value={activeTab}
          onValueChange={(value) => setActiveTab(value)}
        >
          <div className="flex w-full justify-center">
            <TabsList className="">
              <TabsTrigger className="px-8" value="activities">
                {t("activities")}
              </TabsTrigger>
              <TabsTrigger className="px-8" value="rounds">
                {t("rounds")}
              </TabsTrigger>
              <TabsTrigger className="px-8" value="voting">
                {t("voting")}
              </TabsTrigger>
            </TabsList>
          </div>
          <TabsContent
            className="h-full min-h-0 flex-grow px-8"
            value="activities"
            forceMount
            hidden={activeTab !== "activities"}
          >
            <ScrollContainer
              className="h-full"
              scrollShadowColor="var(--card)"
              autoScrollToBottom
            >
              {sessionId && <DebateActivitiesBlock sessionId={sessionId} />}
            </ScrollContainer>
          </TabsContent>
          <TabsContent
            className="h-full min-h-0 flex-grow px-8"
            value="rounds"
            forceMount
            hidden={activeTab !== "rounds"}
          >
            <ScrollContainer
              className="h-full"
              scrollShadowColor="var(--card)"
            >
              <div className="text-muted-foreground py-8 text-center">
                {t("roundsComingSoon")}
              </div>
            </ScrollContainer>
          </TabsContent>
          <TabsContent
            className="h-full min-h-0 flex-grow px-8"
            value="voting"
            forceMount
            hidden={activeTab !== "voting"}
          >
            <ScrollContainer
              className="h-full"
              scrollShadowColor="var(--card)"
            >
              <div className="text-muted-foreground py-8 text-center">
                {t("votingComingSoon")}
              </div>
            </ScrollContainer>
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
}

function DebateActivitiesBlock({ sessionId }: { sessionId: string }) {
  const debateActivityIds = useStore((state) => state.debateActivityIds);
  const activityIds = debateActivityIds.get(sessionId) ?? [];

  return (
    <div className="flex flex-col gap-4 py-4">
      <div className="flex items-center gap-2">
        <RainbowText className="flex items-center gap-2" animated={false}>
          <MessageSquare size={20} />
          <span className="font-semibold">Debate Session</span>
        </RainbowText>
      </div>
      {activityIds.length === 0 ? (
        <div className="text-muted-foreground py-8 text-center">
          No debate activities yet
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {activityIds.map((activityId) => (
            <DebateActivityItem key={activityId} messageId={activityId} />
          ))}
        </div>
      )}
    </div>
  );
}

function DebateActivityItem({ messageId }: { messageId: string }) {
  const message = useStore((state) => state.messages.get(messageId));

  if (!message) return null;

  return (
    <div className="rounded-lg border border-border bg-muted/50 p-4">
      <div className="mb-2 text-sm font-medium">
        {message.agent || "System"}
      </div>
      <div className="text-sm text-muted-foreground whitespace-pre-wrap">
        {message.content || "Processing..."}
      </div>
    </div>
  );
}
