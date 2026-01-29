import React from "react";

import { ChatRequestOptions } from "ai";
import { Message } from "ai/react";

import ChatBottombar from "./chat-bottombar";
import ChatList from "./chat-list";
import { ChatOptions } from "./chat-options";
import ChatTopbar from "./chat-topbar";
import { Source } from "./sources-sidebar";
import { MessageToolActions } from "@/types/tool-action";
import Image from "next/image";

export interface ChatProps {
  chatId?: string;
  setChatId: React.Dispatch<React.SetStateAction<string>>;
  messages: Message[];
  input: string;
  handleInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  handleSubmit: (
    e: React.FormEvent<HTMLFormElement>,
    chatRequestOptions?: ChatRequestOptions
  ) => void;
  isLoading: boolean;
  error: undefined | Error;
  stop: () => void;
  messageSources?: { [messageId: string]: Source[] };
  messageToolActions?: MessageToolActions;
}

export interface ChatTopbarProps {
  chatOptions: ChatOptions;
  setChatOptions: React.Dispatch<React.SetStateAction<ChatOptions>>;
}

export default function Chat({
  messages,
  input,
  handleInputChange,
  handleSubmit,
  isLoading,
  error,
  stop,
  chatOptions,
  setChatOptions,
  chatId,
  setChatId,
  messageSources,
  messageToolActions,
}: ChatProps & ChatTopbarProps) {
  const isEmpty = messages.length === 0;
  const heroPills = ["DeepSearch", "Skapa bild", "Senaste nytt", "Röstanalys"];

  if (isEmpty) {
    return (
      <div className="flex flex-col h-full w-full items-center justify-center gap-8 px-6">
        <div className="flex flex-col items-center gap-4">
          <Image
            src="/oneseek-logo.svg"
            alt="OneSeek"
            width={120}
            height={120}
            className="h-24 w-24 object-contain"
            priority
          />
          <p className="text-center text-lg text-muted-foreground">
            Vad vill du att OneSeek ska veta?
          </p>
        </div>
        <div className="w-full max-w-3xl flex flex-col items-center gap-4">
          <ChatBottombar
            selectedModel={chatOptions.selectedModel}
            input={input}
            handleInputChange={handleInputChange}
            handleSubmit={handleSubmit}
            isLoading={isLoading}
            stop={stop}
            variant="center"
          />
          <div className="flex flex-wrap justify-center gap-2 text-sm text-muted-foreground">
            {heroPills.map((pill) => (
              <button
                key={pill}
                type="button"
                onClick={() => {
                  if (!input?.trim()) {
                    handleInputChange({
                      target: { value: pill },
                    } as unknown as React.ChangeEvent<HTMLTextAreaElement>);
                  }
                }}
                className="rounded-full border border-border/60 px-3 py-1 bg-card/40 hover:bg-card cursor-pointer transition-colors"
              >
                {pill}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col justify-between w-full h-full  ">
      <ChatTopbar
        chatOptions={chatOptions}
        setChatOptions={setChatOptions}
        isLoading={isLoading}
        chatId={chatId}
        setChatId={setChatId}
        messages={messages}
      />

      <ChatList
        messages={messages}
        isLoading={isLoading}
        messageSources={messageSources}
        messageToolActions={messageToolActions}
      />

      <ChatBottombar
        selectedModel={chatOptions.selectedModel}
        input={input}
        handleInputChange={handleInputChange}
        handleSubmit={handleSubmit}
        isLoading={isLoading}
        stop={stop}
      />
    </div>
  );
}
