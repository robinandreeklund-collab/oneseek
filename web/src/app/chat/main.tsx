// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useStore } from "~/core/store";
import { cn } from "~/lib/utils";

import { CoderSidebar } from "./components/coder-sidebar";
import { DebateSidebar } from "./components/debate-sidebar";
import { MessagesBlock } from "./components/messages-block";
import { ResearchBlock } from "./components/research-block";

const SIDEBAR_MIN_WIDTH = 360;
const SIDEBAR_DEFAULT_WIDTH = 420;
const SIDEBAR_MAX_WIDTH = 960;

export default function Main() {
  const openResearchId = useStore((state) => state.openResearchId);
  const openCoderSessionId = useStore((state) => state.openCoderSessionId);
  const openDebateSessionId = useStore((state) => state.openDebateSessionId);
  const showSidebar =
    openResearchId !== null || openCoderSessionId !== null || openDebateSessionId !== null;

  const sidebarContent = useMemo(() => {
    if (openResearchId !== null) {
      return (
        <ResearchBlock
          className="h-full w-full pb-4 transition-all duration-300 ease-out"
          researchId={openResearchId}
        />
      );
    }
    if (openCoderSessionId !== null) {
      return (
        <CoderSidebar
          className="h-full w-full pb-4 transition-all duration-300 ease-out"
          sessionId={openCoderSessionId}
        />
      );
    }
    if (openDebateSessionId !== null) {
      return (
        <DebateSidebar
          className="h-full w-full pb-4 transition-all duration-300 ease-out"
          sessionId={openDebateSessionId}
        />
      );
    }
    return null;
  }, [openResearchId, openCoderSessionId, openDebateSessionId]);

  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT_WIDTH);
  const resizingRef = useRef(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(sidebarWidth);

  const handleResizeStart = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      resizingRef.current = true;
      startXRef.current = event.clientX;
      startWidthRef.current = sidebarWidth;
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [sidebarWidth],
  );

  useEffect(() => {
    if (!showSidebar) {
      return;
    }
    const handlePointerMove = (event: PointerEvent) => {
      if (!resizingRef.current) return;
      const delta = startXRef.current - event.clientX;
      const maxWidth = Math.min(
        SIDEBAR_MAX_WIDTH,
        Math.max(SIDEBAR_MIN_WIDTH, window.innerWidth - 360),
      );
      const nextWidth = Math.min(
        Math.max(startWidthRef.current + delta, SIDEBAR_MIN_WIDTH),
        maxWidth,
      );
      setSidebarWidth(nextWidth);
    };
    const handlePointerUp = () => {
      resizingRef.current = false;
    };
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [showSidebar]);

  return (
    <div
      className={cn(
        "grid h-full w-full gap-0 pl-4 pr-0 pt-12 pb-4",
        showSidebar ? "grid-cols-[minmax(0,1fr)_auto]" : "grid-cols-[minmax(0,1fr)]",
      )}
      style={{
        gridTemplateColumns: showSidebar
          ? `minmax(0,1fr) ${sidebarWidth}px`
          : "minmax(0,1fr)",
      }}
    >
      <MessagesBlock
        className={cn(
          "mx-auto w-full transition-all duration-300 ease-out",
          showSidebar ? "max-w-[720px]" : "max-w-[760px]",
        )}
      />
      {showSidebar && sidebarContent && (
        <div className="relative h-full pr-4">
          <div
            className="absolute left-0 top-0 h-full w-2 cursor-col-resize"
            onPointerDown={handleResizeStart}
            aria-label="Resize sidebar"
          >
            <span className="absolute left-0 top-0 h-full w-px bg-border/60" />
          </div>
          <div className="h-full pl-3">{sidebarContent}</div>
        </div>
      )}
    </div>
  );
}
