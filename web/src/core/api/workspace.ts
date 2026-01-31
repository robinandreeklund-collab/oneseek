// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { resolveServiceURL } from "./resolve-service-url";

export interface WorkspaceHistory {
  undo_count: number;
  redo_count: number;
}

export interface WorkspaceFileContent {
  status: "ok" | "missing";
  content?: string;
  truncated?: boolean;
  size?: number;
}

export interface WorkspaceDiff {
  status: "ok" | "missing";
  diff?: string;
  before?: string | null;
  after?: string | null;
  truncated?: boolean;
  operation?: string;
}

export interface WorkspaceRunResult {
  status: "success" | "error";
  mode?: "repl" | "subprocess";
  output?: string;
  stdout?: string;
  stderr?: string;
  return_code?: number;
  error?: string;
}

async function fetchWithFallback(url: string, options?: RequestInit) {
  try {
    return await fetch(url, options);
  } catch (error) {
    if (typeof window === "undefined") throw error;
    try {
      const parsed = new URL(url);
      const fallbackUrl = `${window.location.origin}${parsed.pathname}${parsed.search}`;
      return await fetch(fallbackUrl, options);
    } catch {
      throw error;
    }
  }
}

export async function fetchWorkspaceHistory(threadId: string) {
  const url = resolveServiceURL(
    `workspace/history?thread_id=${encodeURIComponent(threadId)}`,
  );
  const res = await fetchWithFallback(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch history: ${res.statusText}`);
  }
  return (await res.json()) as WorkspaceHistory;
}

export async function fetchWorkspaceFiles(threadId: string, maxFiles = 1000) {
  const url = resolveServiceURL(
    `workspace/files?thread_id=${encodeURIComponent(threadId)}&max_files=${maxFiles}`,
  );
  const res = await fetchWithFallback(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch files: ${res.statusText}`);
  }
  return (await res.json()) as { files: Array<Record<string, unknown>> };
}

export async function fetchWorkspaceFileContent(
  threadId: string,
  path: string,
) {
  const url = resolveServiceURL(
    `workspace/file?thread_id=${encodeURIComponent(threadId)}&path=${encodeURIComponent(path)}`,
  );
  const res = await fetchWithFallback(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch file: ${res.statusText}`);
  }
  return (await res.json()) as WorkspaceFileContent;
}

export async function fetchWorkspaceDiff(threadId: string, path: string) {
  const url = resolveServiceURL(
    `workspace/diff?thread_id=${encodeURIComponent(threadId)}&path=${encodeURIComponent(path)}`,
  );
  const res = await fetchWithFallback(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch diff: ${res.statusText}`);
  }
  return (await res.json()) as WorkspaceDiff;
}

export async function undoWorkspaceChange(threadId: string) {
  const url = resolveServiceURL("workspace/undo");
  const res = await fetchWithFallback(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId }),
  });
  if (!res.ok) {
    throw new Error(`Failed to undo: ${res.statusText}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

export async function redoWorkspaceChange(threadId: string) {
  const url = resolveServiceURL("workspace/redo");
  const res = await fetchWithFallback(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId }),
  });
  if (!res.ok) {
    throw new Error(`Failed to redo: ${res.statusText}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

export async function runWorkspaceFile(threadId: string, path: string) {
  const url = resolveServiceURL("workspace/run");
  const res = await fetchWithFallback(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, path }),
  });
  if (!res.ok) {
    throw new Error(`Failed to run file: ${res.statusText}`);
  }
  return (await res.json()) as WorkspaceRunResult;
}

export async function exportWorkspaceZip(threadId: string) {
  const url = resolveServiceURL(
    `workspace/export?thread_id=${encodeURIComponent(threadId)}`,
  );
  const res = await fetchWithFallback(url);
  if (!res.ok) {
    throw new Error(`Failed to export zip: ${res.statusText}`);
  }
  return res.blob();
}
