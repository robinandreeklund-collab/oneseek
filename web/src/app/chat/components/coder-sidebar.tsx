// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { PythonOutlined } from "@ant-design/icons";
import { motion } from "framer-motion";
import {
  Code,
  FileCode,
  FileText,
  Monitor,
  PencilRuler,
  X,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import { useMemo, useState } from "react";
import SyntaxHighlighter from "react-syntax-highlighter";
import { docco } from "react-syntax-highlighter/dist/esm/styles/hljs";
import { dark } from "react-syntax-highlighter/dist/esm/styles/prism";

import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { RainbowText } from "~/components/deer-flow/rainbow-text";
import { ScrollContainer } from "~/components/deer-flow/scroll-container";
import { Tooltip } from "~/components/deer-flow/tooltip";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "~/components/ui/accordion";
import { Badge } from "~/components/ui/badge";
import { Button } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { findMCPTool } from "~/core/mcp";
import type { ToolCallRuntime, WorkspaceFile } from "~/core/messages";
import { closeCoder, useMessage, useStore } from "~/core/store";
import { cn } from "~/lib/utils";

export function CoderSidebar({
  className,
  sessionId = null,
}: {
  className?: string;
  sessionId: string | null;
}) {
  const t = useTranslations("chat.coder");
  const [activeTab, setActiveTab] = useState("activities");

  return (
    <div className={cn("h-full w-full", className)}>
      <Card className={cn("relative h-full w-full pt-4", className)}>
        <div className="absolute right-4 flex h-9 items-center justify-center">
          <Tooltip title={t("close")}>
            <Button
              className="text-gray-400"
              size="sm"
              variant="ghost"
              onClick={() => {
                closeCoder();
              }}
            >
              <X />
            </Button>
          </Tooltip>
        </div>
        <Tabs
          className="flex h-full w-full flex-col"
          value={activeTab}
          onValueChange={(value) => setActiveTab(value)}
        >
          <div className="flex w-full justify-center">
            <TabsList className="">
              <TabsTrigger className="px-8" value="activities">
                {t("activities")}
              </TabsTrigger>
              <TabsTrigger className="px-8" value="preview">
                {t("preview")}
              </TabsTrigger>
              <TabsTrigger className="px-8" value="files">
                {t("files")}
              </TabsTrigger>
            </TabsList>
          </div>
          <TabsContent
            className="h-full min-h-0 flex-grow px-8"
            value="activities"
            forceMount
            hidden={activeTab !== "activities"}
          >
            <ScrollContainer
              className="h-full"
              scrollShadowColor="var(--card)"
              autoScrollToBottom
            >
              {sessionId && <CoderActivitiesBlock sessionId={sessionId} />}
            </ScrollContainer>
          </TabsContent>
          <TabsContent
            className="h-full min-h-0 flex-grow px-8"
            value="preview"
            forceMount
            hidden={activeTab !== "preview"}
          >
            <ScrollContainer
              className="h-full"
              scrollShadowColor="var(--card)"
              autoScrollToBottom={false}
            >
              {sessionId && <CoderPreviewBlock sessionId={sessionId} />}
            </ScrollContainer>
          </TabsContent>
          <TabsContent
            className="h-full min-h-0 flex-grow px-8"
            value="files"
            forceMount
            hidden={activeTab !== "files"}
          >
            <ScrollContainer
              className="h-full"
              scrollShadowColor="var(--card)"
              autoScrollToBottom
            >
              {sessionId && <CoderFilesBlock sessionId={sessionId} />}
            </ScrollContainer>
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
}

function CoderActivitiesBlock({ sessionId }: { sessionId: string }) {
  const activityIds = useStore((state) =>
    state.coderActivityIds.get(sessionId),
  );
  const ongoing = useStore(
    (state) => state.ongoingCoderSessionId === sessionId,
  );

  if (!activityIds || activityIds.length === 0) {
    return (
      <>
        {ongoing && <LoadingAnimation className="mx-4 my-12" />}
      </>
    );
  }

  return (
    <>
      <ul className="flex flex-col py-4">
        {activityIds.map((activityId, i) => (
          <motion.li
            key={activityId}
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.3,
              delay: Math.min(i * 0.05, 0.5),
              ease: "easeOut",
            }}
          >
            <CoderActivityItem messageId={activityId} />
            {i !== activityIds.length - 1 && <hr className="my-8" />}
          </motion.li>
        ))}
      </ul>
      {ongoing && <LoadingAnimation className="mx-4 my-12" />}
    </>
  );
}

