// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { LoadingOutlined } from "@ant-design/icons";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Headphones,
  ChevronDown,
  ChevronRight,
  Lightbulb,
  Loader2,
  Wrench,
} from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import React, { useCallback, useMemo, useRef, useState } from "react";
import { useShallow } from "zustand/react/shallow";

import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { FavIcon } from "~/components/deer-flow/fav-icon";
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
import type { Message, Option, ToolCallRuntime } from "~/core/messages";
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
        <ToolActivityTimeline />
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

const TOOL_LABELS: Record<string, { sv: string; en: string }> = {
  web_search: { sv: "Webbsökning", en: "Web search" },
  crawl_tool: { sv: "Läser sida", en: "Read page" },
  python_repl_tool: { sv: "Python", en: "Python" },
  local_search_tool: { sv: "Lokalsök", en: "Local search" },
  file_system_tool: { sv: "Filer", en: "Files" },
  bash_tool: { sv: "Terminal", en: "Terminal" },
  react_sandbox_tool: { sv: "React-sandbox", en: "React sandbox" },
  query_all_models: { sv: "Alla modeller", en: "All models" },
  query_model_in_round: { sv: "Modell i runda", en: "Model in round" },
  query_gpt35: { sv: "GPT-3.5", en: "GPT-3.5" },
  query_gemini_flash: { sv: "Gemini 2.5 Flash", en: "Gemini 2.5 Flash" },
  query_deepseek: { sv: "DeepSeek", en: "DeepSeek" },
  query_grok4: { sv: "Grok-4", en: "Grok-4" },
  query_oneseek_local: { sv: "OneSeek", en: "OneSeek" },
  fact_check_responses: { sv: "Faktakoll", en: "Fact check" },
  run_meta_analysis: { sv: "Meta-analys", en: "Meta analysis" },
  synthesize_optimal_answer: { sv: "Syntes", en: "Synthesis" },
  start_debate_round: { sv: "Debattrunda", en: "Debate round" },
  collect_debate_votes: { sv: "Röstinsamling", en: "Collect votes" },
};
const TOOL_ACTIVITY_TEXT: Record<string, { sv: string; en: string }> = {
  web_search: { sv: "Söker på webben", en: "Searching the web" },
  crawl_tool: { sv: "Läser källor", en: "Reading sources" },
  python_repl_tool: { sv: "Kör Python", en: "Running Python" },
  local_search_tool: { sv: "Söker lokalt", en: "Searching locally" },
  file_system_tool: { sv: "Hantera filer", en: "Working with files" },
  bash_tool: { sv: "Kör kommandon", en: "Running commands" },
  react_sandbox_tool: { sv: "Bygger preview", en: "Building preview" },
  query_all_models: { sv: "Frågar modeller", en: "Querying models" },
  query_model_in_round: { sv: "Frågar modell", en: "Querying model" },
  query_gpt35: { sv: "Frågar GPT-3.5", en: "Querying GPT-3.5" },
  query_gemini_flash: { sv: "Frågar Gemini", en: "Querying Gemini" },
  query_deepseek: { sv: "Frågar DeepSeek", en: "Querying DeepSeek" },
  query_grok4: { sv: "Frågar Grok-4", en: "Querying Grok-4" },
  query_oneseek_local: { sv: "Frågar OneSeek", en: "Querying OneSeek" },
  fact_check_responses: { sv: "Faktakollar", en: "Fact checking" },
  run_meta_analysis: { sv: "Meta‑analyserar", en: "Running meta analysis" },
  synthesize_optimal_answer: { sv: "Syntetiserar", en: "Synthesizing" },
  start_debate_round: { sv: "Startar debatt", en: "Starting debate" },
  collect_debate_votes: { sv: "Samlar röster", en: "Collecting votes" },
};

