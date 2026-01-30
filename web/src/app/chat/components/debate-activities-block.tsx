// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { CheckCircle2, Loader2, PencilRuler } from "lucide-react";
import { motion } from "framer-motion";
import { useTheme } from "next-themes";
import { useTranslations } from "next-intl";
import React, { useMemo } from "react";
import SyntaxHighlighter from "react-syntax-highlighter";
import { docco } from "react-syntax-highlighter/dist/esm/styles/hljs";
import { dark } from "react-syntax-highlighter/dist/esm/styles/prism";

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
import { findMCPTool } from "~/core/mcp";
import { isPlannerAgent } from "~/core/messages";
import type { Message, ToolCallRuntime } from "~/core/messages";
import { useMessage, useStore } from "~/core/store";
import { cn } from "~/lib/utils";

import { DebateModelIcon } from "./debate-model-icon";
// Performance optimization constants
const MAX_ANIMATED_ITEMS = 10; // Only animate first 10 items
const ANIMATION_DELAY_MULTIPLIER = 0.05; // Reduced delay between animations

export function DebateActivitiesBlock({
  className,
  sessionId,
}: {
  className?: string;
  sessionId: string;
}) {
  const activityIds = useStore((state) =>
    state.debateActivityIds.get(sessionId),
  );
  const ongoing = useStore((state) => state.ongoingDebateSessionId === sessionId);
  
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
                  duration: 0.3,
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
    // Show planner messages as plan cards (if needed in future)
    if (isPlannerAgent(message.agent)) {
      return <PlanCard message={message} />;
    }
    // Show debate agent messages with markdown formatting
    if (message.content) {
      const agentLabelMap: Record<string, string> = {
        external_ai_caller: "Modellerna svarar",
        fact_checker: "Faktakontroll",
        synthesizer: "Syntes",
        moderator: "Moderator",
        debate_orchestrator: "Orkestrator",
      };
      const agentLabel = agentLabelMap[message.agent] ?? message.agent;
      return (
        <div className="px-4 py-2">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {agentLabel}
          </div>
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

// Component to display the debate plan (if needed)
const PlanCard = React.memo(({ message }: { message: Message }) => {
  const t = useTranslations("chat.debate");
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="mb-4 px-4"
    >
      <div className="rounded-lg border border-border bg-muted/50 p-4">
        <div className="mb-2 font-semibold">Debate Plan</div>
        {message.content ? (
          <Markdown animated={message.isStreaming}>
            {message.content}
          </Markdown>
        ) : (
          <div className="text-sm opacity-50">
            Creating debate plan...
          </div>
        )}
      </div>
    </motion.div>
  );
});
PlanCard.displayName = "PlanCard";

const ActivityListItem = React.memo(({ messageId }: { messageId: string }) => {
  const message = useMessage(messageId);
  if (message?.toolCalls?.length) {
    const toolCallComponents = message.toolCalls
      .filter(toolCall => !(typeof toolCall.result === "string" && toolCall.result?.startsWith("Error")))
      .map(toolCall => {
        // For debate tools, use MCPToolCall which handles them nicely
        return <MCPToolCall key={toolCall.id} toolCall={toolCall} />;
      });
    
    if (toolCallComponents.length > 0) {
      return <>{toolCallComponents}</>;
    }
  }
  return null;
});
ActivityListItem.displayName = "ActivityListItem";

// MCPToolCall component for debate tools (copied from research-activities-block.tsx)
function MCPToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const tool = useMemo(() => findMCPTool(toolCall.name), [toolCall.name]);
  const { resolvedTheme } = useTheme();
  const modelKey = useMemo(() => {
    if (toolCall.name !== "query_model_in_round") return undefined;
    const args = toolCall.args as { model_key?: string };
    return args.model_key;
  }, [toolCall.args, toolCall.name]);
  
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
      return model;
    } else if (toolCall.name === "start_debate_round") {
        const args = toolCall.args as { round_number?: number };
        return `Round ${args.round_number ?? ""}`;
    } else if (toolCall.name === "collect_debate_votes") {
        return "Collecting votes from all models...";
    }
    
    // Default: just function name
    return `${toolCall.name}()`;
  }, [toolCall.name, toolCall.args]);

  // Is this a debate tool that has finished running?
  // If so, we might want to change the text from "Waiting..." to "Responded"
  const statusText = useMemo(() => {
    if (toolCall.result !== undefined) {
      if (toolCall.name === "query_model_in_round") {
        return `${displayName} responded`;
      }
      if (toolCall.name === "start_debate_round") return "Round started";
      if (toolCall.name === "collect_debate_votes") return "Votes collected";
      return `Executed ${toolCall.name}()`;
    }
    if (toolCall.name === "query_model_in_round") {
      return `Waiting for ${displayName}`;
    }
    return `Running ${displayName}`;
  }, [displayName, toolCall.name, toolCall.result]);
  
  const isRunning = toolCall.result === undefined;

  return (
    <section className="mt-4 pl-4">
      <div className="w-fit overflow-y-auto rounded-md py-0">
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="item-1">
            <AccordionTrigger>
              <Tooltip title={tool?.description}>
                <div className="flex items-center gap-2 font-medium italic">
                  {toolCall.name === "query_model_in_round" ? (
                    <DebateModelIcon modelKey={modelKey} />
                  ) : (
                    <PencilRuler size={16} />
                  )}
                  {isRunning ? (
                    <Loader2 size={14} className="animate-spin text-muted-foreground" />
                  ) : (
                    <CheckCircle2 size={14} className="text-emerald-500" />
                  )}
                  <RainbowText
                    className="pr-0.5 text-base font-medium italic"
                    animated={isRunning}
                  >
                    {statusText}
                  </RainbowText>
                </div>
              </Tooltip>
            </AccordionTrigger>
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
                    {toolCall.result.trim()}
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
