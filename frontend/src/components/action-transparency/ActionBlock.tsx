/**
 * ActionBlock - Design Proposal 1: Inline Tool Actions
 * 
 * Shows tool actions inline with the chat flow, similar to ThinkBlock.
 * Each tool action (web search, browse_page, SMHI API) is displayed
 * with the same visual style as the "Thoughts" section.
 */

import React, { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export interface ToolAction {
  tool: "web_search" | "browse_page" | "smhi_api";
  status: "pending" | "running" | "complete" | "error";
  input?: string;
  output?: string;
  duration?: number;
  metadata?: Record<string, any>;
}

interface ActionBlockProps {
  action: ToolAction;
  live?: boolean;
}

const TOOL_LABELS = {
  web_search: "🔍 Webbsökning",
  browse_page: "🌐 Läser sida",
  smhi_api: "🌤️ SMHI Väder"
};

const TOOL_COLORS = {
  web_search: {
    border: "border-blue-400",
    text: "text-blue-400",
    bg: "bg-blue-50 dark:bg-blue-950/20"
  },
  browse_page: {
    border: "border-green-400",
    text: "text-green-400",
    bg: "bg-green-50 dark:bg-green-950/20"
  },
  smhi_api: {
    border: "border-purple-400",
    text: "text-purple-400",
    bg: "bg-purple-50 dark:bg-purple-950/20"
  }
};

export default function ActionBlock({ action, live = false }: ActionBlockProps) {
  const [seconds, setSeconds] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const [open, setOpen] = useState(live ? true : action.status === "complete" ? false : true);

  useEffect(() => {
    if (live || action.status === "running") {
      intervalRef.current = setInterval(() => {
        setSeconds((s) => +(s + 0.1).toFixed(2));
      }, 100);
      return () => {
        if (intervalRef.current) clearInterval(intervalRef.current);
      };
    }
  }, [live, action.status]);

  const isOpen = (live || action.status === "running") ? true : open;
  const colors = TOOL_COLORS[action.tool];

  return (
    <div className={`my-4 rounded-xl border border-dashed ${colors.border} bg-background/50`}>
      <div className="flex items-center px-4 pt-2 pb-1 select-none">
        {/* Chevron */}
        {(live || action.status === "running") ? (
          <span className="mr-2 inline-block transition-transform rotate-0" style={{ width: 20, height: 20 }}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M7 8l3 3 3-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={colors.text}/>
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
              className={`inline-block transition-transform duration-200 ${open ? "rotate-0" : "-rotate-90"}`}
              style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 20, width: 20 }}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M7 8l3 3 3-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={colors.text}/>
              </svg>
            </span>
          </button>
        )}
        
        {/* Label */}
        <span className={`${colors.text} font-medium text-sm mr-3`}>
          {TOOL_LABELS[action.tool]}
        </span>
        
        {/* Status and timing */}
        {(live || action.status === "running") ? (
          <span className="italic text-sm text-muted-foreground flex items-center gap-2">
            Kör i {action.duration ? action.duration.toFixed(2) : seconds.toFixed(2)} sekunder
            <span className="ml-1 inline-block align-middle">
              <span className={`w-4 h-4 border-2 ${colors.border} border-t-transparent rounded-full inline-block animate-spin`}></span>
            </span>
          </span>
        ) : action.status === "complete" ? (
          <span className="italic text-sm text-muted-foreground">
            {action.duration ? `Slutförde på ${action.duration.toFixed(2)}s` : "Slutförd"}
          </span>
        ) : action.status === "error" ? (
          <span className="italic text-sm text-red-500">
            Fel uppstod
          </span>
        ) : (
          <span className="italic text-sm text-muted-foreground">
            Väntar...
          </span>
        )}
      </div>
      
      {isOpen && (
        <div className="px-6 pb-4 pt-1 text-sm">
          {/* Input */}
          {action.input && (
            <div className="mb-3">
              <div className="text-xs font-semibold text-muted-foreground mb-1">Input:</div>
              <div className={`rounded-md ${colors.bg} p-2 text-xs`}>
                {action.input}
              </div>
            </div>
          )}
          
          {/* Output */}
          {action.output && (
            <div className="mb-3">
              <div className="text-xs font-semibold text-muted-foreground mb-1">Resultat:</div>
              <div className="text-muted-foreground">
                <Markdown remarkPlugins={[remarkGfm]}>{action.output}</Markdown>
              </div>
            </div>
          )}
          
          {/* Metadata */}
          {action.metadata && Object.keys(action.metadata).length > 0 && (
            <div className="mt-2 grid grid-cols-2 gap-2">
              {Object.entries(action.metadata).map(([key, value]) => (
                <div key={key} className="text-xs">
                  <span className="text-muted-foreground font-semibold">{key}:</span>{" "}
                  <span className="text-foreground">{String(value)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