function formatToolLabel(name: string, isSwedish: boolean) {
  const match = TOOL_LABELS[name];
  if (match) {
    return isSwedish ? match.sv : match.en;
  }
  const cleaned = name.replace(/_tool$/, "").replace(/_/g, " ").trim();
  if (!cleaned) return name;
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

function formatToolActivityText(name: string, isSwedish: boolean) {
  const match = TOOL_ACTIVITY_TEXT[name];
  if (match) {
    return isSwedish ? match.sv : match.en;
  }
  return formatToolLabel(name, isSwedish);
}

function getToolDetail(toolCall: ToolCallRuntime) {
  if (!toolCall.args || typeof toolCall.args !== "object") return null;
  const args = toolCall.args as Record<string, unknown>;
  const candidates = [
    args.query,
    args.url,
    args.keywords,
    args.path,
    args.model_key,
    args.display_name,
    args.raw,
    args.tool_input,
    args.input,
  ];
  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim()) {
      const trimmed = candidate.trim();
      return trimmed.length > 80 ? `${trimmed.slice(0, 77)}...` : trimmed;
    }
  }
  if (args._parsed && typeof args._parsed === "string" && args._parsed.trim()) {
    const trimmed = args._parsed.trim();
    return trimmed.length > 80 ? `${trimmed.slice(0, 77)}...` : trimmed;
  }
  return null;
}

function getToolStatus(toolCall: ToolCallRuntime) {
  const status = toolCall.status?.toLowerCase();
  if (status === "error" || status === "failed") return "error";
  if (status === "running" || status === "pending" || status === "in_progress") {
    return "running";
  }
  if (toolCall.result === undefined) return "running";
  return "success";
}

function getToolStatusLabel(status: "running" | "success" | "error", isSwedish: boolean) {
  if (status === "error") return isSwedish ? "Fel" : "Error";
  if (status === "running") return isSwedish ? "Kör" : "Running";
  return isSwedish ? "Klart" : "Done";
}

type SearchResult =
  | {
    type: "page";
    title: string;
    url: string;
    content?: string;
  }
  | {
    type: "image";
    image_url: string;
    image_description?: string;
  };

type ToolTimelineStep = {
  id: string;
  name: string;
  status: "running" | "success" | "error";
  label: string;
  activity: string;
  detail?: string;
  results?: Array<{ title: string; url: string }>;
  isThinking?: boolean;
};

