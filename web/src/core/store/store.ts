// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { nanoid } from "nanoid";
import { toast } from "sonner";
import { create } from "zustand";
import { useShallow } from "zustand/react/shallow";

import { chatStream, generatePodcast } from "../api";
import { isPlannerAgent, mergeMessage } from "../messages";
import type {
  Citation,
  Message,
  Resource,
  ToolAction,
  WorkspaceFile,
} from "../messages";
import { parseJSON } from "../utils";

import { getChatStreamSettings } from "./settings-store";

const THREAD_ID = nanoid();

// Helper function to get locale from cookie
function getLocaleFromCookie(): string {
  if (typeof document === "undefined") return "en";
  
  const cookies = document.cookie.split(";");
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split("=");
    if (name === "NEXT_LOCALE" && value) {
      return decodeURIComponent(value);
    }
  }
  return "en";
}

// Helper function to get translated podcast prompt
function getPodcastPromptTranslation(): string {
  const locale = getLocaleFromCookie();
  const translations: Record<string, string> = {
    "en": "Please generate a podcast for the above research.",
    "sv": "Vänligen generera en podcast för ovanstående forskning.",
    "zh": "请为以上研究生成播客。"
  };
  return translations[locale] ?? translations["en"]!;
}


export const useStore = create<{
  responding: boolean;
  threadId: string;
  messageIds: string[];
  messages: Map<string, Message>;
  researchIds: string[];
  researchPlanIds: Map<string, string>;
  researchReportIds: Map<string, string>;
  researchActivityIds: Map<string, string[]>;
  researchQueries: Map<string, string>;
  researchCitations: Map<string, Citation[]>;
  ongoingResearchId: string | null;
  openResearchId: string | null;
  coderSessionIds: string[];
  coderActivityIds: Map<string, string[]>;
  coderWorkspaceFiles: Map<string, WorkspaceFile[]>;
  coderWorkspaceSnapshot: Map<string, WorkspaceFile[]>;
  ongoingCoderSessionId: string | null;
  openCoderSessionId: string | null;
  debateSessionIds: string[];
  debateActivityIds: Map<string, string[]>;
  ongoingDebateSessionId: string | null;
  openDebateSessionId: string | null;

  appendMessage: (message: Message) => void;
  updateMessage: (message: Message) => void;
  updateMessages: (messages: Message[]) => void;
  openResearch: (researchId: string | null) => void;
  closeResearch: () => void;
  setOngoingResearch: (researchId: string | null) => void;
  setCitations: (researchId: string, citations: Citation[]) => void;
  openCoder: (sessionId: string | null) => void;
  closeCoder: () => void;
  setOngoingCoderSession: (sessionId: string | null) => void;
  setCoderWorkspaceSnapshot: (sessionId: string, files: WorkspaceFile[]) => void;
  openDebate: (sessionId: string | null) => void;
  closeDebate: () => void;
  setOngoingDebateSession: (sessionId: string | null) => void;
  updateToolActions: (actions: ToolAction[], liveUpdate?: boolean) => void;
}>((set) => ({
  responding: false,
  threadId: THREAD_ID,
  messageIds: [],
  messages: new Map<string, Message>(),
  researchIds: [],
  researchPlanIds: new Map<string, string>(),
  researchReportIds: new Map<string, string>(),
  researchActivityIds: new Map<string, string[]>(),
  researchQueries: new Map<string, string>(),
  researchCitations: new Map<string, Citation[]>(),
  ongoingResearchId: null,
  openResearchId: null,
  coderSessionIds: [],
  coderActivityIds: new Map<string, string[]>(),
  coderWorkspaceFiles: new Map<string, WorkspaceFile[]>(),
  coderWorkspaceSnapshot: new Map<string, WorkspaceFile[]>(),
  ongoingCoderSessionId: null,
  openCoderSessionId: null,
  debateSessionIds: [],
  debateActivityIds: new Map<string, string[]>(),
  ongoingDebateSessionId: null,
  openDebateSessionId: null,

  appendMessage(message: Message) {
    set((state) => {
      // Prevent duplicate message IDs in the array to avoid React key warnings
      const newMessageIds = state.messageIds.includes(message.id)
        ? state.messageIds
        : [...state.messageIds, message.id];
      return {
        messageIds: newMessageIds,
        messages: new Map(state.messages).set(message.id, message),
      };
    });
  },
  updateMessage(message: Message) {
    set((state) => ({
      messages: new Map(state.messages).set(message.id, message),
    }));
  },
  updateMessages(messages: Message[]) {
    set((state) => {
      const newMessages = new Map(state.messages);
      messages.forEach((m) => newMessages.set(m.id, m));
      return { messages: newMessages };
    });
  },
  openResearch(researchId: string | null) {
    set({ openResearchId: researchId });
  },
  closeResearch() {
    set({ openResearchId: null });
  },
  setOngoingResearch(researchId: string | null) {
    set({ ongoingResearchId: researchId });
  },
  setCitations(researchId: string, citations: Citation[]) {
    set((state) => ({
      researchCitations: new Map(state.researchCitations).set(researchId, citations),
    }));
  },
  openCoder(sessionId: string | null) {
    set({ openCoderSessionId: sessionId });
  },
  closeCoder() {
    set({ openCoderSessionId: null });
  },
  setOngoingCoderSession(sessionId: string | null) {
    set({ ongoingCoderSessionId: sessionId });
  },
  setCoderWorkspaceSnapshot(sessionId: string, files: WorkspaceFile[]) {
    set((state) => ({
      coderWorkspaceSnapshot: new Map(state.coderWorkspaceSnapshot).set(
        sessionId,
        files,
      ),
    }));
  },
  openDebate(sessionId: string | null) {
    console.log("🎯 DEBUG openDebate called with sessionId=", sessionId);
    set({ openDebateSessionId: sessionId });
    console.log("🎯 DEBUG openDebateSessionId set to=", useStore.getState().openDebateSessionId);
  },
  closeDebate() {
    set({ openDebateSessionId: null });
  },
  setOngoingDebateSession(sessionId: string | null) {
    set({ ongoingDebateSessionId: sessionId });
  },
  updateToolActions(actions: ToolAction[], liveUpdate = true) {
    const currentMessages = useStore.getState().messages;
    const updatedMessages = new Map(currentMessages);
    const updatedMessageIds = new Set<string>();
    const toolActions = actions.filter((action) => action != null);
    const updatedWorkspaceFiles = new Map(useStore.getState().coderWorkspaceFiles);

    toolActions.forEach((action) => {
      let targetMessage = findMessageByToolCallId(action.tool_call_id);
      if (!targetMessage) {
        const toolName = action.tool_name ?? "unknown";
        const fallbackAgent =
          toolName === "query_gpt35" ||
          toolName === "query_gemini_flash" ||
          toolName === "query_deepseek" ||
          toolName === "query_grok4"
            ? "ai_compare_query"
            : toolName === "fact_check_responses"
              ? "ai_compare_fact_check"
              : toolName === "run_meta_analysis"
                ? "ai_compare_meta"
                : toolName === "synthesize_optimal_answer"
                  ? "ai_compare_synth"
                  : "researcher";
        const toolInput = action.tool_input;
        let args: Record<string, unknown> = {};
        if (typeof toolInput === "string" && toolInput.trim()) {
          const trimmed = toolInput.trim();
          if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
            try {
              const parsed = JSON.parse(trimmed);
              args = typeof parsed === "object" && parsed ? (parsed as Record<string, unknown>) : {};
            } catch {
              args = { raw: toolInput };
            }
          } else {
            args = { raw: toolInput };
          }
        }
        const result =
          action.tool_output !== undefined
            ? typeof action.tool_output === "string"
              ? action.tool_output
              : JSON.stringify(action.tool_output, null, 2)
            : undefined;
        const toolCallMessageId = `tool-${action.tool_call_id}`;
        if (!existsMessage(toolCallMessageId)) {
          const message: Message = {
            id: toolCallMessageId,
            threadId: useStore.getState().threadId,
            agent: fallbackAgent,
            role: "assistant",
            content: "",
            contentChunks: [],
            reasoningContent: "",
            reasoningContentChunks: [],
            isStreaming: action.status === "running",
            toolCalls: [
              {
                id: action.tool_call_id,
                name: toolName,
                args,
                result,
                status: action.status,
              },
            ],
          };
          appendMessage(message);
          updatedMessages.set(message.id, message);
          updatedMessageIds.add(message.id);
        }
        targetMessage = findMessageByToolCallId(action.tool_call_id);
        if (!targetMessage) return;
      }
      const toolCalls = targetMessage.toolCalls ?? [];
      const updatedToolCalls = toolCalls.map((toolCall) => {
        if (toolCall.id !== action.tool_call_id) return toolCall;
        const rawInput = action.input ?? action.tool_input;
        const mergedArgs =
          rawInput && typeof rawInput === "object"
            ? (rawInput as Record<string, unknown>)
            : toolCall.args;
        const rawOutput = action.output ?? action.tool_output;
        const mergedResult =
          rawOutput !== undefined
            ? typeof rawOutput === "string"
              ? rawOutput
              : JSON.stringify(rawOutput, null, 2)
            : toolCall.result;
        const mergedStatus = action.status ?? toolCall.status;
        return {
          ...toolCall,
          name: action.tool_name ?? toolCall.name,
          args: mergedArgs,
          result: mergedResult,
          status: mergedStatus,
        };
      });
      if (action.workspace_files?.length) {
        updatedWorkspaceFiles.set(targetMessage.id, action.workspace_files);
      }
      const updatedMessage = {
        ...targetMessage,
        toolCalls: updatedToolCalls,
        ...(liveUpdate ? { isStreaming: true } : {}),
      };
      updatedMessages.set(updatedMessage.id, updatedMessage);
      updatedMessageIds.add(updatedMessage.id);
    });

    if (updatedMessageIds.size > 0) {
      set({
        messages: updatedMessages,
        coderWorkspaceFiles: updatedWorkspaceFiles,
      });
    }
  },
}));

