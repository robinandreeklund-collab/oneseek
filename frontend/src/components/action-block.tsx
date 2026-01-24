import React, { useEffect, useRef, useState } from "react";
import { ToolAction } from "@/types/tool-action";

interface ActionBlockProps {
  actions: ToolAction[];
  live?: boolean;
}

export default function ActionBlock({ actions, live = false }: ActionBlockProps) {
  // Collapsible state
  const [open, setOpen] = useState(live ? true : false);

  // Always open in live mode, collapsible in non-live mode
  const isOpen = live ? true : open;

  // Get color classes based on color name
  const getColorClasses = (color: string) => {
    const colorMap: Record<string, { border: string; text: string; bg: string }> = {
      blue: {
        border: "border-blue-400",
        text: "text-blue-400",
        bg: "bg-blue-400/10",
      },
      green: {
        border: "border-green-400",
        text: "text-green-400",
        bg: "bg-green-400/10",
      },
      purple: {
        border: "border-purple-400",
        text: "text-purple-400",
        bg: "bg-purple-400/10",
      },
      gray: {
        border: "border-gray-400",
        text: "text-gray-400",
        bg: "bg-gray-400/10",
      },
    };
    return colorMap[color] || colorMap.gray;
  };

  if (!actions || actions.length === 0) {
    return null;
  }

  return (
    <div className="my-4 rounded-xl border border-dashed border-gray-400 bg-background/50">
      <div className="flex items-center px-4 pt-2 pb-1 select-none">
        {/* Chevron (button for collapsible, static for live) */}
        {live ? (
          <span
            className="mr-2 inline-block transition-transform rotate-0"
            style={{ width: 20, height: 20 }}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M7 8l3 3 3-3"
                stroke="#9ca3af"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
        ) : (
          <button
            className="mr-2 flex items-center justify-center focus:outline-none transition-transform"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            style={{ height: 24, width: 24 }}
          >
            <span
              className={`inline-block transition-transform duration-200 ${
                open ? "rotate-0" : "-rotate-90"
              }`}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: 20,
                width: 20,
              }}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M7 8l3 3 3-3"
                  stroke="#9ca3af"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
          </button>
        )}
        {/* Label */}
        <span className="text-gray-400 font-medium text-sm mr-3">Actions</span>
        {/* Header */}
        <span className="italic text-sm text-muted-foreground">
          {live ? `${actions.length} tool(s) invoked` : `${actions.length} tool(s) used`}
        </span>
      </div>
      {isOpen && (
        <div className="px-6 pb-4 pt-1">
          {actions.map((action, idx) => {
            const colors = getColorClasses(action.color);
            const isRunning = action.status === "running";
            const duration = action.duration
              ? `${action.duration.toFixed(2)}s`
              : null;

            return (
              <div
                key={idx}
                className={`mb-3 last:mb-0 rounded-lg border ${colors.border} ${colors.bg} p-3`}
              >
                <div className="flex items-start gap-3">
                  {/* Icon */}
                  <span className="text-2xl">{action.icon}</span>

                  <div className="flex-1 min-w-0">
                    {/* Tool name and status */}
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`font-semibold text-sm ${colors.text}`}>
                        {action.display_name}
                      </span>
                      {isRunning && (
                        <span className="inline-flex items-center gap-1">
                          <span className="w-3 h-3 border-2 border-current border-t-transparent rounded-full inline-block animate-spin"></span>
                          <span className="text-xs text-muted-foreground italic">
                            Running...
                          </span>
                        </span>
                      )}
                      {!isRunning && duration && (
                        <span className="text-xs text-muted-foreground">
                          {duration}
                        </span>
                      )}
                    </div>

                    {/* Input parameters */}
                    {action.input && Object.keys(action.input).length > 0 && (
                      <div className="text-xs text-muted-foreground mb-2">
                        <span className="font-medium">Input: </span>
                        <span className="font-mono">
                          {Object.entries(action.input)
                            .map(([key, value]) => {
                              // Handle complex values properly
                              const formattedValue = typeof value === "object" 
                                ? JSON.stringify(value) 
                                : String(value);
                              return `${key}="${formattedValue}"`;
                            })
                            .join(", ")}
                        </span>
                      </div>
                    )}

                    {/* Output summary (only when completed) */}
                    {!isRunning && action.output && (
                      <div className="text-xs text-muted-foreground">
                        <span className="font-medium">Output: </span>
                        {Array.isArray(action.output) ? (
                          <span>{action.output.length} result(s)</span>
                        ) : typeof action.output === "object" ? (
                          <span>1 result</span>
                        ) : (
                          <span className="font-mono">
                            {String(action.output).substring(0, 100)}
                            {String(action.output).length > 100 ? "..." : ""}
                          </span>
                        )}
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