function getDomainLabel(url?: string) {
  if (!url) return "";
  try {
    const hostname = new URL(url).hostname;
    return hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

function getWebSearchResults(result?: string) {
  if (!result) return [];
  const parsed = parseJSON<unknown>(result, null);
  const normalizeItems = (items: unknown[]) => {
    return items
      .map((item) => {
        if (!item || typeof item !== "object") return null;
        const record = item as Record<string, unknown>;
        const url =
          (typeof record.url === "string" && record.url) ||
          (typeof record.link === "string" && record.link) ||
          (typeof record.source === "string" && record.source);
        const title =
          (typeof record.title === "string" && record.title) ||
          (typeof record.name === "string" && record.name) ||
          (typeof record.snippet === "string" && record.snippet);
        if (!url) return null;
        return { title: title || url, url };
      })
      .filter((item): item is { title: string; url: string } => item != null)
      .slice(0, 6);
  };
  if (Array.isArray(parsed)) {
    return normalizeItems(parsed);
  }
  if (parsed && typeof parsed === "object") {
    const record = parsed as Record<string, unknown>;
    const candidates = [
      record.results,
      record.items,
      record.data,
      record.pages,
      record.sources,
    ];
    for (const candidate of candidates) {
      if (Array.isArray(candidate)) {
        return normalizeItems(candidate);
      }
    }
  }
  const urls = Array.from(new Set(result.match(/https?:\/\/[^\s")]+/g) ?? []));
  return urls.slice(0, 6).map((url) => ({ title: url, url }));
}

function ToolActivityTimeline() {
  const locale = useLocale();
  const isSwedish = locale.startsWith("sv");
  const responding = useStore((state) => state.responding);
  const { messageIds, messages } = useStore(
    useShallow((state) => ({
      messageIds: state.messageIds,
      messages: state.messages,
    })),
  );
  const toolCalls = useMemo(() => {
    let lastUserIndex = -1;
    for (let i = messageIds.length - 1; i >= 0; i -= 1) {
      const message = messages.get(messageIds[i]!);
      if (message?.role === "user") {
        lastUserIndex = i;
        break;
      }
    }
    const calls: ToolCallRuntime[] = [];
    const seen = new Set<string>();
    for (let i = messageIds.length - 1; i > lastUserIndex; i -= 1) {
      const message = messages.get(messageIds[i]!);
      if (!message?.toolCalls?.length) continue;
      for (const toolCall of message.toolCalls) {
        if (seen.has(toolCall.id)) continue;
        seen.add(toolCall.id);
        calls.push(toolCall);
      }
    }
    return calls.reverse();
  }, [messageIds, messages]);

  const steps = useMemo<ToolTimelineStep[]>(() => {
    return toolCalls.map((toolCall) => {
      const status = getToolStatus(toolCall);
      const label = formatToolLabel(toolCall.name ?? "tool", isSwedish);
      const activity = formatToolActivityText(toolCall.name ?? "tool", isSwedish);
      const detail = getToolDetail(toolCall) ?? undefined;
      const results =
        toolCall.name === "web_search"
          ? getWebSearchResults(toolCall.result)
          : undefined;
      return {
        id: toolCall.id,
        name: toolCall.name ?? "tool",
        status,
        label,
        activity,
        detail,
        results,
      };
    });
  }, [toolCalls, isSwedish]);

  const shouldShow = responding || steps.some((step) => step.status === "running");
  if (!shouldShow) return null;

  const timelineSteps: ToolTimelineStep[] = responding
    ? [
        {
          id: "thinking",
          name: "thinking",
          status: steps.length > 0 ? "success" : "running",
          label: isSwedish ? "Tänker" : "Thinking",
          activity: isSwedish ? "Tänker..." : "Thinking...",
          isThinking: true,
        },
        ...steps,
      ]
    : steps;

  return (
    <li className="px-4 pb-3">
      <div className="flex flex-col gap-4">
        {timelineSteps.map((step, index) => {
          const isLast = index === timelineSteps.length - 1;
          const statusLabel = getToolStatusLabel(step.status, isSwedish);
          const StatusIcon =
            step.status === "running"
              ? Loader2
              : step.status === "error"
                ? AlertTriangle
                : CheckCircle2;
          const statusClass =
            step.status === "running"
              ? "text-amber-500"
              : step.status === "error"
                ? "text-destructive"
                : "text-emerald-500";
          return (
            <div key={step.id} className="relative flex gap-3">
              <div className="relative flex flex-col items-center">
                <span className="flex h-5 w-5 items-center justify-center rounded-full border border-border/60 bg-background/70">
                  <StatusIcon
                    className={cn(
                      "h-3 w-3",
                      statusClass,
                      step.status === "running" && "animate-spin",
                    )}
                  />
                </span>
                {!isLast && <span className="mt-1 h-full w-px bg-border/60" />}
              </div>
              <div className={cn("flex-1", !isLast && "pb-4")}>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    {step.label}
                  </span>
                  <span className="text-sm font-medium text-foreground">
                    {step.activity}
                  </span>
                  <span className="rounded-full border border-border/60 px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                    {statusLabel}
                  </span>
                </div>
                {step.detail && (
                  <div className="mt-1 text-xs text-muted-foreground">
                    {step.detail}
                  </div>
                )}
                {step.results && step.results.length > 0 && (
                  <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {step.results.map((result) => {
                      const domainLabel = getDomainLabel(result.url);
                      return (
                        <a
                          key={result.url}
                          href={result.url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-start gap-2 rounded-lg border border-border/60 bg-background/60 px-3 py-2 text-xs transition-colors hover:bg-background/80"
                        >
                          {domainLabel ? (
                            <FavIcon url={result.url} title={result.title} className="mt-0.5" />
                          ) : (
                            <span className="mt-0.5 h-4 w-4 rounded-full bg-muted" />
                          )}
                          <div className="min-w-0">
                            <div className="truncate font-medium text-foreground">
                              {result.title}
                            </div>
                            <div className="truncate text-muted-foreground">
                              {domainLabel || result.url}
                            </div>
                          </div>
                        </a>
                      );
                    })}
                  </div>
                )}
                {step.isThinking && step.status === "running" && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    {isSwedish
                      ? "Förbereder nästa steg..."
                      : "Preparing next step..."}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </li>
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

  const reasoningContent = message.reasoningContent;
  const hasMainContent = Boolean(
    message.content && message.content.trim() !== "",
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
  const isThinking = Boolean(reasoningContent && !hasMainContent);

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
      {reasoningContent && (
        <ThoughtBlock
          content={reasoningContent}
          isStreaming={isThinking}
          hasMainContent={hasMainContent}
          contentChunks={message.reasoningContentChunks}
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
                <div style={{ wordBreak: 'break-all', whiteSpace: 'normal' }}>
                  <Markdown className="opacity-80" animated={false}>
                    {plan.thought}
                  </Markdown>
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