export async function sendMessage(
  content?: string,
  {
    interruptFeedback,
    resources,
  }: {
    interruptFeedback?: string;
    resources?: Array<Resource>;
  } = {},
  options: { abortSignal?: AbortSignal } = {},
) {
  if (content != null) {
    appendMessage({
      id: nanoid(),
      threadId: THREAD_ID,
      role: "user",
      content: content,
      contentChunks: [content],
      resources,
    });
  }

  const settings = getChatStreamSettings();
  const stream = chatStream(
    content ?? "[REPLAY]",
    {
      thread_id: THREAD_ID,
      interrupt_feedback: interruptFeedback,
      resources,
      auto_accepted_plan: settings.autoAcceptedPlan,
      enable_clarification: settings.enableClarification ?? false,
      max_clarification_rounds: settings.maxClarificationRounds ?? 3,
      enable_deep_thinking: settings.enableDeepThinking ?? false,
      enable_background_investigation:
        settings.enableBackgroundInvestigation ?? true,
      enable_ai_comparison: settings.enableAiComparison ?? false,
      enable_debate_mode: settings.enableDebateMode ?? false,
      enable_code_mode: settings.enableCodeMode ?? false,
      enable_web_search: settings.enableWebSearch ?? true,
      max_plan_iterations: settings.maxPlanIterations,
      max_step_num: settings.maxStepNum,
      max_search_results: settings.maxSearchResults,
      report_style: settings.reportStyle,
      mcp_settings: settings.mcpSettings,
    },
    options,
  );

  setResponding(true);
  let messageId: string | undefined;
  let lastMessage: Message | undefined;
  const pendingUpdates = new Map<string, Message>();
  let updateTimer: NodeJS.Timeout | undefined;

  const scheduleUpdate = () => {
    if (updateTimer) clearTimeout(updateTimer);
    updateTimer = setTimeout(() => {
      // Batch update message status
      if (pendingUpdates.size > 0) {
        useStore.getState().updateMessages(Array.from(pendingUpdates.values()));
        pendingUpdates.clear();
      }
    }, 16); // ~60fps
  };

  try {
    for await (const event of stream) {
      const { type, data } = event;
      let message: Message | undefined;
      
      // Handle citations event: store citations for the current research
      if (type === "data") {
        const metadata = data as { tool_actions?: ToolAction[]; live_update?: boolean };
        const actions = Array.isArray(metadata.tool_actions)
          ? metadata.tool_actions
          : [];
        if (actions.length > 0) {
          useStore.getState().updateToolActions(
            actions,
            Boolean(metadata.live_update),
          );
        }
        continue;
      }
      if (type === "citations") {
        const ongoingResearchId = useStore.getState().ongoingResearchId;
        if (ongoingResearchId && data.citations) {
          useStore.getState().setCitations(ongoingResearchId, data.citations);
        }
        continue;
      }
      
      // Handle tool_call_result specially: use the message that contains the tool call
      if (type === "tool_call_result") {
        message = findMessageByToolCallId(data.tool_call_id);
        if (message) {
          // Use the found message's ID, not data.id
          messageId = message.id;
        } else {
          // Shouldn't happen, but handle gracefully
          if (process.env.NODE_ENV === "development") {
            console.warn(`Tool call result without matching message: ${data.tool_call_id}`);
          }
          continue; // Skip this event
        }
      } else {
        // For other event types, use data.id
        messageId = data.id;
        
        if (!existsMessage(messageId)) {
          message = {
            id: messageId,
            threadId: data.thread_id,
            agent: data.agent,
            role: data.role,
            content: "",
            contentChunks: [],
            reasoningContent: "",
            reasoningContentChunks: [],
            isStreaming: true,
            interruptFeedback,
          };
          appendMessage(message);
        }
      }
      
      message ??= getMessage(messageId);
      if (message) {
        message = mergeMessage(message, event);
        lastMessage = message;
        // Collect pending messages for update, instead of updating immediately.
        pendingUpdates.set(message.id, message);
        scheduleUpdate();
      }
    }
  } catch (error) {
    console.error("[Store] Error processing chat event:", error);
    console.error("[Store] Current message:", lastMessage);
    console.error("[Store] Message ID:", messageId);
    toast("An error occurred while generating the response. Please try again.");
    // Update message status.
    // TODO: const isAborted = (error as Error).name === "AbortError";
    if (messageId != null) {
      const message = getMessage(messageId);
      if (message?.isStreaming) {
        message.isStreaming = false;
        useStore.getState().updateMessage(message);
      }
    }
    useStore.getState().setOngoingResearch(null);
    useStore.getState().setOngoingCoderSession(null);
  } finally {
    setResponding(false);
    // Ensure all pending updates are processed.
    if (updateTimer) clearTimeout(updateTimer);
    if (pendingUpdates.size > 0) {
      useStore.getState().updateMessages(Array.from(pendingUpdates.values()));
    }

  }
}

