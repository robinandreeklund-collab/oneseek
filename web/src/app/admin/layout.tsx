// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "~/components/deer-flow/logo";
import { Button } from "~/components/ui/button";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="flex h-screen w-screen flex-col">
      <header className="border-b">
        <div className="flex h-16 items-center justify-between px-6">
          <div className="flex items-center gap-6">
            <Logo />
            <span className="text-muted-foreground text-sm">Admin Panel</span>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href="/chat">Tillbaka till Chat</Link>
          </Button>
        </div>
      </header>
      <div className="flex flex-1 overflow-hidden">
        <aside className="border-r w-64 overflow-y-auto bg-muted/10">
          <nav className="space-y-1 p-4">
            <Link
              href="/admin"
              className={`block rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                pathname === "/admin"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted"
              }`}
            >
              Översikt
            </Link>
            <Link
              href="/admin/prompts"
              className={`block rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                pathname.startsWith("/admin/prompts")
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted"
              }`}
            >
              Prompts
            </Link>
          </nav>
        </aside>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
