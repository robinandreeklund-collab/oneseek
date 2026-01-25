// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { FileTextIcon, SettingsIcon } from "@radix-ui/react-icons";
import Link from "next/link";

export default function AdminPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Admin Panel</h1>
        <p className="text-muted-foreground mt-2">
          Hantera systemets inställningar och konfiguration
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Link
          href="/admin/prompts"
          className="bg-card hover:bg-accent group flex flex-col gap-4 rounded-lg border p-6 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 text-primary flex size-12 items-center justify-center rounded-lg">
              <FileTextIcon className="size-6" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Prompt-hantering</h2>
              <p className="text-muted-foreground text-sm">
                Redigera och hantera alla systemprompts
              </p>
            </div>
          </div>
        </Link>

        <div className="bg-card flex flex-col gap-4 rounded-lg border p-6 opacity-50">
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 text-primary flex size-12 items-center justify-center rounded-lg">
              <SettingsIcon className="size-6" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Systeminställningar</h2>
              <p className="text-muted-foreground text-sm">
                Kommer snart...
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
