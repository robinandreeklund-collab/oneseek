// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

export type MessageRole = "user" | "assistant" | "tool";

export type PlannerAgentName = "planner" | `${string}_planner`;
export type AgentName =
  | "coordinator"
  | "researcher"
  | "coder"
  | "code_researcher"
  | "code_reviewer"
  | "code_refiner"
  | "reporter"
  | "podcast"
  | "analyst"
  | "ai_comparison"
  | "debate_orchestrator"
  | "external_ai_caller"
  | "fact_checker"
  | "synthesizer"
  | "moderator"
  | PlannerAgentName;

export function isPlannerAgent(agent?: string): agent is PlannerAgentName {
  return agent === "planner" || (typeof agent === "string" && agent.endsWith("_planner"));
}

export interface Message {
  id: string;
  threadId: string;
  agent?: AgentName;
  role: MessageRole;
  isStreaming?: boolean;
  content: string;
  contentChunks: string[];
  reasoningContent?: string;
  reasoningContentChunks?: string[];
  toolCalls?: ToolCallRuntime[];
  options?: Option[];
  finishReason?: "stop" | "interrupt" | "tool_calls";
  interruptFeedback?: string;
  resources?: Array<Resource>;
  citations?: Array<Citation>;
}

export interface Option {
  text: string;
  value: string;
}

export interface ToolCallRuntime {
  id: string;
  name: string;
  args: Record<string, unknown>;
  argsChunks?: string[];
  result?: string;
  status?: string;
}

export interface ToolAction {
  tool_call_id: string;
  tool_name?: string;
  display_name?: string;
  icon?: string;
  color?: string;
  input?: unknown;
  tool_input?: unknown;
  output?: unknown;
  tool_output?: unknown;
  raw_request?: Record<string, unknown>;
  raw_response?: Record<string, unknown>;
  status?: string;
  start_time?: number;
  end_time?: number;
  duration?: number;
  workspace_files?: WorkspaceFile[];
}

export interface WorkspaceFile {
  path: string;
  name?: string;
  size?: number;
  operation?: string;
  modified?: string;
  content?: string;
  truncated?: boolean;
}

export interface Resource {
  uri: string;
  title: string;
  description?: string;
}

export interface Citation {
  url: string;
  title: string;
  description?: string;
  content_snippet?: string;
  domain?: string;
  relevance_score?: number;
  accessed_at?: string;
  source_type?: string;
}
