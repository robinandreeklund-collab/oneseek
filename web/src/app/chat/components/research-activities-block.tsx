// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { PythonOutlined } from "@ant-design/icons";
import { motion } from "framer-motion";
import { LRUCache } from "lru-cache";
import { BookOpenText, FileText, PencilRuler, Search } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import React, { useMemo } from "react";
import SyntaxHighlighter from "react-syntax-highlighter";
import { docco } from "react-syntax-highlighter/dist/esm/styles/hljs";
import { dark } from "react-syntax-highlighter/dist/esm/styles/prism";

import { FavIcon } from "~/components/deer-flow/fav-icon";
import Image from "~/components/deer-flow/image";
import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { Markdown } from "~/components/deer-flow/markdown";
import { RainbowText } from "~/components/deer-flow/rainbow-text";
import { Tooltip } from "~/components/deer-flow/tooltip";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "~/components/ui/accordion";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Skeleton } from "~/components/ui/skeleton";
import { findMCPTool } from "~/core/mcp";
import { isPlannerAgent } from "~/core/messages";
import type { Message, ToolCallRuntime } from "~/core/messages";
import { useMessage, useStore } from "~/core/store";
import { parseJSON } from "~/core/utils";
import { cn } from "~/lib/utils";
import { DebateModelIcon } from "./debate-model-icon";

// Performance optimization constants
const MAX_ANIMATED_ITEMS = 10; // Only animate first 10 items
const ANIMATION_DELAY_MULTIPLIER = 0.05; // Reduced delay between animations

export function ResearchActivitiesBlock({
  className,
  researchId,
}: {
  className?: string;
  researchId: string;
}) {
  const activityIds = useStore((state) =>
    state.researchActivityIds.get(researchId),
  );
  const ongoing = useStore((state) => state.ongoingResearchId === researchId);
  
  // Guard against undefined activityIds
  if (!activityIds || activityIds.length === 0) {
    return (
      <>
        {ongoing && <LoadingAnimation className="mx-4 my-12" />}
      </>
    );
  }
  
  return (
    <>
      <ul className={cn("flex flex-col py-4", className)}>
        {activityIds.map(
          (activityId, i) => {
            // Performance optimization: limit animations for large lists
            const shouldAnimate = i < MAX_ANIMATED_ITEMS;
            const animationDelay = shouldAnimate ? Math.min(i * ANIMATION_DELAY_MULTIPLIER, 0.5) : 0;
            
            return (
              <motion.li
                key={activityId}
                style={{ transition: shouldAnimate ? "all 0.3s ease-out" : "none" }}
                initial={shouldAnimate ? { opacity: 0, y: 24 } : { opacity: 1, y: 0 }}
                animate={{ opacity: 1, y: 0 }}
                transition={shouldAnimate ? {
                  duration: 0.3, // Reduced from 0.4
                  delay: animationDelay,
                  ease: "easeOut",
                } : undefined}
              >
                <ActivityMessage messageId={activityId} />
                <ActivityListItem messageId={activityId} />
                {i !== activityIds.length - 1 && <hr className="my-8" />}
              </motion.li>
            );
          },
        )}
      </ul>
      {ongoing && <LoadingAnimation className="mx-4 my-12" />}
    </>
  );
}

const ActivityMessage = React.memo(({ messageId }: { messageId: string }) => {
  const message = useMessage(messageId);
  
  // Guard against undefined message (can happen during streaming/race conditions)
  if (!message) {
    return null;
  }
  
  if (message.agent) {
    // Show planner messages as plan cards (even if content is empty/streaming)
    if (isPlannerAgent(message.agent)) {
      return <PlanCard message={message} />;
    }
    // Skip reporter messages (they're shown in the Report tab)
    if (
      message.agent !== "reporter" &&
      message.agent !== "ai_compare_reporter" &&
      ![
        "ai_compare_query",
        "ai_compare_fact_check",
        "ai_compare_meta",
        "ai_compare_synth",
      ].includes(message.agent) &&
      message.content
    ) {
      return (
        <div className="px-4 py-2">
          <Markdown animated checkLinkCredibility>
            {message.content}
          </Markdown>
        </div>
      );
    }
  }
  return null;
});
ActivityMessage.displayName = "ActivityMessage";