function CoderActivityItem({ messageId }: { messageId: string }) {
  const message = useMessage(messageId);

  if (!message) {
    return null;
  }

  if (message.toolCalls?.length) {
    const toolCallComponents = message.toolCalls
      .slice()
      .sort((a, b) => {
        if (a.result && !b.result) return 1;
        if (!a.result && b.result) return -1;
        return 0;
      })
      .map((toolCall) => {
        if (toolCall.name === "python_repl_tool") {
          return <PythonToolCall key={toolCall.id} toolCall={toolCall} />;
        } else if (
          toolCall.name === "file_system_tool" ||
          toolCall.name === "bash_tool"
        ) {
          return <FileSystemToolCall key={toolCall.id} toolCall={toolCall} />;
        } else if (toolCall.name === "react_sandbox_tool") {
          return <ReactSandboxToolCall key={toolCall.id} toolCall={toolCall} />;
        } else {
          return <GenericToolCall key={toolCall.id} toolCall={toolCall} />;
        }
      });

    if (toolCallComponents.length > 0) {
      return <>{toolCallComponents}</>;
    }
  }

  return null;
}

function PythonToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const t = useTranslations("chat.coder");
  const code = useMemo<string | undefined>(() => {
    return (toolCall.args as { code?: string }).code;
  }, [toolCall.args]);
  const { resolvedTheme } = useTheme();
  const statusLabel = useMemo(() => {
    if (toolCall.result) {
      return toolCall.result.trim().startsWith("Error:")
        ? t("statusError")
        : t("statusSuccess");
    }
    if (toolCall.status === "running") {
      return t("statusRunning");
    }
    if (toolCall.status === "complete" || toolCall.status === "completed") {
      return t("statusSuccess");
    }
    return t("statusPending");
  }, [toolCall.result, toolCall.status, t]);

  return (
    <section className="mt-4 pl-4">
      <div className="flex items-center">
        <PythonOutlined className={"mr-2"} />
        <RainbowText
          className="text-base font-medium italic"
          animated={toolCall.result === undefined}
        >
          {t("runningPython")}
        </RainbowText>
        <Badge variant="secondary" className="ml-2">
          {statusLabel}
        </Badge>
      </div>
      <div>
        <div className="bg-accent mt-2 max-h-[400px] max-w-[calc(100%-120px)] overflow-y-auto rounded-md p-2 text-sm">
          <SyntaxHighlighter
            language="python"
            style={resolvedTheme === "dark" ? dark : docco}
            customStyle={{
              background: "transparent",
              border: "none",
              boxShadow: "none",
            }}
          >
            {code?.trim() ?? ""}
          </SyntaxHighlighter>
        </div>
      </div>
      {toolCall.result && <ToolCallResult result={toolCall.result} />}
    </section>
  );
}

function FileSystemToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const t = useTranslations("chat.coder");
  
  // Parse args - handle both parsed object and unparsed argsChunks
  const operation = useMemo<string | undefined>(() => {
    // If args is already parsed
    if (toolCall.args && typeof toolCall.args === 'object') {
      return (toolCall.args as { operation?: string }).operation;
    }
    // If still in argsChunks, try to parse
    if (toolCall.argsChunks) {
      try {
        const parsed = JSON.parse(toolCall.argsChunks.join(''));
        return parsed.operation;
      } catch {
        return undefined;
      }
    }
    return undefined;
  }, [toolCall.args, toolCall.argsChunks]);
  
  const path = useMemo<string | undefined>(() => {
    // If args is already parsed
    if (toolCall.args && typeof toolCall.args === 'object') {
      return (toolCall.args as { path?: string }).path;
    }
    // If still in argsChunks, try to parse
    if (toolCall.argsChunks) {
      try {
        const parsed = JSON.parse(toolCall.argsChunks.join(''));
        return parsed.path;
      } catch {
        return undefined;
      }
    }
    return undefined;
  }, [toolCall.args, toolCall.argsChunks]);
  const statusLabel = useMemo(() => {
    if (toolCall.result) {
      return toolCall.result.trim().startsWith("Error:")
        ? t("statusError")
        : t("statusSuccess");
    }
    if (toolCall.status === "running") {
      return t("statusRunning");
    }
    if (toolCall.status === "complete" || toolCall.status === "completed") {
      return t("statusSuccess");
    }
    return t("statusPending");
  }, [toolCall.result, toolCall.status, t]);

  return (
    <section className="mt-4 pl-4">
      <div className="flex items-center">
        <FileCode className={"mr-2"} size={16} />
        <RainbowText
          className="text-base font-medium italic"
          animated={toolCall.result === undefined}
        >
          {t("fileOperation")}: {operation ?? "unknown"}
          {path && ` → ${path}`}
        </RainbowText>
        <Badge variant="secondary" className="ml-2">
          {statusLabel}
        </Badge>
      </div>
      {toolCall.result && <ToolCallResult result={toolCall.result} />}
    </section>
  );
}

function ReactSandboxToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const t = useTranslations("chat.coder");
  const statusLabel = useMemo(() => {
    if (toolCall.result) {
      return toolCall.result.trim().startsWith("Error:")
        ? t("statusError")
        : t("statusSuccess");
    }
    if (toolCall.status === "running") {
      return t("statusRunning");
    }
    if (toolCall.status === "complete" || toolCall.status === "completed") {
      return t("statusSuccess");
    }
    return t("statusPending");
  }, [toolCall.result, toolCall.status, t]);

  return (
    <section className="mt-4 pl-4">
      <div className="flex items-center">
        <Code className={"mr-2"} size={16} />
        <RainbowText
          className="text-base font-medium italic"
          animated={toolCall.result === undefined}
        >
          {t("reactSandbox")}
        </RainbowText>
        <Badge variant="secondary" className="ml-2">
          {statusLabel}
        </Badge>
      </div>
      {toolCall.result && <ToolCallResult result={toolCall.result} />}
    </section>
  );
}

function GenericToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const t = useTranslations("chat.coder");
  const tool = useMemo(() => findMCPTool(toolCall.name), [toolCall.name]);
  const { resolvedTheme } = useTheme();
  const statusLabel = useMemo(() => {
    if (toolCall.result) {
      return t("statusSuccess");
    }
    if (toolCall.status === "running") {
      return t("statusRunning");
    }
    if (toolCall.status === "complete" || toolCall.status === "completed") {
      return t("statusSuccess");
    }
    return t("statusPending");
  }, [toolCall.result, toolCall.status, t]);

  return (
    <section className="mt-4 pl-4">
      <div className="w-fit overflow-y-auto rounded-md py-0">
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="item-1">
            <AccordionTrigger>
              <Tooltip title={tool?.description}>
                <div className="flex items-center font-medium italic">
                  <PencilRuler size={16} className={"mr-2"} />
                  <RainbowText
                    className="pr-0.5 text-base font-medium italic"
                    animated={toolCall.result === undefined}
                  >
                    {toolCall.result !== undefined
                      ? `Executed ${toolCall.name}()`
                      : `Running ${toolCall.name}()`}
                  </RainbowText>
                  <Badge variant="secondary" className="ml-2">
                    {statusLabel}
                  </Badge>
                </div>
              </Tooltip>
            </AccordionTrigger>
            <AccordionContent>
              {toolCall.result && (
                <div className="bg-accent max-h-[400px] max-w-[560px] overflow-y-auto rounded-md text-sm">
                  <div className="mb-2 p-2 border-b border-border/50 text-xs opacity-70">
                    <strong>Input:</strong>
                    <pre className="whitespace-pre-wrap mt-1">
                      {JSON.stringify(toolCall.args, null, 2)}
                    </pre>
                  </div>

                  <SyntaxHighlighter
                    language="markdown"
                    style={resolvedTheme === "dark" ? dark : docco}
                    wrapLongLines={true}
                    customStyle={{
                      background: "transparent",
                      border: "none",
                      boxShadow: "none",
                    }}
                  >
                    {toolCall.result.trim()}
                  </SyntaxHighlighter>
                </div>
              )}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </section>
  );
}

