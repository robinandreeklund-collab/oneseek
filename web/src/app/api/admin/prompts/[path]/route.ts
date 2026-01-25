// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import fs from "fs/promises";
import path from "path";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

// Note: Backend directory structure uses 'deer_flow' internally
// Frontend displays 'Oneseek' branding
const PROMPTS_DIR = path.join(process.cwd(), "..", "backend", "deer_flow", "prompts");

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string }> }
) {
  try {
    const { path: promptPath } = await params;
    const decodedPath = decodeURIComponent(promptPath);
    const fullPath = path.join(PROMPTS_DIR, decodedPath);

    // Security check: ensure the path is within PROMPTS_DIR
    const resolvedPath = path.resolve(fullPath);
    const resolvedPromptsDir = path.resolve(PROMPTS_DIR);
    if (!resolvedPath.startsWith(resolvedPromptsDir)) {
      return NextResponse.json(
        { error: "Invalid path" },
        { status: 400 }
      );
    }

    const content = await fs.readFile(fullPath, "utf-8");
    return NextResponse.json({ content, path: decodedPath });
  } catch (error) {
    console.error("Error loading prompt:", error);
    return NextResponse.json(
      { error: "Failed to load prompt" },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string }> }
) {
  try {
    const { path: promptPath } = await params;
    const decodedPath = decodeURIComponent(promptPath);
    const fullPath = path.join(PROMPTS_DIR, decodedPath);

    // Security check: ensure the path is within PROMPTS_DIR
    const resolvedPath = path.resolve(fullPath);
    const resolvedPromptsDir = path.resolve(PROMPTS_DIR);
    if (!resolvedPath.startsWith(resolvedPromptsDir)) {
      return NextResponse.json(
        { error: "Invalid path" },
        { status: 400 }
      );
    }

    const body = await request.json();
    const { content } = body;

    if (typeof content !== "string") {
      return NextResponse.json(
        { error: "Invalid content" },
        { status: 400 }
      );
    }

    await fs.writeFile(fullPath, content, "utf-8");
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error saving prompt:", error);
    return NextResponse.json(
      { error: "Failed to save prompt" },
      { status: 500 }
    );
  }
}
