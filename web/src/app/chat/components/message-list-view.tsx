// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { LoadingOutlined } from "@ant-design/icons";
import { motion } from "framer-motion";
import {
  Download,
  Headphones,
  ChevronDown,
  ChevronRight,
  Lightbulb,
  Wrench,
} from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import React, { useCallback, useMemo, useRef, useState } from "react";

import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { Markdown } from "~/components/deer-flow/markdown";
import { RainbowText } from "~/components/deer-flow/rainbow-text";
import { RollingText } from "~/components/deer-flow/rolling-text";
import {
  ScrollContainer,
  type ScrollContainerRef,
} from "~/components/deer-flow/scroll-container";
import { Tooltip } from "~/components/deer-flow/tooltip";
import { Button } from "~/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "~/components/ui/collapsible";
import { isPlannerAgent } from "~/core/messages";
import type { Message, Option } from "~/core/messages";
import {
  closeResearch,
  openResearch,
  useLastFeedbackMessageId,
  useLastInterruptMessage,
  useMessage,
  useRenderableMessageIds,
  useResearchMessage,
  useStore,
} from "~/core/store";
import { parseJSON } from "~/core/utils";
import { cn } from "~/lib/utils";

import { CoderCard } from "./coder-card";
import { DebateCard } from "./debate-card";
import { DebateModelIcon } from "./debate-model-icon";

export function MessageListView({
  className,
  onFeedback,
  onSendMessage,
}: {
  className?: string;
  onFeedback?: (feedback: { option: Option }) => void;
  onSendMessage?: (
    message: string,
    options?: { interruptFeedback?: string },
  ) => void;
}) {
  const scrollContainerRef = useRef<ScrollContainerRef>(null);
  // Use renderable message IDs to avoid React key warnings from duplicate or non-rendering messages
  const messageIds = useRenderableMessageIds();
  const interruptMessage = useLastInterruptMessage();
  const waitingForFeedbackMessageId = useLastFeedbackMessageId();
  const responding = useStore((state) => state.responding);
  const noOngoingResearch = useStore(
    (state) => state.ongoingResearchId === null,
  );
  const ongoingResearchIsOpen = useStore(
    (state) => state.ongoingResearchId === state.openResearchId,
  );

  const handleToggleSidebar = useCallback(() => {
    // Fix the issue where auto-scrolling to the bottom
    // occasionally fails when toggling research or coder sidebar.
    const timer = setTimeout(() => {
      if (scrollContainerRef.current) {
        scrollContainerRef.current.scrollToBottom();
      }
    }, 500);
    return () => {
      clearTimeout(timer);
    };
  }, []);

  const isCodeTestInterrupt = useMemo(() => {
    return (interruptMessage?.options || []).some(
      (option) => option.value === "[TEST]" || option.value === "[SKIP]",
    );
  }, [interruptMessage]);

  return (
    <ScrollContainer
      className={cn("flex h-full w-full flex-col overflow-hidden", className)}
      scrollShadowColor="var(--app-background)"
      autoScrollToBottom
      ref={scrollContainerRef}
    >
      <ul className="flex flex-col">
        {messageIds.map((messageId) => (
          <MessageListItem
            key={messageId}
            messageId={messageId}
            waitForFeedback={waitingForFeedbackMessageId === messageId}
            interruptMessage={interruptMessage}
            onFeedback={onFeedback}
            onSendMessage={onSendMessage}
            onToggleSidebar={handleToggleSidebar}
          />
        ))}
        {isCodeTestInterrupt && interruptMessage && (
          <li className="px-4 py-4">
            <InterruptCard
              message={interruptMessage}
              onSendMessage={onSendMessage}
            />
          </li>
        )}
        <div className="flex h-8 w-full shrink-0"></div>
      </ul>
      {responding && (noOngoingResearch || !ongoingResearchIsOpen) && (
        <LoadingAnimation className="ml-4" />
      )}
    </ScrollContainer>
  );
}

