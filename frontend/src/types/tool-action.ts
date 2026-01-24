/**
 * Shared type definitions for ActionBlock and tool invocation tracking
 */

export interface ToolAction {
  tool_name: string;
  display_name: string;
  icon: string;
  color: string;
  input: any;
  output?: any;
  start_time?: number;
  end_time?: number;
  duration?: number;
  status: "running" | "completed";
}

export interface MessageToolActions {
  [messageId: string]: ToolAction[];
}