function ToolCallResult({ result }: { result: string }) {
  const t = useTranslations("chat.coder");
  const { resolvedTheme } = useTheme();
  const hasError = useMemo(
    () => result.trim().startsWith("Error:") || result.trim().startsWith("ERROR:"),
    [result],
  );

  return (
    <>
      <div className="mt-4 font-medium italic">
        {hasError ? t("error") : t("output")}
      </div>
      <div className="bg-accent mt-2 max-h-[400px] max-w-[calc(100%-120px)] overflow-y-auto rounded-md p-2 text-sm">
        <SyntaxHighlighter
          language="plaintext"
          style={resolvedTheme === "dark" ? dark : docco}
          customStyle={{
            color: hasError ? "red" : "inherit",
            background: "transparent",
            border: "none",
            boxShadow: "none",
          }}
        >
          {result.trim() || "(empty)"}
        </SyntaxHighlighter>
      </div>
    </>
  );
}

function CoderPreviewBlock({ sessionId }: { sessionId: string }) {
  const t = useTranslations("chat.coder");
  const activityIds = useStore((state) =>
    state.coderActivityIds.get(sessionId),
  );
  const messages = useStore((state) => state.messages);
  const workspaceFilesByMessage = useStore((state) => state.coderWorkspaceFiles);
  const previewHtml = useMemo(() => {
    if (!activityIds) return null;
    for (const activityId of [...activityIds].reverse()) {
      const workspaceFiles = workspaceFilesByMessage.get(activityId) ?? [];
      for (const file of workspaceFiles) {
        if (!file.path.endsWith(".html")) continue;
        if (file.content?.trim()) {
          return file.content;
        }
      }
      const message = messages.get(activityId);
      if (!message?.toolCalls) continue;
      for (const toolCall of message.toolCalls) {
        if (toolCall.name !== "file_system_tool") continue;
        const args = toolCall.args as { path?: string; content?: string; operation?: string };
        if (!args.path || (args.operation !== "write" && args.operation !== "create")) {
          continue;
        }
        if (!args.path.endsWith(".html")) continue;
        if (args.content?.trim()) {
          return args.content;
        }
      }
    }
    return null;
  }, [activityIds, messages, workspaceFilesByMessage]);

  const hasPreviewError = useMemo(() => {
    if (!activityIds) return false;
    for (const activityId of [...activityIds].reverse()) {
      const message = messages.get(activityId);
      if (!message?.toolCalls) continue;
      for (const toolCall of message.toolCalls) {
        if (toolCall.name !== "react_sandbox_tool") continue;
        if (toolCall.result?.trim().startsWith("Error:")) {
          return true;
        }
      }
    }
    return false;
  }, [activityIds, messages]);

  const previewUrl = useMemo(() => {
    if (!activityIds) return null;

    for (const activityId of [...activityIds].reverse()) {
      const message = messages.get(activityId);
      if (!message?.toolCalls) continue;

      for (const toolCall of message.toolCalls) {
        if (toolCall.name === "react_sandbox_tool" && toolCall.result) {
          try {
            const result = JSON.parse(toolCall.result);
            if (result.preview_url) {
              // Validate URL format and protocol
              try {
                const url = new URL(result.preview_url);
                if (url.protocol === "http:" || url.protocol === "https:") {
                  return result.preview_url;
                }
              } catch {
                // Invalid URL format
                return null;
              }
            }
          } catch {
            // Not JSON, try to extract URL with more robust pattern
            const urlMatch = /preview_url["':\s]+["']?(https?:\/\/[^\s'"]+)["']?/.exec(
              toolCall.result,
            );
            const previewUrlFromMatch = urlMatch?.[1];
            if (previewUrlFromMatch) {
              try {
                const url = new URL(previewUrlFromMatch);
                if (url.protocol === "http:" || url.protocol === "https:") {
                  return previewUrlFromMatch;
                }
              } catch {
                return null;
              }
            }
          }
        }
      }
    }
    return null;
  }, [activityIds, messages]);

    return (
      <div className="h-full w-full py-4">
        {previewUrl ? (
          <iframe
            src={previewUrl}
            className="h-full w-full rounded-lg border"
            title="React App Preview"
            sandbox="allow-scripts"
          />
        ) : previewHtml ? (
          <iframe
            srcDoc={previewHtml}
            className="h-full w-full rounded-lg border"
            title="HTML Preview"
            sandbox="allow-scripts"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <div className="text-center">
              <Monitor className="mx-auto mb-4 h-12 w-12 opacity-50" />
              <p className="text-muted-foreground">
                {hasPreviewError ? t("error") : t("noPreview")}
              </p>
            </div>
          </div>
        )}
      </div>
    );
}

