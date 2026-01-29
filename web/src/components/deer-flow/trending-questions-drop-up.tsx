// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { TrendingUp } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "~/components/ui/button";
import { cn } from "~/lib/utils";

export function TrendingQuestionsDropUp({
  onSelectQuestion,
}: {
  onSelectQuestion?: (question: string) => void;
}) {
  const t = useTranslations("chat");
  const [isOpen, setIsOpen] = useState(false);
  
  const questions = t.raw("conversationStarters") as string[];

  const handleSelectQuestion = (question: string) => {
    onSelectQuestion?.(question);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <Button
        variant="outline"
        size="sm"
        className="h-8 gap-1.5 rounded-xl text-xs"
        onClick={() => setIsOpen(!isOpen)}
      >
        <TrendingUp className="h-3.5 w-3.5" />
        Trendande frågor
      </Button>

      {isOpen && (
        <>
          {/* Backdrop to close dropdown */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          
          {/* Drop-up menu */}
          <div className="bg-card absolute bottom-full left-0 z-20 mb-2 w-[320px] rounded-lg border shadow-lg">
            <div className="p-1">
              {questions.map((question, index) => (
                <button
                  key={index}
                  className="text-foreground hover:bg-accent flex w-full items-start gap-2 rounded-md px-3 py-2.5 text-left text-sm transition-colors"
                  onClick={() => handleSelectQuestion(question)}
                >
                  <span className="text-muted-foreground mt-0.5 shrink-0 text-xs">
                    {index + 1}.
                  </span>
                  <span className="flex-1">{question}</span>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
