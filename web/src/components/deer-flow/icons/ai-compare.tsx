// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

export function AiCompare(
  props: React.SVGProps<SVGSVGElement> & { size?: number },
) {
  const size = props.size ?? 16;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      <path
        d="M12 3V21M12 3L8 7M12 3L16 7M8 14L4 18H8L12 14M16 14L20 18H16L12 14"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="6" cy="18" r="2" stroke="currentColor" strokeWidth="2" fill="none"/>
      <circle cx="18" cy="18" r="2" stroke="currentColor" strokeWidth="2" fill="none"/>
      <path d="M3 21H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  );
}
