import React, { useState } from "react";
import { ToolAction } from "@/types/tool-action";
import { ChevronDown, Search, FileText, Loader2 } from "lucide-react";

interface ActionBlockProps {
  actions: ToolAction[];
  live?: boolean;
  onToolClick?: (action: ToolAction) => void;
}

export default function ActionBlock({ actions, live = false, onToolClick }: ActionBlockProps) {
  const [open, setOpen] = useState(live);

  if (!actions || actions.length === 0) {
    return null;
  }

  const isOpen = live || open;

  // Group actions by type for workflow display
  const searchActions = actions.filter(a => 
    a.display_name === "web_search" || a.tool_name === "tavily_search"
  );
  const browseActions = actions.filter(a => 
    a.display_name === "browse_page" || a.tool_name === "browse_page"
  );
  const otherActions = actions.filter(a => 
    a.display_name !== "web_search" && 
    a.display_name !== "browse_page" &&
    a.tool_name !== "tavily_search" &&
    a.tool_name !== "browse_page"
  );

  const allCompleted = actions.every(a => a.status === "completed");
  const hasSearching = searchActions.length > 0;
  const hasReviewing = browseActions.length > 0;
  const hasOther = otherActions.length > 0;

  // Extract task description from first search query
  const getTaskDescription = () => {
    const firstSearch = searchActions[0];
    if (!firstSearch?.input) return null;
    if (typeof firstSearch.input === "string") return firstSearch.input;
    if (typeof firstSearch.input === "object") {
      return firstSearch.input.query || firstSearch.input.search_query || null;
    }
    return null;
  };

  // Get all search queries
  const getSearchQueries = () => {
    return searchActions.map(action => {
      if (!action.input) return null;
      if (typeof action.input === "string") return action.input;
      if (typeof action.input === "object") {
        return action.input.query || action.input.search_query || null;
      }
      return null;
    }).filter(Boolean);
  };

  // Get sources from browse actions
  const getSources = () => {
    return browseActions.map((action) => {
      let url = "";
      if (action.input) {
        if (typeof action.input === "string") {
          url = action.input;
        } else if (typeof action.input === "object") {
          url = action.input.url || action.input.uri || "";
        }
      }
      
      // Extract domain or title from URL
      let displayName = "source";
      try {
        const urlObj = new URL(url);
        displayName = urlObj.hostname.replace("www.", "");
      } catch (e) {
        // If URL parsing fails, use truncated URL
        displayName = url.substring(0, 30);
      }

      return {
        action,
        url,
        displayName,
        isRunning: action.status === "running"
      };
    });
  };

  const taskDescription = getTaskDescription();
  const searchQueries = getSearchQueries();
  const sources = getSources();
  const statusText = allCompleted ? "used" : "invoked";

  return (
    <div className="my-3">
      {/* Header */}
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
          Actions {actions.length} tool{actions.length !== 1 ? "s" : ""} {statusText}
        </span>
      </button>

      {/* Workflow stages */}
      {isOpen && (
        <div className="mt-2 ml-5 space-y-3">
          {/* Task description */}
          {taskDescription && (
            <div className="flex items-start gap-2 text-sm text-muted-foreground">
              <div className="w-2 h-2 rounded-full bg-muted mt-1.5 flex-shrink-0"></div>
              <span>{taskDescription}</span>
            </div>
          )}

          {/* Searching stage */}
          {hasSearching && (
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  searchActions.some(a => a.status === "running") 
                    ? "bg-blue-500 animate-pulse" 
                    : "bg-muted"
                }`}></div>
                <span className="text-sm text-muted-foreground">Searching</span>
              </div>
              <div className="ml-4 space-y-1">
                {searchQueries.map((query, idx) => (
                  <div 
                    key={idx}
                    className="flex items-center gap-2 text-sm text-muted-foreground"
                  >
                    <Search className="h-3.5 w-3.5 flex-shrink-0" />
                    <span className="text-xs">{query}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reviewing sources stage */}
          {hasReviewing && (
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  browseActions.some(a => a.status === "running") 
                    ? "bg-green-500 animate-pulse" 
                    : "bg-muted"
                }`}></div>
                <span className="text-sm text-muted-foreground">Reviewing sources</span>
              </div>
              <div className="ml-4 space-y-1">
                {sources.map((source, idx) => (
                  <div 
                    key={idx}
                    onClick={() => onToolClick?.(source.action)}
                    className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
                  >
                    <FileText className="h-3.5 w-3.5 flex-shrink-0" />
                    <span className="text-xs truncate">{source.displayName}</span>
                    {source.isRunning && (
                      <Loader2 className="h-3 w-3 animate-spin flex-shrink-0" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Other tools stage */}
          {hasOther && (
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  otherActions.some(a => a.status === "running") 
                    ? "bg-purple-500 animate-pulse" 
                    : "bg-muted"
                }`}></div>
                <span className="text-sm text-muted-foreground">Processing</span>
              </div>
              <div className="ml-4 space-y-1">
                {otherActions.map((action, idx) => (
                  <div 
                    key={action.tool_call_id || idx}
                    onClick={() => onToolClick?.(action)}
                    className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
                  >
                    <span className="text-base flex-shrink-0">{action.icon}</span>
                    <span className="text-xs">{action.display_name}</span>
                    {action.status === "running" ? (
                      <Loader2 className="h-3 w-3 animate-spin flex-shrink-0" />
                    ) : action.duration ? (
                      <span className="text-xs">({action.duration.toFixed(2)}s)</span>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Finished indicator */}
          {allCompleted && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-2 h-2 rounded-full bg-muted flex-shrink-0"></div>
              <span>Finished</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
