// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { ArrowLeftIcon, CheckIcon } from "@radix-ui/react-icons";
import Link from "next/link";
import { use, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "~/components/ui/button";

export default function EditPromptPage({
  params,
}: {
  params: Promise<{ path: string }>;
}) {
  const { path } = use(params);
  const decodedPath = decodeURIComponent(path);
  const [content, setContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async function loadPrompt() {
      try {
        const response = await fetch(
          `/api/admin/prompts/${encodeURIComponent(decodedPath)}`,
        );
        if (!response.ok) {
          throw new Error("Misslyckades att ladda prompt");
        }
        const data = await response.json();
        setContent(data.content);
        setOriginalContent(data.content);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ett fel uppstod");
      } finally {
        setLoading(false);
      }
    })();
  }, [decodedPath]);

  async function handleSave() {
    setSaving(true);
    try {
      const response = await fetch(
        `/api/admin/prompts/${encodeURIComponent(decodedPath)}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ content }),
        },
      );
      if (!response.ok) {
        throw new Error("Misslyckades att spara prompt");
      }
      setOriginalContent(content);
      toast.success("Prompt sparad!");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Ett fel uppstod");
    } finally {
      setSaving(false);
    }
  }

  const hasChanges = content !== originalContent;

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground">Laddar prompt...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <p className="text-destructive">{error}</p>
        <Button asChild variant="outline">
          <Link href="/admin/prompts">
            <ArrowLeftIcon className="mr-2 size-4" />
            Tillbaka till prompts
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button asChild variant="ghost" size="sm">
            <Link href="/admin/prompts">
              <ArrowLeftIcon className="mr-2 size-4" />
              Tillbaka
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{decodedPath}</h1>
            <p className="text-muted-foreground text-sm">
              Redigera promptinnehåll
            </p>
          </div>
        </div>
        <Button onClick={handleSave} disabled={!hasChanges || saving}>
          <CheckIcon className="mr-2 size-4" />
          {saving ? "Sparar..." : "Spara ändringar"}
        </Button>
      </div>

      <div className="flex-1">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="bg-background border-input h-full w-full resize-none rounded-lg border p-4 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="Skriv promptinnehåll här..."
        />
      </div>
    </div>
  );
}