function InterruptCard({
  message,
  onSendMessage,
}: {
  message: Message;
  onSendMessage?: (
    message: string,
    options?: { interruptFeedback?: string },
  ) => void;
}) {
  const options = message.options ?? [];

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Feedback</CardTitle>
      </CardHeader>
      <CardContent>
        <Markdown animated={false}>{message.content}</Markdown>
      </CardContent>
      <CardFooter className="flex flex-wrap gap-2 justify-end">
        {options.map((option) => (
          <Button
            key={option.value}
            variant={option.value === "[TEST]" ? "default" : "outline"}
            onClick={() => {
              if (!onSendMessage) return;
              const text =
                option.value === "[TEST]"
                  ? "Run tests"
                  : option.value === "[SKIP]"
                    ? "Skip testing"
                    : option.text;
              onSendMessage(text, { interruptFeedback: option.value });
            }}
          >
            {option.text}
          </Button>
        ))}
      </CardFooter>
    </Card>
  );
}

function MessageListItem({
  className,
  messageId,
  waitForFeedback,
  interruptMessage,
  onFeedback,
  onSendMessage,
  onToggleSidebar,
}: {
  className?: string;
  messageId: string;
  waitForFeedback?: boolean;
  onFeedback?: (feedback: { option: Option }) => void;
  interruptMessage?: Message | null;
  onSendMessage?: (
    message: string,
    options?: { interruptFeedback?: string },
  ) => void;
  onToggleSidebar?: () => void;
}) {
  const message = useMessage(messageId);
  const researchIds = useStore((state) => state.researchIds);
  const coderSessionIds = useStore((state) => state.coderSessionIds);
  const debateSessionIds = useStore((state) => state.debateSessionIds);
  const startOfResearch = useMemo(() => {
    return researchIds.includes(messageId);
  }, [researchIds, messageId]);
  const startOfCoderSession = useMemo(() => {
    return coderSessionIds.includes(messageId);
  }, [coderSessionIds, messageId]);
  const startOfDebateSession = useMemo(() => {
    return debateSessionIds.includes(messageId);
  }, [debateSessionIds, messageId]);
  if (message) {
    if (
      message.role === "user" ||
      message.agent === "coordinator" ||
      isPlannerAgent(message.agent) ||
      message.agent === "podcast" ||
      startOfResearch ||
      startOfCoderSession ||
      startOfDebateSession
    ) {
      let content: React.ReactNode;
      if (isPlannerAgent(message.agent)) {
        content = (
          <div className="w-full px-4">
            <PlanCard
              message={message}
              waitForFeedback={waitForFeedback}
              interruptMessage={interruptMessage}
              onFeedback={onFeedback}
              onSendMessage={onSendMessage}
            />
          </div>
        );
      } else if (message.agent === "podcast") {
        content = (
          <div className="w-full px-4">
            <PodcastCard message={message} />
          </div>
        );
      } else if (startOfResearch) {
        content = (
          <div className="w-full px-4">
            <ResearchCard
              researchId={message.id}
              onToggleResearch={onToggleSidebar}
            />
          </div>
        );
      } else if (startOfCoderSession) {
        content = (
          <div className="w-full px-4">
            <CoderCard
              sessionId={message.id}
              onToggleCoder={onToggleSidebar}
            />
          </div>
        );
      } else if (startOfDebateSession) {
        content = (
          <div className="w-full px-4">
            <DebateCard
              sessionId={message.id}
              onToggleDebate={onToggleSidebar}
            />
          </div>
        );
      } else {
        content = message.content ? (
          <div
            className={cn(
              "flex w-full px-4",
              message.role === "user" && "justify-end",
              className,
            )}
          >
            <MessageBubble message={message}>
              <div className="flex w-full flex-col break-words">
                <Markdown
                  className={cn(
                    message.role === "user" &&
                      "prose-invert not-dark:text-secondary dark:text-inherit",
                  )}
                >
                  {message?.content}
                </Markdown>
              </div>
            </MessageBubble>
          </div>
        ) : null;
      }
      if (content) {
        return (
          <motion.li
            className="mt-10"
            key={messageId}
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ transition: "all 0.2s ease-out" }}
            transition={{
              duration: 0.2,
              ease: "easeOut",
            }}
          >
            {content}
          </motion.li>
        );
      }
    }
    return null;
  }
}

function MessageBubble({
  className,
  message,
  children,
}: {
  className?: string;
  message: Message;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "group flex w-auto max-w-[90vw] flex-col rounded-2xl px-4 py-3 break-words",
        message.role === "user" && "bg-brand rounded-ee-none",
        message.role === "assistant" && "bg-card rounded-es-none",
        className,
      )}
      style={{ wordBreak: "break-all" }}
    >
      {children}
    </div>
  );
}

