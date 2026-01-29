// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { cn } from "~/lib/utils";

import { Welcome } from "./welcome";

export function ConversationStarter({
  className,
  onSend,
}: {
  className?: string;
  onSend?: (message: string) => void;
}) {
  return (
    <div
      className={cn(
        "flex h-full flex-col items-center justify-center overflow-auto",
        className,
      )}
    >
      <div className="pointer-events-none flex items-center justify-center">
        <Welcome className="pointer-events-auto w-[75%]" />
      </div>
    </div>
  );
}
