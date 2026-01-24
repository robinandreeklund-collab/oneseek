import React, { useEffect, useRef, useState } from "react";
import { ToolAction } from "@/types/tool-action";

interface ActionBlockProps {
  actions: ToolAction[];
  live?: boolean;
  onToolClick?: (action: ToolAction) => void;
}

export default function ActionBlock({ actions, live = false, onToolClick }: ActionBlockProps) {
  // Collapsible state
  const [open, setOpen] = useState(live ? true : false);

  // Always open in live mode, collapsible in non-live mode
  const isOpen = live ? true : open;

  // Get color classes based on color name (for left border accent)
  const getColorClasses = (color: string) => {
    const colorMap: Record<string, { borderLeft: string; text: string }> = {
      blue: {
        borderLeft: "border-l-blue-500",
        text: "text-blue-500",
      },
      green: {
        borderLeft: "border-l-green-500",
        text: "text-green-500",
      },
      purple: {
        borderLeft: "border-l-purple-500",
        text: "text-purple-500",
      },
      gray: {
        borderLeft: "border-l-gray-500",
        text: "text-gray-500",
      },
    };
    return colorMap[color] || colorMap.gray;
  };

  if (!actions || actions.length === 0) {
    return null;
  }

  return (
    <div className="my-3 rounded-md border border-border/40 bg-background/30">
      {/* Header */}
      <div className="flex items-center px-3 py-2 cursor-pointer select-none" onClick={() => !live && setOpen((o) => !o)}>
        {/* Chevron */}
        <span
          className={`mr-2 inline-block transition-transform duration-200 ${
            isOpen ? "rotate-0" : "-rotate-90"
          }`}
          style={{ width: 16, height: 16 }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M5 6l3 3 3-3"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-muted-foreground"
            />
          </svg>
        </span>
        {/* Label */}
        <span className="text-sm text-muted-foreground">
          Actions <span className="ml-1">{actions.length} tool(s) {live ? "invoked" : "used"}</span>
        </span>
      </div>
      
      {/* Tool cards */}
      {isOpen && (
        <div className="px-3 pb-3 space-y-2">
          {actions.map((action, idx) => {
            const colors = getColorClasses(action.color);
            const isRunning = action.status === "running";
            const duration = action.duration
              ? `${action.duration.toFixed(2)}s`
              : null;

            return (
              <div
                key={action.tool_call_id || idx}
                className={`rounded-md border border-border/60 bg-card/50 ${colors.borderLeft} border-l-4 p-3 cursor-pointer hover:bg-card/80 transition-colors`}
                onClick={() => onToolClick && onToolClick(action)}
              >
                <div className="flex items-start gap-2.5">
                  {/* Icon */}
                  <span className="text-xl flex-shrink-0">{action.icon}</span>

                  <div className="flex-1 min-w-0">
                    {/* Tool name and duration/status */}
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className={`font-medium text-sm ${colors.text}`}>
                        {action.display_name}
                      </span>
                      {isRunning ? (
                        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                          <span className="w-2.5 h-2.5 border-2 border-current border-t-transparent rounded-full inline-block animate-spin"></span>
                          <span className="italic">Running...</span>
                        </span>
                      ) : duration ? (
                        <span className="text-xs text-muted-foreground">
                          {duration}
                        </span>
                      ) : null}
                    </div>

                    {/* Input parameters */}
                    {action.input && Object.keys(action.input).length > 0 && (
                      <div className="text-xs text-muted-foreground/80 mb-1">
                        <span className="opacity-70">Input: </span>
                        <span className="font-mono text-muted-foreground">
                          {Object.entries(action.input)
                            .map(([key, value]) => {
                              const formattedValue = typeof value === "object" 
                                ? JSON.stringify(value) 
                                : String(value);
                              // Truncate long values
                              const displayValue = formattedValue.length > 50 
                                ? formattedValue.substring(0, 50) + "..." 
                                : formattedValue;
                              return `${key}="${displayValue}"`;
                            })
                            .join(", ")}
                        </span>
                      </div>
                    )}

                    {/* Output summary (only when completed) */}
                    {!isRunning && action.output && (
                      <div className="text-xs text-muted-foreground/80">
                        <span className="opacity-70">Output: </span>
                        <span className="text-muted-foreground">
                          {Array.isArray(action.output) ? (
                            `${action.output.length} result${action.output.length !== 1 ? "s" : ""}`
                          ) : typeof action.output === "object" ? (
                            "1 result"
                          ) : (
                            <span className="font-mono">
                              {String(action.output).substring(0, 60)}
                              {String(action.output).length > 60 ? "..." : ""}
                            </span>
                          )}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
