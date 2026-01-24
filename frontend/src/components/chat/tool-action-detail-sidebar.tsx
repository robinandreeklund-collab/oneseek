import React from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Card, CardContent } from "@/components/ui/card";
import { XIcon, Clock, PlayCircle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ToolAction } from "@/types/tool-action";

interface ToolActionDetailSidebarProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  toolAction: ToolAction | null;
}

export function ToolActionDetailSidebar({
  open,
  onOpenChange,
  toolAction,
}: ToolActionDetailSidebarProps) {
  if (!toolAction) return null;

  const getColorClasses = (color: string) => {
    const colorMap: Record<string, { text: string; bg: string; border: string }> = {
      blue: { text: "text-blue-400", bg: "bg-blue-400/10", border: "border-blue-400" },
      green: { text: "text-green-400", bg: "bg-green-400/10", border: "border-green-400" },
      purple: { text: "text-purple-400", bg: "bg-purple-400/10", border: "border-purple-400" },
      gray: { text: "text-gray-400", bg: "bg-gray-400/10", border: "border-gray-400" },
    };
    return colorMap[color] || colorMap.gray;
  };

  const colors = getColorClasses(toolAction.color);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:w-[440px] md:w-[520px] lg:w-[600px] p-0 flex flex-col"
      >
        {/* Fixed Header */}
        <div className="flex-shrink-0 border-b bg-background">
          <div className="flex items-center justify-between p-6">
            <div className="flex-1 min-w-0 flex items-center gap-3">
              <span className="text-2xl">{toolAction.icon}</span>
              <div>
                <SheetTitle className={`text-lg font-semibold ${colors.text}`}>
                  {toolAction.display_name}
                </SheetTitle>
                <SheetDescription className="mt-1 text-sm">
                  Complete tool invocation details
                </SheetDescription>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onOpenChange(false)}
              className="flex-shrink-0 ml-4 h-8 w-8"
            >
              <XIcon className="h-4 w-4" />
              <span className="sr-only">Close</span>
            </Button>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-6 space-y-6">
            {/* Status and Timing */}
            <Card>
              <CardContent className="p-4">
                <h3 className="text-sm font-semibold mb-3">Status & Timing</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    {toolAction.status === "completed" ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <PlayCircle className="h-4 w-4 text-blue-500" />
                    )}
                    <span className="font-medium">Status:</span>
                    <span className="text-muted-foreground capitalize">
                      {toolAction.status}
                    </span>
                  </div>
                  {toolAction.duration !== undefined && (
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4" />
                      <span className="font-medium">Duration:</span>
                      <span className="text-muted-foreground">
                        {toolAction.duration.toFixed(3)}s
                      </span>
                    </div>
                  )}
                  {toolAction.iteration !== undefined && (
                    <div className="flex items-center gap-2">
                      <span className="font-medium">Iteration:</span>
                      <span className="text-muted-foreground">
                        {toolAction.iteration}
                      </span>
                    </div>
                  )}
                  {toolAction.tool_call_id && (
                    <div className="flex items-start gap-2">
                      <span className="font-medium">Call ID:</span>
                      <span className="text-muted-foreground font-mono text-xs break-all">
                        {toolAction.tool_call_id}
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Model Reasoning */}
            {toolAction.reasoning && (
              <Card>
                <CardContent className="p-4">
                  <h3 className="text-sm font-semibold mb-3">Model Reasoning</h3>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {toolAction.reasoning}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Raw Request */}
            {toolAction.raw_request && (
              <Card>
                <CardContent className="p-4">
                  <h3 className="text-sm font-semibold mb-3">Raw Request</h3>
                  <div className="bg-muted/50 p-3 rounded-md overflow-x-auto">
                    <pre className="text-xs font-mono">
                      {JSON.stringify(toolAction.raw_request, null, 2)}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Input Parameters */}
            <Card>
              <CardContent className="p-4">
                <h3 className="text-sm font-semibold mb-3">Input Parameters</h3>
                <div className="bg-muted/50 p-3 rounded-md overflow-x-auto">
                  <pre className="text-xs font-mono">
                    {JSON.stringify(toolAction.input, null, 2)}
                  </pre>
                </div>
              </CardContent>
            </Card>

            {/* Raw Response */}
            {toolAction.raw_response && (
              <Card>
                <CardContent className="p-4">
                  <h3 className="text-sm font-semibold mb-3">Raw Response</h3>
                  <div className="bg-muted/50 p-3 rounded-md overflow-x-auto">
                    <pre className="text-xs font-mono">
                      {JSON.stringify(toolAction.raw_response, null, 2)}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Parsed Output */}
            {toolAction.output && (
              <Card>
                <CardContent className="p-4">
                  <h3 className="text-sm font-semibold mb-3">Parsed Output</h3>
                  <div className="bg-muted/50 p-3 rounded-md overflow-x-auto">
                    <pre className="text-xs font-mono">
                      {JSON.stringify(toolAction.output, null, 2)}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