function setResponding(value: boolean) {
  useStore.setState({ responding: value });
}

function existsMessage(id: string) {
  return useStore.getState().messageIds.includes(id);
}

function getMessage(id: string) {
  return useStore.getState().messages.get(id);
}

function findMessageByToolCallId(toolCallId: string) {
  return Array.from(useStore.getState().messages.values())
    .reverse()
    .find((message) => {
      if (message.toolCalls) {
        return message.toolCalls.some((toolCall) => toolCall.id === toolCallId);
      }
      return false;
    });
}

function appendMessage(message: Message) {
  // DEBUG: Log all messages to trace debate flow
  if (message.agent?.includes("debate")) {
    console.log("🔍 DEBUG appendMessage: agent=", message.agent, "id=", message.id);
  }
  if (message.agent === "external_ai_caller") {
    console.log("🔍 DEBUG appendMessage: EXTERNAL_AI_CALLER detected! agent=", message.agent, "id=", message.id);
  }
  
  if (
    message.agent === "reporter" ||
    message.agent === "researcher" ||
    message.agent === "analyst" ||
    message.agent === "ai_comparison" ||
    message.agent === "ai_compare_query" ||
    message.agent === "ai_compare_fact_check" ||
    message.agent === "ai_compare_meta" ||
    message.agent === "ai_compare_synth" ||
    message.agent === "ai_compare_reporter"
  ) {
    if (!getOngoingResearchId()) {
      const id = message.id;
      appendResearch(id);
      openResearch(id);
    }
    appendResearchActivity(message);
  } else if (
    message.agent === "coder" ||
    message.agent === "code_researcher" ||
    message.agent === "code_architect" ||
    message.agent === "code_reviewer" ||
    message.agent === "code_refiner" ||
    message.agent === "code_tester" ||
    message.agent === "code_reporter"
  ) {
    if (!getOngoingCoderSessionId()) {
      const id = message.id;
      appendCoderSession(id);
      openCoder(id);
    }
    appendCoderActivity(message);
  } else if (
    message.agent === "debate_orchestrator" ||
    message.agent === "external_ai_caller" ||
    message.agent === "fact_checker" ||
    message.agent === "synthesizer" ||
    message.agent === "moderator"
  ) {
    console.log("🎯 DEBUG: debate message detected! agent=", message.agent, "Opening sidebar...");
    if (!getOngoingDebateSessionId()) {
      const id = message.id;
      console.log("🎯 DEBUG: Calling appendDebateSession and openDebate with id=", id);
      appendDebateSession(id);
      openDebate(id);
    }
    appendDebateActivity(message);
  }
  useStore.getState().appendMessage(message);
}

