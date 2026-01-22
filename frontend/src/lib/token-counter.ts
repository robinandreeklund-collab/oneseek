import llama3Tokenizer from "llama3-tokenizer-js";
import { Message } from "ai/react";

export async function getTokenLimit(basePath: string): Promise<number> {
  try {
    // For OneSeek.ai, we use a default token limit since we're using FastAPI backend
    // The backend handles the actual model communication with vLLM
    return 8192; // Default llama3 token limit
  } catch (error) {
    console.error("Error getting token limit:", error);
    return 4096; // Fallback to conservative limit
  }
}

export function countTokens(text: string): number {
  try {
    const tokens = llama3Tokenizer.encode(text);
    return tokens.length;
  } catch (error) {
    // Fallback: approximate token count (1 token ≈ 4 characters)
    return Math.ceil(text.length / 4);
  }
}

export function encodeChat(messages: Message[]): number {
  // Estimate tokens for the entire chat history
  let totalTokens = 0;
  
  for (const message of messages) {
    // Add tokens for role (system/user/assistant)
    totalTokens += countTokens(message.role);
    // Add tokens for content
    totalTokens += countTokens(message.content);
    // Add overhead for message formatting (approximately 4 tokens per message)
    totalTokens += 4;
  }
  
  return totalTokens;
}