// Component to display the research plan
const PlanCard = React.memo(({ message }: { message: Message }) => {
  const t = useTranslations("chat.research");
  const locale = useLocale();
  const isSwedish = locale.startsWith("sv");
  const plan = useMemo<{
    title?: string;
    thought?: string;
    steps?: { title?: string; description?: string; step_type?: string; need_search?: boolean }[];
  }>(() => {
    return parseJSON(message.content ?? "", {});
  }, [message.content]);

  const hasContent = Boolean(message.content && message.content.trim() !== "");

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="mb-4"
    >
      <Card className="w-full">
        <CardHeader>
          <CardTitle>
            <Markdown animated={message.isStreaming}>
              {`### ${plan.title || hasContent ? (plan.title ?? t("deepResearch")) : t("deepResearch")}`}
            </Markdown>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!hasContent && message.isStreaming && (
            <div className="flex items-center gap-2 text-sm opacity-70">
              <LoadingAnimation className="mx-0 my-0" />
              <span>
                {isSwedish ? "Skapar plan..." : "Creating research plan..."}
              </span>
            </div>
          )}
          {!hasContent && !message.isStreaming && (
            <div className="text-sm opacity-50">
              {isSwedish
                ? "Ingen planinformation tillgänglig"
                : "No plan content available"}
            </div>
          )}
          {hasContent && plan.thought && (
            <div className="break-all whitespace-normal">
              <Markdown className="opacity-80" animated={message.isStreaming}>
                {plan.thought}
              </Markdown>
            </div>
          )}
          {hasContent && plan.steps && plan.steps.length > 0 && (
            <ul className="my-2 flex list-decimal flex-col gap-4 border-l-[2px] pl-8">
              {plan.steps.map((step, i) => (
                <li key={`step-${i}`} className="break-all whitespace-normal">
                  <div className="flex items-start gap-2">
                    <div className="flex-1">
                      <h3 className="mb-1 flex items-center gap-2 text-lg font-medium">
                        <Markdown animated={false}>
                          {step.title ?? `Step ${i + 1}`}
                        </Markdown>
                      </h3>
                      {step.description && (
                        <Markdown className="text-sm opacity-70" animated={false}>
                          {step.description}
                        </Markdown>
                      )}
                      {step.step_type && (
                        <div className="mt-1 text-xs opacity-50">
                          Type: {step.step_type}
                          {step.need_search ?? false ? ' • Search: Yes' : ' • Search: No'}
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
});
PlanCard.displayName = "PlanCard";

const ActivityListItem = React.memo(({ messageId }: { messageId: string }) => {
  const message = useMessage(messageId);
  if (message) {
    if (message.toolCalls?.length) {
      const toolCallComponents = message.toolCalls
        .filter(toolCall => !(typeof toolCall.result === "string" && toolCall.result?.startsWith("Error")))
        .map(toolCall => {
          if (toolCall.name === "web_search") {
            return <WebSearchToolCall key={toolCall.id} toolCall={toolCall} />;
          } else if (toolCall.name === "crawl_tool") {
            return <CrawlToolCall key={toolCall.id} toolCall={toolCall} />;
          } else if (toolCall.name === "python_repl_tool") {
            return <PythonToolCall key={toolCall.id} toolCall={toolCall} />;
          } else if (toolCall.name === "local_search_tool") {
            return <RetrieverToolCall key={toolCall.id} toolCall={toolCall} />;
          } else {
            return <MCPToolCall key={toolCall.id} toolCall={toolCall} />;
          }
        });
      
      if (toolCallComponents.length > 0) {
        return <>{toolCallComponents}</>;
      }
    }
  }
  return null;
});
ActivityListItem.displayName = "ActivityListItem";

const __pageCache = new LRUCache<string, string>({ max: 100 });
type SearchResult =
  | {
    type: "page";
    title: string;
    url: string;
    content: string;
  }
  | {
    type: "image";
    image_url: string;
    image_description: string;
  };

function WebSearchToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const t = useTranslations("chat.research");
  const searching = useMemo(() => {
    return toolCall.result === undefined;
  }, [toolCall.result]);
  const searchResults = useMemo<SearchResult[]>(() => {
    let results: SearchResult[] | undefined = undefined;
    let parseError = false;
    
    try {
      if (toolCall.result) {
        results = parseJSON(toolCall.result, []);
      }
    } catch (error) {
      parseError = true;
      console.warn("Failed to parse search results:", error);
      results = undefined;
    }
    
    if (Array.isArray(results)) {
      results.forEach((result) => {
        if (result.type === "page") {
          __pageCache.set(result.url, result.title);
        }
      });
    } else {
      // If parsing failed, still try to show something useful
      results = [];
    }
    
    return results;
  }, [toolCall.result]);
  const pageResults = useMemo(
    () => searchResults?.filter((result) => result.type === "page"),
    [searchResults],
  );
  const imageResults = useMemo(
    () => searchResults?.filter((result) => result.type === "image"),
    [searchResults],
  );
  return (
    <section className="mt-4 pl-4">
      <div className="font-medium italic">
        <RainbowText
          className="flex items-center"
          animated={searchResults === undefined}
        >
          <Search size={16} className={"mr-2"} />
          <span>{t("searchingFor")}&nbsp;</span>
          <span className="max-w-[500px] overflow-hidden text-ellipsis whitespace-nowrap">
            {(toolCall.args as { query: string }).query}
          </span>
        </RainbowText>
      </div>
      <div className="pr-4">
        {pageResults && (
          <ul className="mt-2 flex flex-wrap gap-4">
            {searching &&
              [...Array(6)].map((_, i) => (
                <li
                  key={`search-result-${i}`}
                  className="flex h-40 w-40 gap-2 rounded-md text-sm"
                >
                  <Skeleton
                    className="to-accent h-full w-full rounded-md bg-gradient-to-tl from-slate-400"
                    style={{ animationDelay: `${i * 0.2}s` }}
                  />
                </li>
              ))}
            {pageResults
              .filter((result) => result.type === "page")
              .slice(0, 20) // Limit displayed results for performance
              .map((searchResult, i) => {
                const shouldAnimate = i < 6; // Only animate first 6 results
                return (
                  <motion.li
                    key={`search-result-${i}`}
                    className="text-muted-foreground bg-accent flex max-w-40 gap-2 rounded-md px-2 py-1 text-sm"
                    initial={shouldAnimate ? { opacity: 0, y: 10 } : { opacity: 1, y: 0 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={shouldAnimate ? {
                      duration: 0.15, // Reduced from 0.2
                      delay: Math.min(i * 0.05, 0.3), // Cap delay at 0.3s
                      ease: "easeOut",
                    } : undefined}
                  >
                    <FavIcon
                      className="mt-1"
                      url={searchResult.url}
                      title={searchResult.title}
                    />
                    <a href={searchResult.url} target="_blank">
                      {searchResult.title}
                    </a>
                  </motion.li>
                );
              })}
            {imageResults
              .slice(0, 10) // Limit displayed images for performance
              .map((searchResult, i) => {
                const shouldAnimate = i < 4; // Only animate first 4 images
                return (
                  <motion.li
                    key={`search-result-${i}`}
                    initial={shouldAnimate ? { opacity: 0, y: 10 } : { opacity: 1, y: 0 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={shouldAnimate ? {
                      duration: 0.15,
                      delay: Math.min(i * 0.05, 0.2),
                      ease: "easeOut",
                    } : undefined}
              >
                <a
                  className="flex flex-col gap-2 overflow-hidden rounded-md opacity-75 transition-opacity duration-300 hover:opacity-100"
                  href={searchResult.image_url}
                  target="_blank"
                >
                  <Image
                    src={searchResult.image_url}
                    alt={searchResult.image_description}
                    className="bg-accent h-40 w-40 max-w-full rounded-md bg-cover bg-center bg-no-repeat"
                    imageClassName="hover:scale-110"
                    imageTransition
                  />
                </a>
              </motion.li>
                );
              })}
          </ul>
        )}
      </div>
    </section>
  );
}

function CrawlToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const t = useTranslations("chat.research");
  const url = useMemo(
    () => (toolCall.args as { url: string }).url,
    [toolCall.args],
  );
  const title = useMemo(() => __pageCache.get(url), [url]);
  return (
    <section className="mt-4 pl-4">
      <div>
        <RainbowText
          className="flex items-center text-base font-medium italic"
          animated={toolCall.result === undefined}
        >
          <BookOpenText size={16} className={"mr-2"} />
          <span>{t("reading")}</span>
        </RainbowText>
      </div>
      <ul className="mt-2 flex flex-wrap gap-4">
        <motion.li
          className="text-muted-foreground bg-accent flex h-40 w-40 gap-2 rounded-md px-2 py-1 text-sm"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.15, // Reduced for better performance
            ease: "easeOut",
          }}
        >
          <FavIcon className="mt-1" url={url} title={title} />
          <a
            className="h-full flex-grow overflow-hidden text-ellipsis whitespace-nowrap"
            href={url}
            target="_blank"
          >
            {title ?? url}
          </a>
        </motion.li>
      </ul>
    </section>
  );
}

function RetrieverToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const t = useTranslations("chat.research");
  const searching = useMemo(() => {
    return toolCall.result === undefined;
  }, [toolCall.result]);
  const documents = useMemo<
    Array<{ id: string; title: string; content: string }>
  >(() => {
    return toolCall.result ? parseJSON(toolCall.result, []) : [];
  }, [toolCall.result]);
  return (
    <section className="mt-4 pl-4">
      <div className="font-medium italic">
        <RainbowText className="flex items-center" animated={searching}>
          <Search size={16} className={"mr-2"} />
          <span>{t("retrievingDocuments")}&nbsp;</span>
          <span className="max-w-[500px] overflow-hidden text-ellipsis whitespace-nowrap">
            {(toolCall.args as { keywords: string }).keywords}
          </span>
        </RainbowText>
      </div>
      <div className="pr-4">
        {documents && (
          <ul className="mt-2 flex flex-wrap gap-4">
            {searching &&
              [...Array(2)].map((_, i) => (
                <li
                  key={`search-result-${i}`}
                  className="flex h-40 w-40 gap-2 rounded-md text-sm"
                >
                  <Skeleton
                    className="to-accent h-full w-full rounded-md bg-gradient-to-tl from-slate-400"
                    style={{ animationDelay: `${i * 0.2}s` }}
                  />
                </li>
              ))}
            {documents?.map((doc, i) => {
              const shouldAnimate = i < 4; // Only animate first 4 documents
              return (
                <motion.li
                  key={`search-result-${i}`}
                  className="text-muted-foreground bg-accent flex max-w-40 gap-2 rounded-md px-2 py-1 text-sm"
                  initial={shouldAnimate ? { opacity: 0, y: 10 } : { opacity: 1, y: 0 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={shouldAnimate ? {
                    duration: 0.15,
                    delay: Math.min(i * 0.05, 0.2),
                    ease: "easeOut",
                  } : undefined}
                >
                  <FileText size={32} />
                  {doc.title} (chunk-{i},size-{doc.content.length})
                </motion.li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}

function PythonToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const t = useTranslations("chat.research");
  const code = useMemo<string | undefined>(() => {
    return (toolCall.args as { code?: string }).code;
  }, [toolCall.args]);
  const { resolvedTheme } = useTheme();
  return (
    <section className="mt-4 pl-4">
      <div className="flex items-center">
        <PythonOutlined className={"mr-2"} />
        <RainbowText
          className="text-base font-medium italic"
          animated={toolCall.result === undefined}
        >
          {t("runningPythonCode")}
        </RainbowText>
      </div>
      <div>
        <div className="bg-accent mt-2 max-h-[400px] max-w-[calc(100%-120px)] overflow-y-auto rounded-md p-2 text-sm">
          <SyntaxHighlighter
            language="python"
            style={resolvedTheme === "dark" ? dark : docco}
            customStyle={{
              background: "transparent",
              border: "none",
              boxShadow: "none",
            }}
          >
            {code?.trim() ?? ""}
          </SyntaxHighlighter>
        </div>
      </div>
      {toolCall.result && <PythonToolCallResult result={toolCall.result} />}
    </section>
  );
}

function PythonToolCallResult({ result }: { result: string }) {
  const t = useTranslations("chat.research");
  const { resolvedTheme } = useTheme();
  const hasError = useMemo(
    () => result.includes("Error executing code:\n"),
    [result],
  );
  const error = useMemo(() => {
    if (hasError) {
      const parts = result.split("```\nError: ");
      if (parts.length > 1) {
        return parts[1]!.trim();
      }
    }
    return null;
  }, [result, hasError]);
  const stdout = useMemo(() => {
    if (!hasError) {
      const parts = result.split("```\nStdout: ");
      if (parts.length > 1) {
        return parts[1]!.trim();
      }
    }
    return null;
  }, [result, hasError]);
  return (
    <>
      <div className="mt-4 font-medium italic">
        {hasError ? t("errorExecutingCode") : t("executionOutput")}
      </div>
      <div className="bg-accent mt-2 max-h-[400px] max-w-[calc(100%-120px)] overflow-y-auto rounded-md p-2 text-sm">
        <SyntaxHighlighter
          language="plaintext"
          style={resolvedTheme === "dark" ? dark : docco}
          customStyle={{
            color: hasError ? "red" : "inherit",
            background: "transparent",
            border: "none",
            boxShadow: "none",
          }}
        >
          {error ?? stdout ?? "(empty)"}
        </SyntaxHighlighter>
      </div>
    </>
  );
}

function MCPToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const tool = useMemo(() => findMCPTool(toolCall.name), [toolCall.name]);
  const { resolvedTheme } = useTheme();
  const locale = useLocale();
  const isSwedish = locale.startsWith("sv");
  const modelIconKey = useMemo(() => {
    if (toolCall.name === "query_model_in_round") {
      const args = toolCall.args as { model_key?: string };
      return args.model_key;
    }
    if (toolCall.args && typeof toolCall.args === "object") {
      const args = toolCall.args as { model_key?: string };
      if (args.model_key) return args.model_key;
    }
    if (toolCall.name === "query_gpt35") return "gpt-3.5-turbo";
    if (toolCall.name === "query_gemini_flash") return "gemini-2.5-flash";
    if (toolCall.name === "query_deepseek") return "deepseek-chat";
    if (toolCall.name === "query_grok4") return "grok-4-fast-reasoning";
    return undefined;
  }, [toolCall.args, toolCall.name]);
  const aiComparePayload = useMemo(() => {
    if (!toolCall.result) return null;
    const name = toolCall.name ?? "";
    if (
      [
        "query_gpt35",
        "query_gemini_flash",
        "query_deepseek",
        "query_grok4",
        "fact_check_responses",
        "run_meta_analysis",
        "synthesize_optimal_answer",
      ].includes(name)
    ) {
      return parseJSON<unknown>(toolCall.result, null) as
        | Record<string, unknown>
        | string
        | null;
    }
    return null;
  }, [toolCall.name, toolCall.result]);
  const modelLabelFromKey = useMemo(() => {
    const key =
      (aiComparePayload &&
      typeof aiComparePayload === "object" &&
      "model" in aiComparePayload
        ? String((aiComparePayload as Record<string, unknown>).model)
        : modelIconKey) ?? "";
    if (key === "gpt-3.5-turbo") return "GPT-3.5";
    if (key === "gemini-2.5-flash") return "Gemini 2.5 Flash";
    if (key === "deepseek-chat") return "DeepSeek";
    if (key === "grok-4-fast-reasoning") return "Grok-4";
    return "";
  }, [aiComparePayload, modelIconKey]);
  const modelDisplayName = useMemo(() => {
    if (aiComparePayload && typeof aiComparePayload === "object" && "display_name" in aiComparePayload) {
      const name = (aiComparePayload as Record<string, unknown>).display_name;
      if (typeof name === "string" && name.trim()) return name;
    }
    if (toolCall.args && typeof toolCall.args === "object") {
      const args = toolCall.args as { display_name?: string };
      if (args.display_name) return args.display_name;
    }
    return modelLabelFromKey || undefined;
  }, [aiComparePayload, modelLabelFromKey]);
  const resolvedModelKey = useMemo(() => {
    if (aiComparePayload && typeof aiComparePayload === "object" && "model" in aiComparePayload) {
      const key = String((aiComparePayload as Record<string, unknown>).model);
      if (key) return key;
    }
    return modelIconKey;
  }, [aiComparePayload, modelIconKey]);
  
  // Custom display name for debate tools
  const displayName = useMemo(() => {
    if (!toolCall.name) return "MCP tool";
    
    // Debate: querying a specific model
    if (toolCall.name === "query_model_in_round") {
      const args = toolCall.args as { model_key?: string };
      // Try to extract a clean model name
      let model = args.model_key ?? "model";
      // Clean up common ID formats if present (e.g., "(ID: gpt-3.5)")
      if (model.includes("(ID:")) {
        model = model.split("(ID:")[0]?.trim() || model;
      }
      return isSwedish ? `Väntar på ${model}...` : `Waiting for ${model}...`;
    } else if (toolCall.name === "query_gpt35") {
      const label = modelDisplayName ?? "GPT-3.5";
      return isSwedish ? `Väntar på ${label}...` : `Waiting for ${label}...`;
    } else if (toolCall.name === "query_gemini_flash") {
      const label = modelDisplayName ?? "Gemini 2.5 Flash";
      return isSwedish ? `Väntar på ${label}...` : `Waiting for ${label}...`;
    } else if (toolCall.name === "query_deepseek") {
      const label = modelDisplayName ?? "DeepSeek";
      return isSwedish ? `Väntar på ${label}...` : `Waiting for ${label}...`;
    } else if (toolCall.name === "query_grok4") {
      const label = modelDisplayName ?? "Grok-4";
      return isSwedish ? `Väntar på ${label}...` : `Waiting for ${label}...`;
    } else if (toolCall.name === "fact_check_responses") {
      return isSwedish ? "Väntar på faktakoll..." : "Waiting for fact check...";
    } else if (toolCall.name === "run_meta_analysis") {
      return isSwedish ? "Väntar på meta‑analys..." : "Waiting for meta analysis...";
    } else if (toolCall.name === "synthesize_optimal_answer") {
      return isSwedish ? "Väntar på syntes..." : "Waiting for synthesis...";
    } else if (toolCall.name === "start_debate_round") {
        const args = toolCall.args as { round_number?: number };
        return isSwedish
          ? `Startar runda ${args.round_number ?? ""}...`
          : `Starting Round ${args.round_number ?? ""}...`;
    } else if (toolCall.name === "collect_debate_votes") {
        return isSwedish ? "Samlar röster från alla modeller..." : "Collecting votes from all models...";
    }
    
    // Default: just function name
    return `${toolCall.name}()`;
  }, [toolCall.name, toolCall.args, isSwedish, modelDisplayName]);

  // Is this a debate tool that has finished running?
  // If so, we might want to change the text from "Waiting..." to "Responded"
  const statusText = useMemo(() => {
    if (toolCall.result !== undefined) {
       if (toolCall.name === "query_model_in_round") {
           const args = toolCall.args as { model_key?: string };
           let model = args.model_key ?? "model";
           if (model.includes("(ID:")) {
             model = model.split("(ID:")[0]?.trim() || model;
           }
           return isSwedish ? `${model} svarade` : `${model} responded`;
       }
       if (toolCall.name === "query_gpt35") {
         const label = modelDisplayName ?? "GPT-3.5";
         return isSwedish ? `${label} svarade` : `${label} responded`;
       }
       if (toolCall.name === "query_gemini_flash") {
         const label = modelDisplayName ?? "Gemini 2.5 Flash";
         return isSwedish ? `${label} svarade` : `${label} responded`;
       }
       if (toolCall.name === "query_deepseek") {
         const label = modelDisplayName ?? "DeepSeek";
         return isSwedish ? `${label} svarade` : `${label} responded`;
       }
       if (toolCall.name === "query_grok4") {
         const label = modelDisplayName ?? "Grok-4";
         return isSwedish ? `${label} svarade` : `${label} responded`;
       }
      if (toolCall.name === "fact_check_responses") {
        return isSwedish ? "Faktakoll klart" : "Fact check completed";
      }
      if (toolCall.name === "run_meta_analysis") {
        return isSwedish ? "Meta‑analys klar" : "Meta analysis completed";
      }
      if (toolCall.name === "synthesize_optimal_answer") {
        return isSwedish ? "Syntes klar" : "Synthesis completed";
      }
       if (toolCall.name === "start_debate_round") return isSwedish ? "Runda startad" : "Round started";
       if (toolCall.name === "collect_debate_votes") return isSwedish ? "Röster insamlade" : "Votes collected";
       return isSwedish ? `Körde ${toolCall.name}()` : `Executed ${toolCall.name}()`;
    }
    return isSwedish ? `Kör ${displayName}` : `Running ${displayName}`;
  }, [displayName, toolCall.name, toolCall.result, toolCall.args, isSwedish, modelDisplayName]);

  const displayResult = useMemo(() => {
    if (!toolCall.result) return "";
    if (aiComparePayload) {
      if (typeof aiComparePayload === "string") {
        return aiComparePayload;
      }
      if (Array.isArray(aiComparePayload)) {
        return JSON.stringify(aiComparePayload, null, 2);
      }
      if (typeof aiComparePayload === "object") {
        const payload = aiComparePayload as Record<string, unknown>;
        if (typeof payload.response === "string") {
          return payload.response;
        }
        if (typeof payload.error === "string") {
          return payload.error;
        }
        if (payload.synthesis) {
          if (typeof payload.synthesis === "string") {
            return payload.synthesis;
          }
          return JSON.stringify(payload.synthesis, null, 2);
        }
        return JSON.stringify(payload, null, 2);
      }
    }
    return toolCall.result;
  }, [aiComparePayload, toolCall.result]);

  const isAiCompareTool = useMemo(() => {
    if (toolCall.name !== "query_model_in_round") return false;
    if (!toolCall.args || typeof toolCall.args !== "object") return false;
    const args = toolCall.args as { user_query?: string; round_number?: number };
    return Boolean(args.user_query) && !args.round_number;
  }, [toolCall.args, toolCall.name]);

  return (
    <section className="mt-4 pl-4">
      <div className="w-fit overflow-y-auto rounded-md py-0">
        <Accordion
          type="single"
          collapsible
          className="w-full"
          defaultValue={isAiCompareTool ? "item-1" : undefined}
        >
          <AccordionItem value="item-1">
            <AccordionTrigger>
              <Tooltip title={tool?.description}>
                <div className="flex items-center font-medium italic">
                  {resolvedModelKey ? (
                    <DebateModelIcon modelKey={resolvedModelKey} size={16} className="mr-2" />
                  ) : (
                    <PencilRuler size={16} className={"mr-2"} />
                  )}
                  <RainbowText
                    className="pr-0.5 text-base font-medium italic"
                    animated={toolCall.result === undefined}
                  >
                    {statusText}
                  </RainbowText>
                </div>
              </Tooltip>
            </AccordionTrigger>
            {toolCall.result && (
              <div className="px-2 pb-2 text-xs opacity-70">
                {displayResult.length > 240
                  ? `${displayResult.slice(0, 240)}...`
                  : displayResult}
              </div>
            )}
            <AccordionContent>
              {toolCall.result && (
                <div className="bg-accent max-h-[400px] max-w-[560px] overflow-y-auto rounded-md text-sm">
                  {/* Show arguments if available (for transparency) */}
                  <div className="mb-2 p-2 border-b border-border/50 text-xs opacity-70">
                    <strong>Input:</strong>
                    <pre className="whitespace-pre-wrap mt-1">
                      {JSON.stringify(toolCall.args, null, 2)}
                    </pre>
                  </div>
                  
                  <SyntaxHighlighter
                    language="markdown" // Changed to markdown for better reading of text responses
                    style={resolvedTheme === "dark" ? dark : docco}
                    wrapLongLines={true}
                    customStyle={{
                      background: "transparent",
                      border: "none",
                      boxShadow: "none",
                    }}
                  >
                    {displayResult.trim()}
                  </SyntaxHighlighter>
                </div>
              )}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </section>
  );
}
