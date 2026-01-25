// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { FileTextIcon, Pencil1Icon } from "@radix-ui/react-icons";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "~/components/ui/button";

interface Prompt {
  name: string;
  path: string;
  locale?: string;
}

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPrompts() {
      try {
        const response = await fetch("/api/admin/prompts");
        if (!response.ok) {
          throw new Error("Misslyckades att ladda prompts");
        }
        const data = await response.json();
        setPrompts(data.prompts);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ett fel uppstod");
      } finally {
        setLoading(false);
      }
    }
    loadPrompts();
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground">Laddar prompts...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-destructive">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Prompts</h1>
        <p className="text-muted-foreground mt-2">
          Hantera och redigera alla systemprompts
        </p>
      </div>

      <div className="grid gap-4">
        {prompts.map((prompt) => (
          <div
            key={prompt.path}
            className="bg-card flex items-center justify-between rounded-lg border p-4"
          >
            <div className="flex items-center gap-3">
              <FileTextIcon className="text-muted-foreground size-5" />
              <div>
                <h3 className="font-medium">{prompt.name}</h3>
                {prompt.locale && (
                  <p className="text-muted-foreground text-xs">
                    Språk: {prompt.locale}
                  </p>
                )}
              </div>
            </div>
            <Button asChild size="sm" variant="outline">
              <Link href={`/admin/prompts/${encodeURIComponent(prompt.path)}`}>
                <Pencil1Icon className="mr-2 size-4" />
                Redigera
              </Link>
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
