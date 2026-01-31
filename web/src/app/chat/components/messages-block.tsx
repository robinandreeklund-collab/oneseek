// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { motion } from "framer-motion";
import { FastForward, Play } from "lucide-react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { RainbowText } from "~/components/deer-flow/rainbow-text";
import { Button } from "~/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import { fastForwardReplay } from "~/core/api";
import { useReplayMetadata } from "~/core/api/hooks";
import type { Option, Resource } from "~/core/messages";
import { useReplay } from "~/core/replay";
import { sendMessage, useMessageIds, useStore } from "~/core/store";
import { env } from "~/env";
import { cn } from "~/lib/utils";

import { ConversationStarter } from "./conversation-starter";
import { InputBox } from "./input-box";
import { MessageListView } from "./message-list-view";
import { Welcome } from "./welcome";

export function MessagesBlock({ className }: { className?: string }) {
  const t = useTranslations("chat.messages");
  const searchParams = useSearchParams();
  const messageIds = useMessageIds();
  const messageCount = messageIds.length;
  const responding = useStore((state) => state.responding);
  const { isReplay } = useReplay();
  const { title: replayTitle, hasError: replayHasError } = useReplayMetadata();
  const [replayStarted, setReplayStarted] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [feedback, setFeedback] = useState<{ option: Option } | null>(null);
  const initialQueryProcessedRef = useRef(false);
  
  const handleSend = useCallback(
    async (
      message: string,
      options?: {
        interruptFeedback?: string;
        resources?: Array<Resource>;
      },
    ) => {
      const abortController = new AbortController();
      abortControllerRef.current = abortController;
      try {
        await sendMessage(
          message,
          {
            interruptFeedback:
              options?.interruptFeedback ?? feedback?.option.value,
            resources: options?.resources,
          },
          {
            abortSignal: abortController.signal,
          },
        );
      } catch {}
    },
    [feedback],
  );
  const handleCancel = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
  }, []);
  const handleFeedback = useCallback(
    (feedback: { option: Option }) => {
      setFeedback(feedback);
    },
    [setFeedback],
  );
  const handleRemoveFeedback = useCallback(() => {
    setFeedback(null);
  }, [setFeedback]);
  const handleStartReplay = useCallback(() => {
    setReplayStarted(true);
    void sendMessage();
  }, [setReplayStarted]);
  const [fastForwarding, setFastForwarding] = useState(false);
  const handleFastForwardReplay = useCallback(() => {
    setFastForwarding(!fastForwarding);
    fastForwardReplay(!fastForwarding);
  }, [fastForwarding]);

  const heroPills = ["DeepSearch", "Skapa bild", "Senaste nytt", "Röstanalys"];
  
  // Handle initial query parameter from landing page
  useEffect(() => {
    const query = searchParams?.get("q");
    if (query && !initialQueryProcessedRef.current && !isReplay && messageCount === 0) {
      initialQueryProcessedRef.current = true;
      void handleSend(query);
    }
  }, [searchParams, isReplay, messageCount, handleSend]);
  
  return (
    <div className={cn("flex h-full flex-col", className)}>
      {responding || messageCount !== 0 || isReplay ? (
        <>
          <MessageListView
            className="flex flex-grow"
            onFeedback={handleFeedback}
            onSendMessage={handleSend}
          />
          {!isReplay && (
            <div className="relative flex shrink-0 pb-4">
              <InputBox
                className="w-full"
                responding={responding}
                feedback={feedback}
                onSend={handleSend}
                onCancel={handleCancel}
                onRemoveFeedback={handleRemoveFeedback}
              />
            </div>
          )}
        </>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center gap-6 px-6 py-10">
          <div className="flex flex-col items-center gap-3">
            <Image
              src="/oneseek-logo.svg"
              alt="OneSeek"
              width={72}
              height={72}
              className="h-18 w-18 object-contain"
              priority
            />
            <h3 className="text-center text-2xl font-semibold">OneSeek</h3>
            <p className="text-muted-foreground text-center text-base">
              Vad vill du att OneSeek ska veta?
            </p>
          </div>
          <div className="w-full max-w-3xl">
            <InputBox
              className="w-full shadow-2xl"
              responding={responding}
              feedback={feedback}
              onSend={handleSend}
              onCancel={handleCancel}
              onRemoveFeedback={handleRemoveFeedback}
            />
            <div className="mt-3 flex flex-wrap justify-center gap-2 text-sm text-muted-foreground">
              {heroPills.map((pill) => (
                <Button
                  key={pill}
                  type="button"
                  variant="outline"
                  className="rounded-full border-border/70 bg-background/60 px-3 py-1 text-xs hover:bg-background"
                  onClick={() => handleSend(pill)}
                >
                  {pill}
                </Button>
              ))}
            </div>
          </div>
        </div>
      )}
      {isReplay && (
        <>
          <div
            className={cn(
              "fixed bottom-[calc(50vh+80px)] left-0 transition-all duration-500 ease-out",
              replayStarted && "pointer-events-none scale-150 opacity-0",
            )}
          >
            <Welcome />
          </div>
          <motion.div
            className="mb-4 h-fit w-full items-center justify-center"
            initial={{ opacity: 0, y: "20vh" }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Card
              className={cn(
                "w-full transition-all duration-300",
                !replayStarted && "translate-y-[-40vh]",
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex flex-grow items-center">
                  {responding && (
                    <motion.div
                      className="ml-3"
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.8 }}
                      transition={{ duration: 0.3 }}
                    >
                      <video
                        // Walking deer animation, designed by @liangzhaojun. Thank you for creating it!
                        src="/images/walking_deer.webm"
                        autoPlay
                        loop
                        muted
                        className="h-[42px] w-[42px] object-contain"
                      />
                    </motion.div>
                  )}
                  <CardHeader className={cn("flex-grow", responding && "pl-3")}>
                    <CardTitle>
                      <RainbowText animated={responding}>
                        {responding ? t("replaying") : `${replayTitle}`}
                      </RainbowText>
                    </CardTitle>
                    <CardDescription>
                      <RainbowText animated={responding}>
                        {responding
                          ? t("replayDescription")
                          : replayStarted
                            ? t("replayHasStopped")
                            : t("replayModeDescription")}
                      </RainbowText>
                    </CardDescription>
                  </CardHeader>
                </div>
                {!replayHasError && (
                  <div className="pr-4">
                    {responding && (
                      <Button
                        className={cn(fastForwarding && "animate-pulse")}
                        variant={fastForwarding ? "default" : "outline"}
                        onClick={handleFastForwardReplay}
                      >
                        <FastForward size={16} />
                        {t("fastForward")}
                      </Button>
                    )}
                    {!replayStarted && (
                      <Button className="w-24" onClick={handleStartReplay}>
                        <Play size={16} />
                        {t("play")}
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </Card>
            {!replayStarted && env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY && (
              <div className="text-muted-foreground w-full text-center text-xs">
                {t("demoNotice")}{" "}
                <a
                  className="underline"
                  href="https://github.com/bytedance/deer-flow"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {t("clickHere")}
                </a>{" "}
                {t("cloneLocally")}
              </div>
            )}
          </motion.div>
        </>
      )}
    </div>
  );
}