function updateMessage(message: Message) {
  if (
    getOngoingResearchId() &&
    (message.agent === "reporter" || message.agent === "ai_compare_reporter") &&
    !message.isStreaming
  ) {
    useStore.getState().setOngoingResearch(null);
  }
  if (
    getOngoingCoderSessionId() &&
    message.agent === "coder" &&
    !message.isStreaming
  ) {
    useStore.getState().setOngoingCoderSession(null);
  }
  if (
    getOngoingDebateSessionId() &&
    (message.agent === "debate_orchestrator" ||
      message.agent === "external_ai_caller" ||
      message.agent === "fact_checker" ||
      message.agent === "synthesizer" ||
      message.agent === "moderator") &&
    !message.isStreaming
  ) {
    // Don't close debate session when streaming completes - keep it open
    // useStore.getState().setOngoingDebateSession(null);
  }
  useStore.getState().updateMessage(message);
}

function getOngoingResearchId() {
  return useStore.getState().ongoingResearchId;
}

function getOngoingCoderSessionId() {
  return useStore.getState().ongoingCoderSessionId;
}

function getOngoingDebateSessionId() {
  return useStore.getState().ongoingDebateSessionId;
}

function appendCoderSession(sessionId: string) {
  const messageIds = [sessionId];
  useStore.setState({
    ongoingCoderSessionId: sessionId,
    coderSessionIds: [...useStore.getState().coderSessionIds, sessionId],
    coderActivityIds: new Map(useStore.getState().coderActivityIds).set(
      sessionId,
      messageIds,
    ),
  });
}

