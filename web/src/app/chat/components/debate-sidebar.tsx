// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { ScrollContainer } from "~/components/deer-flow/scroll-container";
import { Tooltip } from "~/components/deer-flow/tooltip";
import { Button } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { closeDebate, useStore } from "~/core/store";
import { cn } from "~/lib/utils";

import { DebateActivitiesBlock } from "./debate-activities-block";
import { DebateReportBlock } from "./debate-report-block";

export function DebateSidebar({
  className,
  sessionId = null,
}: {
  className?: string;
  sessionId: string | null;
}) {
  const t = useTranslations("chat.debate");
  const [activeTab, setActiveTab] = useState("activities");
  const [editing, setEditing] = useState(false);
  
  // Find report message (agent="reporter")
  const messages = Array.from(useStore(state => state.messages).values());
  const reportMessage = messages.find(m => m.agent === "reporter");
  const reportId = reportMessage?.id;

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
              <TabsTrigger className="px-8" value="reporter">
                {t("reporter")}
              </TabsTrigger>
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
            value="reporter"
            forceMount
            hidden={activeTab !== "reporter"}
          >
            <ScrollContainer
              className="h-full px-5 pb-20"
              scrollShadowColor="var(--card)"
              autoScrollToBottom={!reportId}
            >
              {reportId && sessionId && (
                <DebateReportBlock
                  className="mt-4"
                  debateId={sessionId}
                  messageId={reportId}
                  editing={editing}
                />
              )}
            </ScrollContainer>
          </TabsContent>
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