function ResearchCard({
  className,
  researchId,
  onToggleResearch,
}: {
  className?: string;
  researchId: string;
  onToggleResearch?: () => void;
}) {
  const t = useTranslations("chat.research");
  const locale = useLocale();
  const isSwedish = locale.startsWith("sv");
  const reportId = useStore((state) => state.researchReportIds.get(researchId));
  const hasReport = reportId !== undefined;
  const reportGenerating = useStore(
    (state) => hasReport && state.messages.get(reportId)!.isStreaming,
  );
  const openResearchId = useStore((state) => state.openResearchId);
  const state = useMemo(() => {
    if (hasReport) {
      return reportGenerating ? t("generatingReport") : t("reportGenerated");
    }
    return t("researching");
  }, [hasReport, reportGenerating, t]);
  const msg = useResearchMessage(researchId);
  const title = useMemo(() => {
    if (msg) {
      return parseJSON(msg.content ?? "", { title: "" }).title;
    }
    return undefined;
  }, [msg]);
  const handleOpen = useCallback(() => {
    if (openResearchId === researchId) {
      closeResearch();
    } else {
      openResearch(researchId);
    }
    onToggleResearch?.();
  }, [openResearchId, researchId, onToggleResearch]);
  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle>
          <RainbowText animated={state !== t("reportGenerated")}>
            {title !== undefined && title !== "" ? title : t("deepResearch")}
          </RainbowText>
        </CardTitle>
      </CardHeader>
      <CardFooter>
        <div className="flex w-full">
          <RollingText className="text-muted-foreground flex-grow text-sm">
            {state}
          </RollingText>
          <Button
            variant={!openResearchId ? "default" : "outline"}
            onClick={handleOpen}
          >
            {researchId !== openResearchId ? t("open") : t("close")}
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}

