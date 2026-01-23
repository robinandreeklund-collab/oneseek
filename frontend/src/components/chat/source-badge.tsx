import React from "react";
import { Button } from "@/components/ui/button";
import { SearchIcon } from "lucide-react";

interface SourceBadgeProps {
  sourceCount: number;
  onClick: () => void;
}

export function SourceBadge({ sourceCount, onClick }: SourceBadgeProps) {
  if (sourceCount === 0) return null;

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onClick}
      className="mb-2 h-7 gap-1.5 rounded-md border border-border/40 bg-background px-2 text-xs hover:bg-accent/50"
    >
      <SearchIcon className="h-3 w-3" />
      <span className="text-muted-foreground">
        Web search completed · {sourceCount} {sourceCount === 1 ? "source" : "sources"}
      </span>
    </Button>
  );
}