function appendCoderActivity(message: Message) {
  const sessionId = getOngoingCoderSessionId();
  if (sessionId) {
    const coderActivityIds = useStore.getState().coderActivityIds;
    const current = coderActivityIds.get(sessionId);
    if (current && !current.includes(message.id)) {
      useStore.setState({
        coderActivityIds: new Map(coderActivityIds).set(sessionId, [
          ...current,
          message.id,
        ]),
      });
    }
  }
}

function appendDebateSession(sessionId: string) {
  const messageIds = [sessionId];
  useStore.setState({
    ongoingDebateSessionId: sessionId,
    debateSessionIds: [...useStore.getState().debateSessionIds, sessionId],
    debateActivityIds: new Map(useStore.getState().debateActivityIds).set(
      sessionId,
      messageIds,
    ),
  });
}

function appendDebateActivity(message: Message) {
  const sessionId = getOngoingDebateSessionId();
  if (sessionId) {
    const debateActivityIds = useStore.getState().debateActivityIds;
    const current = debateActivityIds.get(sessionId);
    if (current && !current.includes(message.id)) {
      const updated = [...current, message.id];
      useStore.setState({
        debateActivityIds: new Map(debateActivityIds).set(sessionId, updated),
      });
    }
  }
}

function appendResearch(researchId: string) {
  let planMessage: Message | undefined;
  let userQuery: string | undefined;
  const reversedMessageIds = [...useStore.getState().messageIds].reverse();
  for (const messageId of reversedMessageIds) {
    const message = getMessage(messageId);
    if (!planMessage && isPlannerAgent(message?.agent)) {
      planMessage = message;
    }
    if (!userQuery && message?.role === "user") {
      userQuery = message.content;
    }
    if (planMessage && userQuery) {
      break;
    }
  }
  const messageIds = [researchId];
  // Only add planMessage.id if it exists (direct coder calls have no plan message)
  if (planMessage?.id) {
    messageIds.unshift(planMessage.id);
  }
  useStore.setState({
    ongoingResearchId: researchId,
    researchIds: [...useStore.getState().researchIds, researchId],
    researchPlanIds: new Map(useStore.getState().researchPlanIds).set(
      researchId,
      planMessage?.id ?? "",
    ),
    researchActivityIds: new Map(useStore.getState().researchActivityIds).set(
      researchId,
      messageIds,
    ),
    researchQueries: new Map(useStore.getState().researchQueries).set(
      researchId,
      userQuery ?? "",
    ),
  });
}

