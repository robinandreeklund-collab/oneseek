// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { Code } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useMemo } from "react";

import { RainbowText } from "~/components/deer-flow/rainbow-text";
import { RollingText } from "~/components/deer-flow/rolling-text";
import { Button } from "~/components/ui/button";
import { Card, CardFooter, CardHeader, CardTitle } from "~/components/ui/card";
import { closeCoder, openCoder, useMessage, useStore } from "~/core/store";
import { cn } from "~/lib/utils";

export function CoderCard({
  className,
  sessionId,
  onToggleCoder,
}: {
  className?: string;
  sessionId: string;
  onToggleCoder?: () => void;
}) {
  const t = useTranslations("chat.coder");
  const message = useMessage(sessionId);
  const openCoderSessionId = useStore((state) => state.openCoderSessionId);
  const ongoingCoderSessionId = useStore((state) => state.ongoingCoderSessionId);
  
  const isOngoing = useMemo(
    () => ongoingCoderSessionId === sessionId,
    [ongoingCoderSessionId, sessionId]
  );
  
  const state = useMemo(() => {
    if (message?.isStreaming) {
      return t("runningCode");
    }
    return t("codeExecutionComplete");
  }, [message?.isStreaming, t]);

  const handleOpen = useCallback(() => {
    if (openCoderSessionId === sessionId) {
      closeCoder();
    } else {
      openCoder(sessionId);
    }
    onToggleCoder?.();
  }, [openCoderSessionId, sessionId, onToggleCoder]);

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle>
          <RainbowText
            className="flex items-center gap-2"
            animated={isOngoing && message?.isStreaming}
          >
            <Code size={20} />
            <span>{t("codeExecution")}</span>
          </RainbowText>
        </CardTitle>
      </CardHeader>
      <CardFooter>
        <div className="flex w-full">
          <RollingText className="text-muted-foreground flex-grow text-sm">
            {state}
          </RollingText>
          <Button
            variant={openCoderSessionId !== sessionId ? "default" : "outline"}
            onClick={handleOpen}
          >
            {sessionId !== openCoderSessionId ? t("open") : t("close")}
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}
