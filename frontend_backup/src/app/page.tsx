"use client";

import { useState, useEffect } from "react";
import { ChatInterface } from "@/components/ChatInterface";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function Home() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <main className="flex min-h-screen flex-col">
      <header className="border-b border-border bg-card">
        <div className="container flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold">OneSeek.ai</h1>
            <span className="text-xs text-muted-foreground">MVP v0.2</span>
          </div>
          <ThemeToggle />
        </div>
      </header>
      <div className="flex-1">
        <ChatInterface />
      </div>
    </main>
  );
}