function appendResearchActivity(message: Message) {
  const researchId = getOngoingResearchId();
  if (researchId) {
    const researchActivityIds = useStore.getState().researchActivityIds;
    const current = researchActivityIds.get(researchId)!;
    if (!current.includes(message.id)) {
      useStore.setState({
        researchActivityIds: new Map(researchActivityIds).set(researchId, [
          ...current,
          message.id,
        ]),
      });
    }
    if (message.agent === "reporter" || message.agent === "ai_compare_reporter") {
      useStore.setState({
        researchReportIds: new Map(useStore.getState().researchReportIds).set(
          researchId,
          message.id,
        ),
      });
    }
  }
}

export function openResearch(researchId: string | null) {
  useStore.getState().openResearch(researchId);
}

export function closeResearch() {
  useStore.getState().closeResearch();
}

export function openCoder(sessionId: string | null) {
  useStore.getState().openCoder(sessionId);
}

export function closeCoder() {
  useStore.getState().closeCoder();
}

export function openDebate(sessionId: string | null) {
  useStore.getState().openDebate(sessionId);
}

export function closeDebate() {
  useStore.getState().closeDebate();
}

export async function listenToPodcast(researchId: string) {
  const planMessageId = useStore.getState().researchPlanIds.get(researchId);
  const reportMessageId = useStore.getState().researchReportIds.get(researchId);
  if (planMessageId && reportMessageId) {
    const planMessage = getMessage(planMessageId)!;
    const title = parseJSON(planMessage.content, { title: "Untitled" }).title;
    const reportMessage = getMessage(reportMessageId);
    if (reportMessage?.content) {
      appendMessage({
        id: nanoid(),
        threadId: THREAD_ID,
        role: "user",
        content: getPodcastPromptTranslation(),
        contentChunks: [],
      });
      const podCastMessageId = nanoid();
      const podcastObject = { title, researchId };
      const podcastMessage: Message = {
        id: podCastMessageId,
        threadId: THREAD_ID,
        role: "assistant",
        agent: "podcast",
        content: JSON.stringify(podcastObject),
        contentChunks: [],
        reasoningContent: "",
        reasoningContentChunks: [],
        isStreaming: true,
      };
      appendMessage(podcastMessage);
      // Generating podcast...
      let audioUrl: string | undefined;
      try {
        audioUrl = await generatePodcast(reportMessage.content);
      } catch (e) {
        console.error(e);
        useStore.setState((state) => ({
          messages: new Map(useStore.getState().messages).set(
            podCastMessageId,
            {
              ...state.messages.get(podCastMessageId)!,
              content: JSON.stringify({
                ...podcastObject,
                error: e instanceof Error ? e.message : "Unknown error",
              }),
              isStreaming: false,
            },
          ),
        }));
        toast("An error occurred while generating podcast. Please try again.");
        return;
      }
      useStore.setState((state) => ({
        messages: new Map(useStore.getState().messages).set(podCastMessageId, {
          ...state.messages.get(podCastMessageId)!,
          content: JSON.stringify({ ...podcastObject, audioUrl }),
          isStreaming: false,
        }),
      }));
    }
  }
}

