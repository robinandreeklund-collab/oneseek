// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { MessageSquare } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useMemo } from "react";

import { RainbowText } from "~/components/deer-flow/rainbow-text";
import { RollingText } from "~/components/deer-flow/rolling-text";
import { Button } from "~/components/ui/button";
import { Card, CardFooter, CardHeader, CardTitle } from "~/components/ui/card";
import { closeDebate, openDebate, useMessage, useStore } from "~/core/store";
import { cn } from "~/lib/utils";

export function DebateCard({
  className,
  sessionId,
  onToggleDebate,
}: {
  className?: string;
  sessionId: string;
  onToggleDebate?: () => void;
}) {
  const t = useTranslations("chat.debate");
  const message = useMessage(sessionId);
  const openDebateSessionId = useStore((state) => state.openDebateSessionId);
  const ongoingDebateSessionId = useStore((state) => state.ongoingDebateSessionId);
  
  const isOngoing = useMemo(
    () => ongoingDebateSessionId === sessionId,
    [ongoingDebateSessionId, sessionId]
  );
  
  const state = useMemo(() => {
    // Show "running" if this is the ongoing debate session (not completed yet)
    if (isOngoing) {
      return t("runningDebate");
    }
    return t("debateComplete");
  }, [isOngoing, t]);

  const handleOpen = useCallback(() => {
    if (openDebateSessionId === sessionId) {
      closeDebate();
    } else {
      openDebate(sessionId);
    }
    onToggleDebate?.();
  }, [openDebateSessionId, sessionId, onToggleDebate]);

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle>
          <RainbowText
            className="flex items-center gap-2"
            animated={isOngoing && message?.isStreaming}
          >
            <MessageSquare size={20} />
            <span>{t("debateSession")}</span>
          </RainbowText>
        </CardTitle>
      </CardHeader>
      <CardFooter>
        <div className="flex w-full">
          <RollingText className="text-muted-foreground flex-grow text-sm">
            {state}
          </RollingText>
          <Button
            variant={openDebateSessionId !== sessionId ? "default" : "outline"}
            onClick={handleOpen}
          >
            {sessionId !== openDebateSessionId ? t("open") : t("close")}
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}
