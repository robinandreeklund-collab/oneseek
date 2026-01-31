// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Settings } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Lightbulb } from "lucide-react";

import { AiCompare } from "~/components/deer-flow/icons/ai-compare";
import { DebateIcon } from "~/components/deer-flow/icons/debate";
import { Detective } from "~/components/deer-flow/icons/detective";
import { Button } from "~/components/ui/button";
import {
  setEnableDeepThinking,
  setEnableBackgroundInvestigation,
  setEnableAiComparison,
  setEnableDebateMode,
  useSettingsStore,
} from "~/core/store";
import { cn } from "~/lib/utils";

export function ModesDropUp() {
  const t = useTranslations("chat.inputBox");
  const [isOpen, setIsOpen] = useState(false);
  const enableDeepThinking = useSettingsStore(
    (state) => state.general.enableDeepThinking,
  );
  const backgroundInvestigation = useSettingsStore(
    (state) => state.general.enableBackgroundInvestigation,
  );
  const aiComparison = useSettingsStore(
    (state) => state.general.enableAiComparison,
  );
  const debateMode = useSettingsStore(
    (state) => state.general.enableDebateMode,
  );

  const modes = [
    {
      icon: <Lightbulb className="h-4 w-4" />,
      label: t("deepThinking"),
      enabled: enableDeepThinking,
      toggle: () => setEnableDeepThinking(!enableDeepThinking),
      tooltip: t("deepThinkingTooltip.description", { model: "" }),
    },
    {
      icon: <Detective className="h-4 w-4" />,
      label: t("investigation"),
      enabled: backgroundInvestigation,
      toggle: () => setEnableBackgroundInvestigation(!backgroundInvestigation),
      tooltip: t("investigationTooltip.description"),
    },
    {
      icon: <AiCompare className="h-4 w-4" />,
      label: t("aiComparison"),
      enabled: aiComparison,
      toggle: () => setEnableAiComparison(!aiComparison),
      tooltip: t("aiComparisonTooltip.description"),
    },
    {
      icon: <DebateIcon className="h-4 w-4" />,
      label: t("debateMode"),
      enabled: debateMode,
      toggle: () => setEnableDebateMode(!debateMode),
      tooltip: t("debateModeTooltip.description"),
    },
  ];

  const activeModesCount = modes.filter((mode) => mode.enabled).length;

  return (
    <div className="relative">
      <Button
        variant="outline"
        size="sm"
        className={cn(
          "h-8 gap-1.5 rounded-xl text-xs",
          activeModesCount > 0 && "!border-brand !text-brand",
        )}
        onClick={() => setIsOpen(!isOpen)}
      >
        <Settings className="h-3.5 w-3.5" />
        {t("modes")} {activeModesCount > 0 && `(${activeModesCount})`}
      </Button>

      {isOpen && (
        <>
          {/* Backdrop to close dropdown */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          
          {/* Drop-up menu */}
          <div className="bg-card absolute bottom-full left-0 z-20 mb-2 min-w-[200px] rounded-lg border shadow-lg">
            <div className="p-1">
              {modes.map((mode, index) => (
                <button
                  key={index}
                  className={cn(
                    "text-foreground hover:bg-accent flex w-full items-center gap-2 rounded-md px-3 py-2.5 text-left text-sm transition-colors",
                    mode.enabled && "bg-brand/10 text-brand",
                  )}
                  onClick={() => {
                    mode.toggle();
                  }}
                >
                  {mode.icon}
                  <span className="flex-1">{mode.label}</span>
                  {mode.enabled && (
                    <div className="bg-brand h-2 w-2 rounded-full" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
