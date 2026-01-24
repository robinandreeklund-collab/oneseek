"use client";

import React from "react";

import { ChatRequestOptions } from "ai";
import { useChat } from "ai/react";
import { toast } from "sonner";
import useLocalStorageState from "use-local-storage-state";
import { v4 as uuidv4 } from "uuid";

import { ChatLayout } from "@/components/chat/chat-layout";
import { ChatOptions } from "@/components/chat/chat-options";
import { basePath } from "@/lib/utils";
import { Source } from "@/components/chat/sources-sidebar";
import { MessageToolActions } from "@/types/tool-action";

interface ChatPageProps {
  chatId: string;
  setChatId: React.Dispatch<React.SetStateAction<string>>;
}

interface MessageSources {
  [messageId: string]: Source[];
}

export default function ChatPage({ chatId, setChatId }: ChatPageProps) {
  const [messageSources, setMessageSources] = React.useState<MessageSources>({});
  const [messageToolActions, setMessageToolActions] = React.useState<MessageToolActions>({});
  const processedDataRef = React.useRef<Set<string>>(new Set());
  const currentStreamingMessageIdRef = React.useRef<string | null>(null);
  const lastSeenMessageCountRef = React.useRef<number>(0);

  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    stop,
    setMessages,
    data,
  } = useChat({
    api: basePath + "/api/chat",
    streamMode: "stream-data",
    onError: (error) => {
      toast.error("Something went wrong: " + error);
    },
  });
  
  // Track the current streaming message - detect when a NEW assistant message appears
  React.useEffect(() => {
    const currentMessageCount = messages.length;
    
    // Check if a new message was added
    if (currentMessageCount > lastSeenMessageCountRef.current) {
      lastSeenMessageCountRef.current = currentMessageCount;
      
      // Get the latest assistant message
      const lastAssistantMessage = messages.filter(m => m.role === 'assistant').slice(-1)[0];
      
      // If there's a new assistant message and it's different from the tracked one
      if (lastAssistantMessage && currentStreamingMessageIdRef.current !== lastAssistantMessage.id) {
        console.log(`New assistant message detected: ${lastAssistantMessage.id}, clearing previous tracking`);
        
        // Update to track this new message
        currentStreamingMessageIdRef.current = lastAssistantMessage.id;
        
        // Initialize empty tool actions for this new message
        setMessageToolActions((prev) => {
          const newState = { ...prev };
          newState[lastAssistantMessage.id] = [];
          return newState;
        });
      }
    }
    
    // DO NOT clear tracking when loading stops - keep the reference so final tool actions go to the right message
    // The reference will be updated when the next new message starts
  }, [messages]);
  
  // Watch for data changes and extract sources and tool actions
  React.useEffect(() => {
    if (data && Array.isArray(data) && data.length > 0) {
      // Get the most recent assistant message
      const lastAssistantMessage = messages.filter(m => m.role === 'assistant').slice(-1)[0];
      if (!lastAssistantMessage) {
        return;
      }
      
      // Create a unique key for this data + message combination
      const dataKey = `${lastAssistantMessage.id}-${JSON.stringify(data)}`;
      
      // Skip if we've already processed this data for this message
      if (processedDataRef.current.has(dataKey)) {
        return;
      }
      
      // Process all data items to find sources and tool actions
      for (const item of data) {
        // Type guard to ensure item is an object with the expected properties
        if (!item || typeof item !== 'object' || Array.isArray(item)) {
          continue;
        }
        
        // Extract sources
        if ('retrieved' in item && Array.isArray(item.retrieved) && item.retrieved.length > 0) {
          const retrieved = item.retrieved as any[];
          setMessageSources((prev) => {
            // Only set if not already set for this message
            if (!prev[lastAssistantMessage.id]) {
              processedDataRef.current.add(dataKey);
              return {
                ...prev,
                [lastAssistantMessage.id]: retrieved.map((source: any) => ({
                  title: source.title || "Untitled",
                  content: source.content || "",
                  url: source.url,
                  relevance: source.relevance,
                  source: source.source,
                })),
              };
            }
            return prev;
          });
        }
        
        // Extract tool actions - only update for the current message being streamed
        if ('tool_actions' in item && Array.isArray(item.tool_actions) && item.tool_actions.length > 0) {
          const toolActions = item.tool_actions as any[];
          const isLiveUpdate = item.live_update === true;
          
          setMessageToolActions((prev) => {
            // Determine target message ID - prefer the tracked streaming message
            const targetMessageId = currentStreamingMessageIdRef.current;
            
            // If no target message is being tracked, skip (shouldn't happen during streaming)
            if (!targetMessageId) {
              console.warn('Tool actions received but no streaming message tracked');
              return prev;
            }
            
            // ALWAYS replace tool actions for the target message (never merge with old data)
            // This ensures each question gets its OWN tool actions and old data doesn't persist
            const newState = { ...prev };
            newState[targetMessageId] = toolActions;
            console.log(`Updated tool actions for message ${targetMessageId}:`, toolActions.length, 'actions', isLiveUpdate ? '(live)' : '(final)');
            return newState;
          });
        }
      }
    }
  }, [data, messages]);
  const [chatOptions, setChatOptions] = useLocalStorageState<ChatOptions>(
    "chatOptions",
    {
      defaultValue: {
        selectedModel: "",
        systemPrompt: "",
        temperature: 0.9,
      },
    }
  );

  React.useEffect(() => {
    if (chatId) {
      const item = localStorage.getItem(`chat_${chatId}`);
      if (item) {
        setMessages(JSON.parse(item));
      }
    } else {
      setMessages([]);
    }
  }, [setMessages, chatId]);

  React.useEffect(() => {
    if (!isLoading && !error && chatId && messages.length > 0) {
      // Save messages to local storage
      localStorage.setItem(`chat_${chatId}`, JSON.stringify(messages));
      // Trigger the storage event to update the sidebar component
      window.dispatchEvent(new Event("storage"));
    }
  }, [messages, chatId, isLoading, error]);

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (messages.length === 0) {
      // Generate a random id for the chat
      const id = uuidv4();
      setChatId(id);
    }

    setMessages([...messages]);

    // Prepare the options object with additional body data, to pass the model.
    const requestOptions: ChatRequestOptions = {
      options: {
        body: {
          chatOptions: chatOptions,
        },
      },
    };

    // Call the handleSubmit function with the options
    handleSubmit(e, requestOptions);
  };

  return (
    <main className="flex h-[calc(100dvh)] flex-col items-center ">
      <ChatLayout
        chatId={chatId}
        setChatId={setChatId}
        chatOptions={chatOptions}
        setChatOptions={setChatOptions}
        messages={messages}
        input={input}
        handleInputChange={handleInputChange}
        handleSubmit={onSubmit}
        isLoading={isLoading}
        error={error}
        stop={stop}
        navCollapsedSize={10}
        defaultLayout={[30, 160]}
        messageSources={messageSources}
        messageToolActions={messageToolActions}
      />
    </main>
  );
}
