/**
 * Shared type definitions for ActionBlock and tool invocation tracking
 */

export interface ToolAction {
  tool_call_id: string;  // Unique identifier for this specific invocation
  tool_name: string;
  display_name: string;
  icon: string;
  color: string;
  input: any;
  output?: any;
  raw_request?: {  // Complete raw request details
    tool: string;
    arguments: any;
    call_id: string;
  };
  raw_response?: {  // Complete raw response details
    content: string;
    tool_call_id?: string;
    parsed?: any;
    error?: string;
  };
  reasoning?: string;  // Model's reasoning before calling the tool
  iteration?: number;  // Which iteration in the agent loop
  start_time?: number;
  end_time?: number;
  duration?: number;
  status: "running" | "completed";
}

export interface MessageToolActions {
  [messageId: string]: ToolAction[];
}