function CoderFilesBlock({ sessionId }: { sessionId: string }) {
  const t = useTranslations("chat.coder");
  const activityIds = useStore((state) =>
    state.coderActivityIds.get(sessionId),
  );
  const messages = useStore((state) => state.messages);
  const workspaceFilesByMessage = useStore((state) => state.coderWorkspaceFiles);
  const [selectedFile, setSelectedFile] = useState<WorkspaceFile | null>(null);
  const { resolvedTheme } = useTheme();

  const files = useMemo(() => {
    const fileMap = new Map<string, WorkspaceFile>();
    if (!activityIds) return [];

    for (const activityId of activityIds) {
      const workspaceFiles = workspaceFilesByMessage.get(activityId) ?? [];
      if (workspaceFiles.length > 0) {
        workspaceFiles.forEach((file) => {
          fileMap.set(file.path, file);
        });
      }
      const message = messages.get(activityId);
      if (!message?.toolCalls) continue;

      for (const toolCall of message.toolCalls) {
        if (toolCall.name !== "file_system_tool") continue;
        const args = toolCall.args as {
          path?: string;
          operation?: string;
          content?: string;
        };
        if (!args.path) continue;
        const operation = args.operation ?? "unknown";
        fileMap.set(args.path, {
          path: args.path,
          name: args.path.split("/").pop() ?? args.path,
          operation,
          content: args.content ?? toolCall.result ?? "",
        });
      }
    }

    return Array.from(fileMap.values());
  }, [activityIds, messages, workspaceFilesByMessage]);

  return (
    <div className="py-4">
      {files.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {files.map((file, i) => (
            <motion.li
              key={file.path}
              className="bg-accent flex items-center justify-between gap-2 rounded-md p-3"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: i * 0.05 }}
            >
              <button
                type="button"
                className="flex min-w-0 flex-1 items-center gap-2 text-left"
                onClick={() => setSelectedFile(file)}
              >
                <FileText className="h-4 w-4 shrink-0" />
                <span className="truncate font-mono text-sm">{file.path}</span>
              </button>
              <Badge variant="secondary">
                {file.operation ?? "unknown"}
              </Badge>
            </motion.li>
          ))}
        </ul>
      ) : (
        <div className="flex h-full w-full items-center justify-center">
          <div className="text-center">
            <FileText className="mx-auto mb-4 h-12 w-12 opacity-50" />
            <p className="text-muted-foreground">{t("noFiles")}</p>
          </div>
        </div>
      )}
      <Dialog
        open={Boolean(selectedFile)}
        onOpenChange={(open) => {
          if (!open) setSelectedFile(null);
        }}
      >
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>{selectedFile?.path}</DialogTitle>
            <DialogDescription>
              {selectedFile?.operation ?? "unknown"}
            </DialogDescription>
          </DialogHeader>
          <div className="bg-accent max-h-[60vh] overflow-auto rounded-md p-4 text-sm">
            <SyntaxHighlighter
              language="text"
              style={resolvedTheme === "dark" ? dark : docco}
              customStyle={{
                background: "transparent",
                border: "none",
                boxShadow: "none",
              }}
            >
              {selectedFile?.content?.trim() || "(empty)"}
            </SyntaxHighlighter>
          </div>
          {selectedFile?.truncated && (
            <p className="text-xs text-muted-foreground">
              Showing truncated content
            </p>
          )}
          </DialogContent>
        </Dialog>
    </div>
  );
}
