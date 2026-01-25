// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

const PROMPTS_DIR = path.join(process.cwd(), "..", "backend", "deer_flow", "prompts");

interface PromptFile {
  name: string;
  path: string;
  locale?: string;
}

async function getPromptFiles(dir: string, baseDir: string = ""): Promise<PromptFile[]> {
  const files: PromptFile[] = [];
  const entries = await fs.readdir(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    const relativePath = baseDir ? path.join(baseDir, entry.name) : entry.name;

    if (entry.isDirectory()) {
      // Recursively get files from subdirectories
      const subFiles = await getPromptFiles(fullPath, relativePath);
      files.push(...subFiles);
    } else if (entry.isFile() && entry.name.endsWith(".md")) {
      // Extract locale from filename if present (e.g., coordinator.zh_CN.md)
      const match = entry.name.match(/^(.+)\.(zh_CN|en_US|sv_SE)\.md$/);
      if (match) {
        files.push({
          name: `${match[1]} (${match[2]})`,
          path: relativePath,
          locale: match[2],
        });
      } else {
        files.push({
          name: entry.name.replace(/\.md$/, ""),
          path: relativePath,
        });
      }
    }
  }

  return files;
}

export async function GET() {
  try {
    const prompts = await getPromptFiles(PROMPTS_DIR);
    return NextResponse.json({ prompts });
  } catch (error) {
    console.error("Error loading prompts:", error);
    return NextResponse.json(
      { error: "Failed to load prompts" },
      { status: 500 }
    );
  }
}
