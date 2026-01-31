// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, useCallback } from "react";

import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";

export function HeroInput() {
  const t = useTranslations("messageInput");
  const router = useRouter();
  const [message, setMessage] = useState("");

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (message.trim()) {
        // Navigate to chat page with the message as a query parameter
        router.push(`/chat?q=${encodeURIComponent(message.trim())}`);
      }
    },
    [message, router]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (message.trim()) {
          router.push(`/chat?q=${encodeURIComponent(message.trim())}`);
        }
      }
    },
    [message, router]
  );

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div className="relative flex items-center">
        <Input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t("placeholder")}
          className="h-14 pr-14 text-base shadow-lg backdrop-blur-sm"
        />
        <Button
          type="submit"
          size="icon"
          className="absolute right-2 h-10 w-10"
          disabled={!message.trim()}
        >
          <ArrowRight className="h-5 w-5" />
        </Button>
      </div>
    </form>
  );
}