export function useResearchMessage(researchId: string) {
  return useStore(
    useShallow((state) => {
      const messageId = state.researchPlanIds.get(researchId);
      return messageId ? state.messages.get(messageId) : undefined;
    }),
  );
}

export function getResearchQuery(researchId: string): string {
  return useStore.getState().researchQueries.get(researchId) ?? "";
}

export function useMessage(messageId: string | null | undefined) {
  return useStore(
    useShallow((state) =>
      messageId ? state.messages.get(messageId) : undefined,
    ),
  );
}

export function useMessageIds() {
  return useStore(useShallow((state) => state.messageIds));
}

export function useRenderableMessageIds() {
  return useStore(
    useShallow((state) => {
      const seenPlannerContent = new Set<string>();
      const renderableIds: string[] = [];
      // Filter to only messages that will actually render in MessageListView
      // This prevents duplicate keys and React warnings when messages change state
      for (let i = state.messageIds.length - 1; i >= 0; i--) {
        const messageId = state.messageIds[i]!;
        const message = state.messages.get(messageId);
        if (!message) continue;

        // Only include messages that match MessageListItem rendering conditions
        // These are the same conditions checked in MessageListItem component
        const isPlanner = isPlannerAgent(message.agent);
        const isPodcast = message.agent === "podcast";
        const isStartOfResearch = state.researchIds.includes(messageId);
        const isStartOfCoderSession = state.coderSessionIds.includes(messageId);
        const isStartOfDebateSession = state.debateSessionIds.includes(messageId);

        // Planner, podcast, research cards, coder cards, and debate cards always render (they have their own content)
        let isRenderable = isPlanner || isPodcast || isStartOfResearch || isStartOfCoderSession || isStartOfDebateSession;

        // For user and coordinator messages, only include if they have content
        // This prevents empty dividers from appearing in the UI
        if (!isRenderable && (message.role === "user" || message.agent === "coordinator")) {
          isRenderable = !!message.content;
        }

        if (!isRenderable) {
          continue;
        }

        if (isPlanner) {
          const contentKey = (message.content ?? "").trim();
          if (contentKey) {
            if (seenPlannerContent.has(contentKey)) {
              continue;
            }
            seenPlannerContent.add(contentKey);
          }
        }

        renderableIds.push(messageId);
      }
      return renderableIds.reverse();
    }),
  );
}

export function useLastInterruptMessage() {
  return useStore(
    useShallow((state) => {
      for (let i = state.messageIds.length - 1; i >= 0; i--) {
        const message = state.messages.get(state.messageIds[i]!);
        if (message?.finishReason === "interrupt") {
          return message;
        }
      }
      return null;
    }),
  );
}

export function useLastFeedbackMessageId() {
  const waitingForFeedbackMessageId = useStore(
    useShallow((state) => {
      let interruptIndex = -1;
      for (let i = state.messageIds.length - 1; i >= 0; i--) {
        const message = state.messages.get(state.messageIds[i]!);
        if (message?.finishReason === "interrupt") {
          const isCodeTestInterrupt = (message.options || []).some(
            (option) => option.value === "[TEST]" || option.value === "[SKIP]",
          );
          if (isCodeTestInterrupt) {
            return null;
          }
          interruptIndex = i;
          break;
        }
      }
      if (interruptIndex <= 0) {
        return null;
      }
      for (let i = interruptIndex - 1; i >= 0; i--) {
        const message = state.messages.get(state.messageIds[i]!);
        if (isPlannerAgent(message?.agent)) {
          return state.messageIds[i]!;
        }
      }
      return null;
    }),
  );
  return waitingForFeedbackMessageId;
}

export function useToolCalls() {
  return useStore(
    useShallow((state) => {
      return state.messageIds
        ?.map((id) => getMessage(id)?.toolCalls)
        .filter((toolCalls) => toolCalls != null)
        .flat();
    }),
  );
}

export function useCitations(researchId: string | null | undefined) {
  return useStore(
    useShallow((state) =>
      researchId ? state.researchCitations.get(researchId) ?? [] : []
    ),
  );
}

export function getCitations(researchId: string): Citation[] {
  return useStore.getState().researchCitations.get(researchId) ?? [];
}
