import React, { useState } from "react";
import { ToolAction } from "@/types/tool-action";
import { ChevronDown } from "lucide-react";

interface ActionBlockProps {
  actions: ToolAction[];
  live?: boolean;
  onToolClick?: (action: ToolAction) => void;
}

export default function ActionBlock({ actions, live = false, onToolClick }: ActionBlockProps) {
  // Collapsible state - start collapsed after completion, open during live
  const [open, setOpen] = useState(live);

  if (!actions || actions.length === 0) {
    return null;
  }

  const isOpen = live || open;

  return (
    <div className="my-3">
      {/* Header - matches "Reviewed 10 sources" style */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ChevronDown
          className={`h-4 w-4 transition-transform ${
            isOpen ? "rotate-0" : "-rotate-90"
          }`}
        />
        <span>
          Reviewed {actions.length} action{actions.length !== 1 ? "s" : ""}
        </span>
      </button>

      {/* Tool list - simple list matching the reference design */}
      {isOpen && (
        <div className="mt-2 ml-5 space-y-0.5">
          {actions.map((action, idx) => {
            const isRunning = action.status === "running";
            const duration = action.duration ? `${action.duration.toFixed(2)}s` : null;

            // Get text color based on tool color
            const getTextColor = (color: string) => {
              const colorMap: Record<string, string> = {
                blue: "text-blue-400",
                green: "text-green-400",
                purple: "text-purple-400",
                gray: "text-gray-400",
              };
              return colorMap[color] || "text-muted-foreground";
            };

            return (
              <div
                key={action.tool_call_id || idx}
                onClick={() => onToolClick && onToolClick(action)}
                className="py-1.5 cursor-pointer hover:opacity-80 transition-opacity"
              >
                <div className="flex items-start gap-2">
                  {/* Icon */}
                  <span className="text-base mt-0.5">{action.icon}</span>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    {/* Tool name with duration */}
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-medium ${getTextColor(action.color)}`}>
                        {action.display_name}
                      </span>
                      {isRunning ? (
                        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground italic">
                          <span className="w-2 h-2 border-2 border-current border-t-transparent rounded-full inline-block animate-spin"></span>
                          Running...
                        </span>
                      ) : duration ? (
                        <span className="text-xs text-muted-foreground">{duration}</span>
                      ) : null}
                    </div>

                    {/* Input parameters - simplified */}
                    {action.input && Object.keys(action.input).length > 0 && (
                      <div className="text-xs text-muted-foreground/70 mt-0.5">
                        Input: {Object.entries(action.input)
                          .map(([key, value]) => {
                            const formattedValue = typeof value === "object"
                              ? JSON.stringify(value)
                              : String(value);
                            const displayValue = formattedValue.length > 40
                              ? formattedValue.substring(0, 40) + "..."
                              : formattedValue;
                            return `${key}="${displayValue}"`;
                          })
                          .join(", ")}
                      </div>
                    )}

                    {/* Output - simplified */}
                    {!isRunning && action.output && (
                      <div className="text-xs text-muted-foreground/70 mt-0.5">
                        Output: {Array.isArray(action.output)
                          ? `${action.output.length} result${action.output.length !== 1 ? "s" : ""}`
                          : typeof action.output === "object"
                          ? "1 result"
                          : String(action.output).substring(0, 50) +
                            (String(action.output).length > 50 ? "..." : "")}
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
