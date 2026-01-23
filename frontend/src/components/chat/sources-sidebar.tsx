import React from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Card, CardContent } from "@/components/ui/card";
import { ExternalLinkIcon, XIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

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
      <SheetContent 
        side="right" 
        className="w-full sm:w-[440px] md:w-[480px] lg:w-[520px] p-0 flex flex-col"
      >
        {/* Fixed Header */}
        <div className="flex-shrink-0 border-b bg-background">
          <div className="flex items-center justify-between p-6">
            <div className="flex-1 min-w-0">
              <SheetTitle className="text-lg font-semibold">Källor</SheetTitle>
              <SheetDescription className="mt-1 text-sm">
                {sources.length} {sources.length === 1 ? "källa" : "källor"} använda för detta svar
              </SheetDescription>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onOpenChange(false)}
              className="flex-shrink-0 ml-4 h-8 w-8"
            >
              <XIcon className="h-4 w-4" />
              <span className="sr-only">Stäng</span>
            </Button>
          </div>
        </div>
        
        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-6 space-y-4">
            {sources.map((source, index) => (
              <Card
                key={index}
                className="group cursor-pointer transition-all duration-200 hover:shadow-md hover:border-primary/20 active:scale-[0.98]"
                onClick={() => source.url && window.open(source.url, "_blank", "noopener,noreferrer")}
              >
                <CardContent className="p-5">
                  {/* Source number badge */}
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-medium">
                      {index + 1}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      {/* Title */}
                      <h3 className="text-sm font-semibold leading-snug line-clamp-2 mb-2 group-hover:text-primary transition-colors">
                        {source.title}
                      </h3>
                      
                      {/* Content excerpt */}
                      <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3 mb-3">
                        {source.content}
                      </p>
                      
                      {/* URL and source tool */}
                      <div className="flex flex-wrap items-center gap-3 text-xs">
                        {source.url && (
                          <div className="flex items-center gap-1.5 text-muted-foreground group-hover:text-foreground transition-colors">
                            <ExternalLinkIcon className="h-3.5 w-3.5 flex-shrink-0" />
                            <span className="truncate font-medium">
                              {new URL(source.url).hostname.replace('www.', '')}
                            </span>
                          </div>
                        )}
                        
                        {source.source && (
                          <>
                            {source.url && (
                              <span className="text-muted-foreground/40">•</span>
                            )}
                            <span className="text-muted-foreground/70">
                              via {source.source}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
