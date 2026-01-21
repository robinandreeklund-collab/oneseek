"use client";

import { useState, useEffect, useRef } from "react";
import { Send, Loader2 } from "lucide-react";
import { TransparensAccordion } from "./TransparensAccordion";
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
  retrieved?: Array<{
    title: string;
    content: string;
    relevance?: number;
  }>;
  steps?: string[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001";

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Load chat history from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("oneseek-chat-history");
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to load chat history:", e);
      }
    }
  }, []);

  // Save chat history to localStorage
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem("oneseek-chat-history", JSON.stringify(messages));
    }
  }, [messages]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Create placeholder for assistant message
    const assistantIndex = messages.length + 1;
    let assistantMessage: Message = {
      role: "assistant",
      content: "",
      retrieved: [],
      steps: [],
    };

    setMessages((prev) => [...prev, assistantMessage]);

    try {
      // Prepare messages for API (exclude metadata)
      const apiMessages = [...messages, userMessage].map(({ role, content }) => ({
        role,
        content,
      }));

      // Create AbortController for cancellation
      abortControllerRef.current = new AbortController();

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: apiMessages,
          stream: true,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      // Handle streaming response
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("No response body");
      }

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === "step") {
                // Update steps
                assistantMessage = {
                  ...assistantMessage,
                  steps: [...(assistantMessage.steps || []), data.content],
                };
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[assistantIndex] = assistantMessage;
                  return newMessages;
                });
              } else if (data.type === "retrieved") {
                // Update retrieved documents
                assistantMessage = {
                  ...assistantMessage,
                  retrieved: data.content,
                };
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[assistantIndex] = assistantMessage;
                  return newMessages;
                });
              } else if (data.type === "token") {
                // Append token to content
                assistantMessage = {
                  ...assistantMessage,
                  content: assistantMessage.content + data.content,
                };
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[assistantIndex] = assistantMessage;
                  return newMessages;
                });
              } else if (data.type === "done") {
                // Final update with complete data
                assistantMessage = {
                  role: "assistant",
                  content: data.content,
                  retrieved: data.retrieved || [],
                  steps: data.steps || [],
                };
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[assistantIndex] = assistantMessage;
                  return newMessages;
                });
              } else if (data.type === "error") {
                throw new Error(data.content);
              }
            } catch (parseError) {
              console.error("Failed to parse SSE data:", parseError);
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        console.log("Request cancelled");
        return;
      }

      console.error("Chat error:", error);

      const errorMessage: Message = {
        role: "assistant",
        content: `Fel vid anrop till backend: ${error instanceof Error ? error.message : "Okänt fel"}. Kontrollera att FastAPI-servern körs på ${API_BASE_URL}`,
      };

      setMessages((prev) => {
        const newMessages = [...prev];
        newMessages[assistantIndex] = errorMessage;
        return newMessages;
      });
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const clearHistory = () => {
    setMessages([]);
    localStorage.removeItem("oneseek-chat-history");
  };

  const cancelRequest = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground py-12">
            <h2 className="text-2xl font-semibold mb-2">Välkommen till OneSeek.ai</h2>
            <p className="text-sm">
              Ställ en fråga för att börja. Svar berikas med RAG via Vespa Cloud.
            </p>
            <p className="text-xs mt-4">
              Exempel: &quot;Vad är riskerna med AI enligt experter?&quot;
            </p>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={cn(
              "flex w-full",
              message.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            <div
              className={cn(
                "max-w-[85%] rounded-lg px-4 py-3",
                message.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted"
              )}
            >
              <div className="text-sm whitespace-pre-wrap">
                {message.content}
                {isLoading && index === messages.length - 1 && message.role === "assistant" && !message.content && (
                  <span className="inline-block animate-pulse">▊</span>
                )}
              </div>

              {/* Show transparency accordion for assistant messages with metadata */}
              {message.role === "assistant" && (message.retrieved || message.steps) && (
                <TransparensAccordion
                  retrieved={message.retrieved || []}
                  steps={message.steps || []}
                />
              )}
            </div>
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-border bg-card p-4">
        <div className="max-w-4xl mx-auto space-y-2">
          {messages.length > 0 && (
            <div className="flex justify-end gap-2">
              {isLoading && (
                <button
                  onClick={cancelRequest}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Avbryt
                </button>
              )}
              <button
                onClick={clearHistory}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Rensa historik
              </button>
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Skriv ditt meddelande..."
              disabled={isLoading}
              className="flex-1 rounded-md border border-input bg-background px-4 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
