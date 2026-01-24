/**
 * ActionCards - Design Proposal 3: Compact Card Grid
 * 
 * Shows tool actions as compact cards in a responsive grid.
 * Good for when multiple tools run in parallel.
 */

import React, { useState } from "react";
import { ToolAction } from "./ActionBlock";
import { ChevronDown } from "lucide-react";

interface ActionCardsProps {
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
  web_search: "border-blue-400/50 hover:border-blue-400",
  browse_page: "border-green-400/50 hover:border-green-400",
  smhi_api: "border-purple-400/50 hover:border-purple-400"
};

const STATUS_COLORS = {
  pending: "bg-yellow-100 dark:bg-yellow-950 text-yellow-700 dark:text-yellow-300",
  running: "bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 animate-pulse",
  complete: "bg-green-100 dark:bg-green-950 text-green-700 dark:text-green-300",
  error: "bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300"
};

const STATUS_LABELS = {
  pending: "Väntar",
  running: "Kör",
  complete: "Klar",
  error: "Fel"
};

function ActionCard({ action }: { action: ToolAction }) {
  const [expanded, setExpanded] = useState(false);
  
  return (
    <div className={`rounded-lg border-2 ${TOOL_COLORS[action.tool]} bg-card transition-all duration-200 hover:shadow-md`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 text-left"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{TOOL_ICONS[action.tool]}</span>
            <div>
              <div className="font-semibold text-sm">{TOOL_LABELS[action.tool]}</div>
              {action.duration && (
                <div className="text-xs text-muted-foreground">{action.duration.toFixed(2)}s</div>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[action.status]}`}>
              {STATUS_LABELS[action.status]}
            </span>
            <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${expanded ? "rotate-180" : ""}`} />
          </div>
        </div>
      </button>
      
      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-border/50 pt-2">
          {action.input && (
            <div>
              <div className="text-xs font-semibold text-muted-foreground mb-1">Input:</div>
              <div className="text-xs bg-muted/50 rounded p-2">{action.input}</div>
            </div>
          )}
          
          {action.output && (
            <div>
              <div className="text-xs font-semibold text-muted-foreground mb-1">Resultat:</div>
              <div className="text-xs bg-muted/50 rounded p-2 max-h-32 overflow-y-auto">
                {action.output}
              </div>
            </div>
          )}
          
          {action.metadata && Object.keys(action.metadata).length > 0 && (
            <div className="flex flex-wrap gap-1">
              {Object.entries(action.metadata).map(([key, value]) => (
                <span key={key} className="text-xs bg-muted px-2 py-1 rounded">
                  <span className="font-semibold">{key}:</span> {String(value)}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ActionCards({ actions }: ActionCardsProps) {
  if (actions.length === 0) {
    return null;
  }

  return (
    <div className="my-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {actions.map((action, index) => (
        <ActionCard key={index} action={action} />
      ))}
    </div>
  );
}
