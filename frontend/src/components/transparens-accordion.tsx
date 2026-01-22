"use client";

import React from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronDown, FileText, ListOrdered } from "lucide-react";

interface RetrievedDoc {
  title?: string;
  content: string;
  score?: number;
  source?: string;
}

interface TransparensAccordionProps {
  retrieved?: RetrievedDoc[];
  steps?: string[];
  prompt?: string;
  response?: string;
}

export function TransparensAccordion({
  retrieved = [],
  steps = [],
  prompt,
  response,
}: TransparensAccordionProps) {
  const [isOpen, setIsOpen] = React.useState(false);

  // Don't render if there's no data to show
  if (retrieved.length === 0 && steps.length === 0 && !prompt && !response) {
    return null;
  }

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className="mt-2 rounded-lg border border-border/40 bg-muted/20"
    >
      <CollapsibleTrigger className="flex w-full items-center justify-between px-4 py-2 text-sm font-medium hover:bg-muted/40 transition-colors">
        <span className="flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Källor & steg
          {retrieved.length > 0 && (
            <span className="text-xs text-muted-foreground">
              ({retrieved.length} dokument)
            </span>
          )}
        </span>
        <ChevronDown
          className={`h-4 w-4 transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="px-4 py-3 space-y-4">
        {/* Retrieved Documents */}
        {retrieved.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Hämtade dokument från Vespa
            </h4>
            <div className="space-y-2">
              {retrieved.map((doc, idx) => (
                <div
                  key={idx}
                  className="rounded-md border border-border/50 bg-background/50 p-3 text-xs"
                >
                  {doc.title && (
                    <div className="font-semibold text-sm mb-1">{doc.title}</div>
                  )}
                  <div className="text-muted-foreground line-clamp-3">
                    {doc.content}
                  </div>
                  {doc.score !== undefined && (
                    <div className="mt-2 text-xs text-muted-foreground">
                      Score: {doc.score.toFixed(4)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Processing Steps */}
        {steps.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
              <ListOrdered className="h-4 w-4" />
              LangGraph steg
            </h4>
            <ol className="space-y-1 pl-4 text-xs text-muted-foreground">
              {steps.map((step, idx) => (
                <li key={idx} className="list-decimal">
                  {step}
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Raw Prompt (if available) */}
        {prompt && (
          <div>
            <h4 className="text-sm font-semibold mb-2">Raw Prompt</h4>
            <pre className="rounded-md bg-background/80 p-3 text-xs overflow-x-auto">
              {prompt}
            </pre>
          </div>
        )}

        {/* LLM Response (if available separately) */}
        {response && (
          <div>
            <h4 className="text-sm font-semibold mb-2">LLM Response</h4>
            <div className="rounded-md bg-background/80 p-3 text-xs">
              {response}
            </div>
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}
