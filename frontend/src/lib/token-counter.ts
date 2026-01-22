import llama3Tokenizer from "llama3-tokenizer-js";

export function getTokenLimit(model: string): number {
  const limits: Record<string, number> = {
    "llama3:latest": 8192,
    "llama3:8b": 8192,
    "llama3:70b": 8192,
    "qwen:7b": 32768,
    "qwen:14b": 32768,
    "qwen:32b": 32768,
    "qwen:72b": 32768,
    "qwen2:0.5b": 32768,
    "qwen2:1.5b": 32768,
    "qwen2:7b": 131072,
    "qwen2:72b": 131072,
    "qwen2.5:0.5b": 32768,
    "qwen2.5:1.5b": 32768,
    "qwen2.5:3b": 32768,
    "qwen2.5:7b": 131072,
    "qwen2.5:14b": 131072,
    "qwen2.5:32b": 131072,
    "qwen2.5:72b": 131072,
  };

  return limits[model] || 4096; // Default to 4096 if model not found
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
