/**
 * ActionTimeline - Design Proposal 2: Timeline View
 * 
 * Shows all tool actions in a vertical timeline format.
 * Each action is connected with a visual line showing the flow.
 */

import React from "react";
import { ToolAction } from "./ActionBlock";

interface ActionTimelineProps {
  actions: ToolAction[];
}

const TOOL_ICONS = {
  web_search: "🔍",
  browse_page: "🌐",
  smhi_api: "🌤️"
};

const TOOL_LABELS = {
  web_search: "Webbsökning",
  browse_page: "Läser sida",
  smhi_api: "SMHI Väder"
};

const TOOL_COLORS = {
  web_search: "border-blue-400 bg-blue-100 dark:bg-blue-950",
  browse_page: "border-green-400 bg-green-100 dark:bg-green-950",
  smhi_api: "border-purple-400 bg-purple-100 dark:bg-purple-950"
};

const STATUS_ICONS = {
  pending: "⏳",
  running: "⚙️",
  complete: "✅",
  error: "❌"
};

export default function ActionTimeline({ actions }: ActionTimelineProps) {
  if (actions.length === 0) {
    return null;
  }

  return (
    <div className="my-4 relative">
      {/* Timeline line */}
      <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-border"></div>
      
      <div className="space-y-4">
        {actions.map((action, index) => (
          <div key={index} className="relative pl-14">
            {/* Timeline dot */}
            <div className={`absolute left-3 top-2 w-6 h-6 rounded-full border-2 ${TOOL_COLORS[action.tool]} flex items-center justify-center text-xs z-10`}>
              {TOOL_ICONS[action.tool]}
            </div>
            
            {/* Action card */}
            <div className="rounded-lg border border-border bg-card p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="font-semibold text-sm flex items-center gap-2">
                    {TOOL_LABELS[action.tool]}
                    <span className="text-xs">{STATUS_ICONS[action.status]}</span>
                  </div>
                  {action.duration && (
                    <div className="text-xs text-muted-foreground mt-1">
                      {action.duration.toFixed(2)}s
                    </div>
                  )}
                </div>
              </div>
              
              {action.input && (
                <div className="text-xs text-muted-foreground mb-2">
                  <span className="font-semibold">Input:</span> {action.input}
                </div>
              )}
              
              {action.output && (
                <div className="text-xs bg-muted/50 rounded p-2 mt-2">
                  {action.output}
                </div>
              )}
              
              {action.metadata && Object.keys(action.metadata).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {Object.entries(action.metadata).map(([key, value]) => (
                    <span key={key} className="text-xs bg-muted px-2 py-1 rounded">
                      <span className="font-semibold">{key}:</span> {String(value)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
