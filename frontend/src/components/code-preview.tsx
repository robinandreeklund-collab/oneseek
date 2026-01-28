import React, { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Code, Eye, Terminal, FileCode, Loader2, ExternalLink, RefreshCw } from "lucide-react";

interface CodePreviewProps {
  projectName?: string;
  previewUrl?: string;
  code?: string;
  language?: string;
  live?: boolean;
  onRefresh?: () => void;
}

interface CodeFile {
  name: string;
  content: string;
  language: string;
}

export default function CodePreview({
  projectName = "Preview",
  previewUrl,
  code,
  language = "javascript",
  live = false,
  onRefresh,
}: CodePreviewProps) {
  const [activeTab, setActiveTab] = useState<"preview" | "code" | "terminal">("preview");
  const [isLoading, setIsLoading] = useState(true);
  const [terminalOutput, setTerminalOutput] = useState<string[]>([]);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Simulate iframe loading
  useEffect(() => {
    if (previewUrl) {
      setIsLoading(true);
      const timer = setTimeout(() => setIsLoading(false), 1500);
      return () => clearTimeout(timer);
    }
  }, [previewUrl]);

  const handleRefresh = () => {
    if (onRefresh) {
      onRefresh();
    } else if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src;
    }
  };

  const handleOpenExternal = () => {
    if (previewUrl) {
      window.open(previewUrl, "_blank");
    }
  };

  const addTerminalOutput = (output: string) => {
    setTerminalOutput((prev) => [...prev, output]);
  };

  // Syntax highlighting for code (basic)
  const renderCode = (code: string, lang: string) => {
    return (
      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-auto max-h-[500px] text-sm">
        <code className={`language-${lang}`}>{code}</code>
      </pre>
    );
  };

  return (
    <Card className="w-full border-2 border-blue-200 dark:border-blue-800 bg-gradient-to-br from-blue-50 to-white dark:from-gray-900 dark:to-gray-800">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileCode className="h-5 w-5 text-blue-600" />
            <CardTitle className="text-lg">Live Code Preview</CardTitle>
            {live && (
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {previewUrl && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRefresh}
                  className="h-8"
                >
                  <RefreshCw className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleOpenExternal}
                  className="h-8"
                >
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </>
            )}
          </div>
        </div>
        <CardDescription>
          {projectName} {previewUrl && `• ${previewUrl}`}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="preview" className="flex items-center gap-2">
              <Eye className="h-4 w-4" />
              Preview
            </TabsTrigger>
            <TabsTrigger value="code" className="flex items-center gap-2">
              <Code className="h-4 w-4" />
              Code
            </TabsTrigger>
            <TabsTrigger value="terminal" className="flex items-center gap-2">
              <Terminal className="h-4 w-4" />
              Terminal
            </TabsTrigger>
          </TabsList>

          <TabsContent value="preview" className="mt-4">
            {previewUrl ? (
              <div className="relative w-full border-2 border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white">
                {isLoading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 z-10">
                    <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                  </div>
                )}
                <iframe
                  ref={iframeRef}
                  src={previewUrl}
                  className="w-full h-[500px]"
                  title={projectName}
                  sandbox="allow-scripts allow-same-origin allow-forms"
                  onLoad={() => setIsLoading(false)}
                />
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-[500px] border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg">
                <Eye className="h-12 w-12 text-gray-400 mb-4" />
                <p className="text-gray-500 dark:text-gray-400">No preview available</p>
                <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">
                  Start a preview server to see your app in action
                </p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="code" className="mt-4">
            {code ? (
              renderCode(code, language)
            ) : (
              <div className="flex flex-col items-center justify-center h-[500px] border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg">
                <Code className="h-12 w-12 text-gray-400 mb-4" />
                <p className="text-gray-500 dark:text-gray-400">No code to display</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="terminal" className="mt-4">
            <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm h-[500px] overflow-auto">
              {terminalOutput.length > 0 ? (
                terminalOutput.map((line, index) => (
                  <div key={index} className="mb-1">
                    <span className="text-gray-500">$ </span>
                    {line}
                  </div>
                ))
              ) : (
                <div className="text-gray-500">
                  <p>$ # Terminal output will appear here</p>
                  <p>$ # Commands from sandbox executions will be logged</p>
                  <span className="animate-pulse">█</span>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>

        {live && (
          <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div className="flex items-start gap-2">
              <div className="relative flex h-5 w-5 items-center justify-center">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                  Live Preview Active
                </p>
                <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                  This preview will automatically reload when code changes are detected
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Helper component for displaying multiple code files
export function MultiFileCodePreview({ files }: { files: CodeFile[] }) {
  const [selectedFile, setSelectedFile] = useState(0);

  if (!files || files.length === 0) {
    return null;
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <FileCode className="h-5 w-5" />
          Project Files
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2 mb-4 overflow-x-auto">
          {files.map((file, index) => (
            <Button
              key={index}
              variant={selectedFile === index ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedFile(index)}
              className="whitespace-nowrap"
            >
              {file.name}
            </Button>
          ))}
        </div>
        <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-auto max-h-[500px] text-sm">
          <code className={`language-${files[selectedFile].language}`}>
            {files[selectedFile].content}
          </code>
        </pre>
      </CardContent>
    </Card>
  );
}
