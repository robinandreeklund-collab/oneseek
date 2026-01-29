import React, { useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { XIcon, Clock, PlayCircle, CheckCircle, FileText, Activity } from "lucide-react";
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
  const [activeTab, setActiveTab] = useState("activities");
  
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
  
  // Extract workspace files if available
  const workspaceFiles = (toolAction as any).workspace_files || [];

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

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-2 rounded-none border-b">
            <TabsTrigger value="activities" className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Aktiviteter
            </TabsTrigger>
            <TabsTrigger value="files" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Filer
            </TabsTrigger>
          </TabsList>

          {/* Activities Tab */}
          <TabsContent value="activities" className="flex-1 overflow-y-auto m-0">
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
        </TabsContent>

        {/* Files Tab */}
        <TabsContent value="files" className="flex-1 overflow-y-auto m-0">
          <div className="p-6">
            {workspaceFiles && workspaceFiles.length > 0 ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold">
                    Workspace Filer ({workspaceFiles.length})
                  </h3>
                </div>
                {workspaceFiles.map((file: any, index: number) => (
                  <Card key={index} className="hover:bg-muted/50 transition-colors">
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        <FileText className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <h4 className="text-sm font-medium break-all">
                              {file.path || file.name}
                            </h4>
                            {file.size && (
                              <span className="text-xs text-muted-foreground whitespace-nowrap">
                                {formatFileSize(file.size)}
                              </span>
                            )}
                          </div>
                          {file.content && (
                            <div className="bg-muted/50 p-2 rounded text-xs font-mono overflow-x-auto max-h-32 overflow-y-auto">
                              <pre className="whitespace-pre-wrap break-words">
                                {file.content.substring(0, 500)}
                                {file.content.length > 500 && '...'}
                              </pre>
                            </div>
                          )}
                          {file.type && (
                            <div className="mt-2 text-xs text-muted-foreground">
                              Type: {file.type}
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <FileText className="h-12 w-12 text-muted-foreground/50 mb-4" />
                <h3 className="text-sm font-medium text-muted-foreground mb-2">
                  Inga filer skapade än
                </h3>
                <p className="text-xs text-muted-foreground/70 max-w-sm">
                  Filer som skapas i workspace kommer att visas här
                </p>
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
      </SheetContent>
    </Sheet>
  );
}

// Helper function to format file size
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
