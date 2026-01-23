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

interface ChatPageProps {
  chatId: string;
  setChatId: React.Dispatch<React.SetStateAction<string>>;
}

interface MessageSources {
  [messageId: string]: Source[];
}

export default function ChatPage({ chatId, setChatId }: ChatPageProps) {
  const [messageSources, setMessageSources] = React.useState<MessageSources>({});

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
    onFinish: (message, { data }) => {
      // Extract source metadata from stream data
      if (data && Array.isArray(data)) {
        for (const item of data) {
          if (item.retrieved && Array.isArray(item.retrieved)) {
            setMessageSources((prev) => ({
              ...prev,
              [message.id]: item.retrieved.map((source: any) => ({
                title: source.title || "Untitled",
                content: source.content || "",
                url: source.url,
                relevance: source.relevance,
                source: source.source,
              })),
            }));
            break;
          }
        }
      }
    },
  });
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
      />
    </main>
  );
}
