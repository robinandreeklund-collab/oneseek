import React from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";
import { ExternalLinkIcon } from "lucide-react";

export interface Source {
  title: string;
  content: string;
  url?: string;
  relevance?: number;
  source?: string;
}

interface SourcesSidebarProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sources: Source[];
}

export function SourcesSidebar({ open, onOpenChange, sources }: SourcesSidebarProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Sources</SheetTitle>
          <SheetDescription>
            {sources.length} {sources.length === 1 ? "source" : "sources"} used for this response
          </SheetDescription>
        </SheetHeader>
        
        <div className="mt-6 space-y-3">
          {sources.map((source, index) => (
            <Card
              key={index}
              className="cursor-pointer transition-colors hover:bg-accent/50"
              onClick={() => source.url && window.open(source.url, "_blank")}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-sm font-medium leading-tight line-clamp-2 mb-2">
                      {source.title}
                    </CardTitle>
                    <CardDescription className="text-xs line-clamp-3">
                      {source.content}
                    </CardDescription>
                    {source.url && (
                      <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                        <ExternalLinkIcon className="h-3 w-3" />
                        <span className="truncate">{new URL(source.url).hostname}</span>
                      </div>
                    )}
                  </div>
                </div>
                {source.source && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    via {source.source}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </SheetContent>
    </Sheet>
  );
}
