import React, { useMemo, useState } from "react";

import { cn } from "~/lib/utils";

type ModelIconProps = {
  modelKey?: string;
  className?: string;
  size?: number;
};

const MODEL_ICON_SOURCES: Record<string, string[]> = {
  "gpt-3.5-turbo": [
    "/images/ai-logos/openai.png",
    "/images/ai-logos/openai.svg",
    "/images/ai-logos/openai.svg.svg",
    "/openai.png",
  ],
  "gemini-2.5-flash": [
    "/images/ai-logos/gemini.png",
    "/images/ai-logos/gemini.svg.png",
    "/images/ai-logos/gemini.svg",
    "/gemini.png",
  ],
  "deepseek-chat": [
    "/images/ai-logos/deepseek.png",
    "/images/ai-logos/deepseek.svg.png",
    "/images/ai-logos/deepseek.svg",
    "/deepseek.png",
  ],
  "grok-4-fast-reasoning": [
    "/images/ai-logos/grok.png",
    "/images/ai-logos/grok.svg.png",
    "/images/ai-logos/grok.svg",
    "/grok.png",
  ],
};

const MODEL_STYLES: Record<string, { label: string; color: string }> = {
  "gpt-3.5-turbo": { label: "GPT", color: "bg-emerald-500/15 text-emerald-500 border-emerald-500/40" },
  "gemini-2.5-flash": { label: "Gem", color: "bg-blue-500/15 text-blue-500 border-blue-500/40" },
  "deepseek-chat": { label: "DS", color: "bg-indigo-500/15 text-indigo-500 border-indigo-500/40" },
  "grok-4-fast-reasoning": { label: "Grok", color: "bg-fuchsia-500/15 text-fuchsia-500 border-fuchsia-500/40" },
  "oneseek-local": { label: "OS", color: "bg-amber-500/15 text-amber-500 border-amber-500/40" },
};

export function DebateModelIcon({ modelKey, className, size = 20 }: ModelIconProps) {
  if (modelKey === "oneseek-local") {
    return (
      <span
        className={cn(
          "inline-flex items-center justify-center rounded-full border border-border bg-white/90",
          className,
        )}
        style={{ width: size, height: size }}
      >
        <img
          src="/oneseek-logo.svg"
          alt="OneSeek"
          width={size - 6}
          height={size - 6}
          className="h-auto w-auto object-contain"
        />
      </span>
    );
  }

  const sources = useMemo(
    () => (modelKey ? MODEL_ICON_SOURCES[modelKey] ?? [] : []),
    [modelKey],
  );
  const [sourceIndex, setSourceIndex] = useState(0);
  const [showFallback, setShowFallback] = useState(false);
  const iconSrc = sources[sourceIndex];
  if (iconSrc && !showFallback) {
    return (
      <span
        className={cn(
          "inline-flex items-center justify-center rounded-full border border-border bg-white/90",
          className,
        )}
        style={{ width: size, height: size }}
      >
        <img
          src={iconSrc}
          alt={modelKey}
          width={size - 4}
          height={size - 4}
          className="h-auto w-auto object-contain"
          onError={() => {
            if (sourceIndex < sources.length - 1) {
              setSourceIndex(sourceIndex + 1);
            } else {
              setShowFallback(true);
            }
          }}
        />
      </span>
    );
  }

  const style = modelKey ? MODEL_STYLES[modelKey] : undefined;
  const label = style?.label ?? "AI";
  const color = style?.color ?? "bg-slate-500/15 text-slate-500 border-slate-500/40";

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full border text-[10px] font-semibold uppercase",
        color,
        className,
      )}
      style={{ width: size, height: size }}
      aria-label={modelKey}
      title={modelKey}
    >
      {label}
    </span>
  );
}
