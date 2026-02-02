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
import { parseJSON } from "~/core/utils";
import { cn } from "~/lib/utils";

import { DebateActivitiesBlock } from "./debate-activities-block";
import { DebateReportBlock } from "./debate-report-block";
import { DebateModelIcon } from "./debate-model-icon";

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
  
  const debateSummary = parseJSON(
    messages
      .filter((m) => m.agent === "debate_orchestrator" && m.content)
      .map((m) => m.content)
      .reverse()[0],
    {},
  ) as {
    rounds?: Array<{
      round?: number;
      responses?: Array<{ model?: string; display_name?: string; response?: string }>;
    }>;
    vote_results?: {
      winner?: string;
      votes?: Record<string, number>;
      vote_details?: Array<{ voter?: string; vote?: string; reasons?: string[] }>;
    };
  };

  return (
    <div className="h-full w-full">
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
              {debateSummary.rounds?.length ? (
                <div className="space-y-6 py-4">
                  {debateSummary.rounds.map((round) => (
                    <div
                      key={`round-${round.round}`}
                      className="rounded-lg border border-border/60 bg-muted/30 p-4"
                    >
                      <div className="text-sm font-semibold">
                        Runda {round.round}
                      </div>
                      <div className="mt-3 space-y-3">
                        {(round.responses ?? []).map((resp, idx) => (
                          <div
                            key={`${round.round}-${resp.model ?? idx}`}
                            className="rounded-md border border-border/40 bg-background/60 p-3"
                          >
                            <div className="flex items-center gap-2 text-sm font-medium">
                              <DebateModelIcon modelKey={resp.model} />
                              <span>{resp.display_name ?? resp.model ?? "Model"}</span>
                            </div>
                            <div className="mt-2 text-sm text-foreground/80">
                              {resp.response}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-muted-foreground py-8 text-center">
                  {t("roundsComingSoon")}
                </div>
              )}
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
              {debateSummary.vote_results ? (
                <div className="space-y-4 py-4">
                  <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <div className="text-sm font-semibold">Vinnare</div>
                    <div className="mt-2 text-base">
                      {debateSummary.vote_results.winner ?? "Ingen vinnare"}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                    <div className="text-sm font-semibold">Röstfördelning</div>
                    <div className="mt-2 space-y-2 text-sm">
                      {debateSummary.vote_results.votes &&
                        Object.entries(debateSummary.vote_results.votes).map(
                          ([model, count]) => (
                            <div key={model} className="flex items-center gap-2">
                              <DebateModelIcon modelKey={model} />
                              <span className="flex-1">{model}</span>
                              <span className="font-semibold">{count}</span>
                            </div>
                          ),
                        )}
                    </div>
                  </div>
                  {debateSummary.vote_results.vote_details?.length ? (
                    <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                      <div className="text-sm font-semibold">Detaljer</div>
                      <div className="mt-2 space-y-3 text-sm">
                        {debateSummary.vote_results.vote_details.map((detail, idx) => (
                          <div key={`${detail.voter}-${idx}`} className="rounded-md border border-border/50 p-2">
                            <div className="flex items-center gap-2">
                              <span className="flex-1">
                                {detail.voter ?? "Okänd"} → {detail.vote ?? "Okänd"}
                              </span>
                            </div>
                            {Array.isArray(detail.reasons) && detail.reasons.length > 0 && (
                              <ul className="mt-2 list-disc pl-5 text-xs text-muted-foreground">
                                {detail.reasons.slice(0, 3).map((reason, reasonIdx) => (
                                  <li key={`${detail.voter}-${reasonIdx}`}>{reason}</li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="text-muted-foreground py-8 text-center">
                  {t("votingComingSoon")}
                </div>
              )}
            </ScrollContainer>
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
}