function ThoughtBlock({
  className,
  content,
  isStreaming,
  hasMainContent,
  contentChunks,
}: {
  className?: string;
  content: string;
  isStreaming?: boolean;
  hasMainContent?: boolean;
  contentChunks?: string[];
}) {
  const t = useTranslations("chat.research");
  const [isOpen, setIsOpen] = useState(true);

  const [hasAutoCollapsed, setHasAutoCollapsed] = useState(false);

  React.useEffect(() => {
    if (hasMainContent && !hasAutoCollapsed) {
      setIsOpen(false);
      setHasAutoCollapsed(true);
    }
  }, [hasMainContent, hasAutoCollapsed]);

  if (!content || content.trim() === "") {
    return null;
  }

  // Split content into static (previous chunks) and streaming (current chunk)
  const chunks = contentChunks ?? [];
  const staticContent = chunks.slice(0, -1).join("");
  const streamingChunk = isStreaming && chunks.length > 0 ? (chunks[chunks.length - 1] ?? "") : "";
  const hasStreamingContent = isStreaming && streamingChunk.length > 0;

  return (
    <div className={cn("mb-6 w-full", className)}>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className={cn(
              "h-auto w-full justify-start rounded-xl border px-6 py-4 text-left transition-all duration-200",
              "hover:bg-accent hover:text-accent-foreground",
              isStreaming
                ? "border-primary/20 bg-primary/5 shadow-sm"
                : "border-border bg-card",
            )}
          >
            <div className="flex w-full items-center gap-3">
              <Lightbulb
                size={18}
                className={cn(
                  "shrink-0 transition-colors duration-200",
                  isStreaming ? "text-primary" : "text-muted-foreground",
                )}
              />
              <span
                className={cn(
                  "leading-none font-semibold transition-colors duration-200",
                  isStreaming ? "text-primary" : "text-foreground",
                )}
              >
                {t("deepThinking")}
              </span>
              {isStreaming && <LoadingAnimation className="ml-2 scale-75" />}
              <div className="flex-grow" />
              {isOpen ? (
                <ChevronDown
                  size={16}
                  className="text-muted-foreground transition-transform duration-200"
                />
              ) : (
                <ChevronRight
                  size={16}
                  className="text-muted-foreground transition-transform duration-200"
                />
              )}
            </div>
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:slide-up-2 data-[state=open]:slide-down-2 mt-3">
          <Card
            className={cn(
              "transition-all duration-200",
              isStreaming ? "border-primary/20 bg-primary/5" : "border-border",
            )}
          >
            <CardContent>
              <div className="flex h-40 w-full overflow-y-auto">
                <ScrollContainer
                  className={cn(
                    "flex h-full w-full flex-col overflow-hidden",
                    className,
                  )}
                  scrollShadow={false}
                  autoScrollToBottom
                >
                  {staticContent && (
                    <Markdown
                      className={cn(
                        "prose dark:prose-invert max-w-none transition-colors duration-200",
                        "opacity-80",
                      )}
                      animated={false}
                    >
                      {staticContent}
                    </Markdown>
                  )}
                  {hasStreamingContent && (
                    <Markdown
                      className={cn(
                        "prose dark:prose-invert max-w-none transition-colors duration-200",
                        "prose-primary",
                      )}
                      animated={true}
                    >
                      {streamingChunk}
                    </Markdown>
                  )}
                  {!hasStreamingContent && (
                    <Markdown
                      className={cn(
                        "prose dark:prose-invert max-w-none transition-colors duration-200",
                        isStreaming ? "prose-primary" : "opacity-80",
                      )}
                      animated={false}
                    >
                      {content}
                    </Markdown>
                  )}
                </ScrollContainer>
              </div>
            </CardContent>
          </Card>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

const GREETINGS = ["Cool", "Sounds great", "Looks good", "Great", "Awesome"];
const DEBATE_MODEL_OPTIONS = [
  { id: "gpt-3.5-turbo", label: "ChatGPT" },
  { id: "gemini-2.5-flash", label: "Gemini" },
  { id: "deepseek-chat", label: "DeepSeek" },
  { id: "grok-4-fast-reasoning", label: "Grok-4" },
];
const DEFAULT_DEBATE_MODELS = [
  "gpt-3.5-turbo",
  "gemini-2.5-flash",
  "deepseek-chat",
];
function formatPlannerName(agent?: string) {
  if (!agent || agent === "planner") {
    return null;
  }
  if (agent.endsWith("_planner")) {
    const base = agent.replace(/_planner$/, "").replace(/_/g, " ").trim();
    if (!base) {
      return null;
    }
    return base.charAt(0).toUpperCase() + base.slice(1);
  }
  return null;
}
function PlanCard({
  className,
  message,
  interruptMessage,
  onFeedback,
  waitForFeedback,
  onSendMessage,
}: {
  className?: string;
  message: Message;
  interruptMessage?: Message | null;
  onFeedback?: (feedback: { option: Option }) => void;
  onSendMessage?: (
    message: string,
    options?: { interruptFeedback?: string },
  ) => void;
  waitForFeedback?: boolean;
}) {
  const t = useTranslations("chat.research");
  const locale = useLocale();
  const isSwedish = locale.startsWith("sv");
  const plan = useMemo<{
    title?: string;
    thought?: string;
    steps?: { title?: string; description?: string; tools?: string[] }[];
  }>(() => {
    return parseJSON(message.content ?? "", {});
  }, [message.content]);

  const reasoningContent = message.reasoningContent ?? "";
  const planThought = (plan.thought ?? "").trim();
  const hasMainContent = Boolean(
    plan.title || planThought || (plan.steps && plan.steps.length > 0),
  );
  const isDebatePlan = useMemo(() => {
    const title = plan.title ?? "";
    const thought = plan.thought ?? "";
    const hasRoundSteps = (plan.steps || []).some((step) =>
      /runda|round/i.test(step?.title ?? ""),
    );
    return /debatt|debate/i.test(title) || /debatt|debate/i.test(thought) || hasRoundSteps;
  }, [plan]);
  const [selectedModels, setSelectedModels] = useState<string[]>(
    DEFAULT_DEBATE_MODELS,
  );
  const canAcceptDebate = selectedModels.length > 0;
  const startActionLabel = useMemo(() => {
    if (isDebatePlan) {
      return t("startDebate");
    }
    const plannerName = formatPlannerName(message.agent);
    if (plannerName) {
      const normalized = plannerName.toLowerCase();
      const displayName =
        normalized === "ai comparison"
          ? isSwedish
            ? "AI-jämförelse"
            : "AI comparison"
          : plannerName;
      return isSwedish ? `Starta ${displayName}` : `Start ${displayName}`;
    }
    return t("startResearch");
  }, [isDebatePlan, message.agent, t, isSwedish]);

  // Check if thinking: has reasoning content but no main content yet
  const hasReasoning = reasoningContent.trim().length > 0;
  const thoughtContent = hasReasoning ? reasoningContent : planThought;
  const thoughtChunks = hasReasoning ? message.reasoningContentChunks : undefined;
  const isThinking = Boolean(hasReasoning && !hasMainContent);

  // Show plan if we have content OR if we're still streaming (to show loading state)
  const shouldShowPlan = hasMainContent || message.isStreaming;
  const handleAccept = useCallback(async () => {
    if (onSendMessage) {
      const greetings = isSwedish
        ? ["Toppen", "Låter bra", "Ser bra ut", "Grymt", "Kanon"]
        : GREETINGS;
      const feedback = isDebatePlan
        ? `accepted|models=${selectedModels.join(",")}`
        : "accepted";
      const intro = greetings[Math.floor(Math.random() * greetings.length)];
      const followup = isSwedish
        ? Math.random() > 0.5
          ? "Då kör vi."
          : "Nu kör vi."
        : Math.random() > 0.5
          ? "Let's get started."
          : "Let's start.";
      onSendMessage(
        `${intro}! ${followup}`,
        {
          interruptFeedback: feedback,
        },
      );
    }
  }, [isDebatePlan, onSendMessage, selectedModels, isSwedish]);
  return (
    <div className={cn("w-full", className)}>
      {thoughtContent && (
        <ThoughtBlock
          content={thoughtContent}
          isStreaming={isThinking}
          hasMainContent={hasMainContent}
          contentChunks={thoughtChunks}
        />
      )}
      {shouldShowPlan && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        >
          <Card className="w-full">
            <CardHeader>
              <CardTitle>
                <Markdown animated={false}>
                  {`### ${
                    plan.title !== undefined && plan.title !== ""
                      ? plan.title
                      : t("deepResearch")
                  }`}
                </Markdown>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!hasMainContent && message.isStreaming && (
                <div className="flex items-center gap-2 text-sm opacity-70 p-4">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                  <span>
                    {isSwedish ? "Skapar plan..." : "Creating research plan..."}
                  </span>
                </div>
              )}
              {hasMainContent && (
                <div style={{ wordBreak: "break-all", whiteSpace: "normal" }}>
                  {planThought && !hasReasoning && (
                    <Markdown className="opacity-80" animated={false}>
                      {planThought}
                    </Markdown>
                  )}
                  {isDebatePlan && (
                    <div className="mt-4 rounded-md border border-border/60 bg-muted/40 p-3">
                      <div className="text-sm font-semibold">
                        Välj modeller som ska delta
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {DEBATE_MODEL_OPTIONS.map((model) => {
                          const isSelected = selectedModels.includes(model.id);
                          return (
                            <Button
                              key={model.id}
                              type="button"
                              size="sm"
                              variant={isSelected ? "default" : "outline"}
                              className="gap-2"
                              onClick={() => {
                                setSelectedModels((prev) => {
                                  if (prev.includes(model.id)) {
                                    return prev.filter((id) => id !== model.id);
                                  }
                                  return [...prev, model.id];
                                });
                              }}
                            >
                              <DebateModelIcon modelKey={model.id} />
                              {model.label}
                            </Button>
                          );
                        })}
                        <div className="flex items-center gap-2 rounded-md border border-border/60 px-2 py-1 text-xs text-muted-foreground">
                          <DebateModelIcon modelKey="oneseek-local" />
                          OneSeek (alltid)
                        </div>
                      </div>
                      {!canAcceptDebate && (
                        <div className="mt-2 text-xs text-destructive">
                          Välj minst en extern modell för att starta debatten.
                        </div>
                      )}
                    </div>
                  )}
                  {plan.steps && (
                    <ul className="my-2 flex list-decimal flex-col gap-4 border-l-[2px] pl-8">
                      {plan.steps.map((step, i) => (
                        <li key={`step-${i}`} style={{ wordBreak: 'break-all', whiteSpace: 'normal' }}>
                          <div className="flex items-start gap-2">
                            <div className="flex-1">
                              <h3 className="mb flex items-center gap-2 text-lg font-medium">
                                <Markdown animated={false}>
                                  {step.title}
                                </Markdown>
                                {step.tools && step.tools.length > 0 && (
                                  <Tooltip
                                    title={`Uses ${step.tools.length} MCP tool${step.tools.length > 1 ? "s" : ""}`}
                                  >
                                    <div className="flex items-center gap-1 rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-800">
                                      <Wrench size={12} />
                                      <span>{step.tools.length}</span>
                                    </div>
                                  </Tooltip>
                                )}
                              </h3>
                              <div className="text-muted-foreground text-sm" style={{ wordBreak: 'break-all', whiteSpace: 'normal' }}>
                                <Markdown animated={false}>
                                  {step.description}
                                </Markdown>
                              </div>
                              {step.tools && step.tools.length > 0 && (
                                <ToolsDisplay tools={step.tools} />
                              )}
                            </div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </CardContent>
            <CardFooter className="flex justify-end">
              {interruptMessage?.options?.length &&
                (!message.isStreaming || waitForFeedback) && (
                <motion.div
                  className="flex gap-2"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.3 }}
                >
                  {interruptMessage?.options.map((option) => (
                    <Button
                      key={option.value}
                      variant={
                        option.value === "accepted" ? "default" : "outline"
                      }
                      disabled={
                        !waitForFeedback ||
                        (option.value === "accepted" &&
                          isDebatePlan &&
                          !canAcceptDebate)
                      }
                      onClick={() => {
                        if (option.value === "accepted") {
                          void handleAccept();
                        } else {
                          onFeedback?.({
                            option,
                          });
                        }
                      }}
                    >
                      {option.value === "accepted"
                        ? startActionLabel
                        : option.value === "edit_plan"
                          ? t("editPlan")
                          : option.text}
                    </Button>
                  ))}
                </motion.div>
              )}
            </CardFooter>
          </Card>
        </motion.div>
      )}
    </div>
  );
}

function PodcastCard({
  className,
  message,
}: {
  className?: string;
  message: Message;
}) {
  const t = useTranslations("chat.research");
  const data = useMemo(() => {
    return JSON.parse(message.content ?? "");
  }, [message.content]);
  const title = useMemo<string | undefined>(() => data?.title, [data]);
  const audioUrl = useMemo<string | undefined>(() => data?.audioUrl, [data]);
  const isGenerating = useMemo(() => {
    return message.isStreaming;
  }, [message.isStreaming]);
  const hasError = useMemo(() => {
    return data?.error !== undefined;
  }, [data]);
  const [isPlaying, setIsPlaying] = useState(false);
  return (
    <Card className={cn("w-[508px]", className)}>
      <CardHeader>
        <div className="text-muted-foreground flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            {isGenerating ? <LoadingOutlined /> : <Headphones size={16} />}
            {!hasError ? (
              <RainbowText animated={isGenerating}>
                {isGenerating
                  ? t("generatingPodcast")
                  : isPlaying
                    ? t("nowPlayingPodcast")
                    : t("podcast")}
              </RainbowText>
            ) : (
              <div className="text-red-500">
                {t("errorGeneratingPodcast")}
              </div>
            )}
          </div>
          {!hasError && !isGenerating && (
            <div className="flex">
              <Tooltip title={t("downloadPodcast")}>
                <Button variant="ghost" size="icon" asChild>
                  <a
                    href={audioUrl}
                    download={`${(title ?? "podcast").replaceAll(" ", "-")}.mp3`}
                  >
                    <Download size={16} />
                  </a>
                </Button>
              </Tooltip>
            </div>
          )}
        </div>
        <CardTitle>
          <div className="text-lg font-medium">
            <RainbowText animated={isGenerating}>{title}</RainbowText>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {audioUrl ? (
          <audio
            className="w-full"
            src={audioUrl}
            controls
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
          />
        ) : (
          <div className="w-full"></div>
        )}
      </CardContent>
    </Card>
  );
}

function ToolsDisplay({ tools }: { tools: string[] }) {
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {tools.map((tool, index) => (
        <span
          key={index}
          className="rounded-md bg-muted px-2 py-1 text-xs font-mono text-muted-foreground"
        >
          {tool}
        </span>
      ))}
    </div>
  );
}
