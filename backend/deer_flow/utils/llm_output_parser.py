import json
import logging
import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from backend.deer_flow.utils.json_utils import repair_json_output

logger = logging.getLogger(__name__)

_THINK_TAG_PATTERNS = [
    re.compile(r"<think>(.*?)</think>", re.I | re.S),
    re.compile(r"<thinking>(.*?)</thinking>", re.I | re.S),
    re.compile(r"\[(think|thinking)\](.*?)\[/\1\]", re.I | re.S),
]
_TOOL_CALL_TAG_PATTERNS = [
    re.compile(r"<tool_call>(.*?)</tool_call>", re.I | re.S),
    re.compile(r"\[tool_call\](.*?)\[/tool_call\]", re.I | re.S),
]


@dataclass
class ParsedLlmOutput:
    content: str
    reasoning_content: str | None
    tool_calls: list[dict[str, Any]]


def _extract_json_substring(content: str) -> str | None:
    if not content:
        return None
    start_positions = [pos for pos in (content.find("{"), content.find("[")) if pos != -1]
    if not start_positions:
        return None
    start = min(start_positions)
    return content[start:].strip()


def _parse_tool_payload(payload_text: str) -> dict[str, Any] | None:
    if not payload_text:
        return None
    try:
        return json.loads(repair_json_output(payload_text))
    except Exception:
        extracted = _extract_json_substring(payload_text)
        if extracted:
            try:
                return json.loads(repair_json_output(extracted))
            except Exception:
                return None
        return None


def _coerce_tool_args(raw_args: Any) -> Any:
    if isinstance(raw_args, str):
        try:
            return json.loads(repair_json_output(raw_args))
        except Exception:
            return {"_raw": raw_args}
    return raw_args if raw_args is not None else {}


def extract_thinking_blocks(content: str) -> tuple[str | None, str]:
    if not content:
        return None, content

    cleaned = content
    reasoning_parts: list[str] = []
    for pattern in _THINK_TAG_PATTERNS:
        matches = list(pattern.finditer(cleaned))
        if not matches:
            continue
        for match in matches:
            if match.lastindex and match.lastindex >= 2:
                reasoning_text = match.group(2)
            else:
                reasoning_text = match.group(1)
            reasoning_text = (reasoning_text or "").strip()
            if reasoning_text:
                reasoning_parts.append(reasoning_text)
        cleaned = pattern.sub("", cleaned)

    reasoning_content = "\n\n".join(reasoning_parts).strip() if reasoning_parts else None
    return reasoning_content, cleaned.strip()


def extract_tool_calls(content: str) -> tuple[list[dict[str, Any]], str]:
    if not content:
        return [], content

    tool_calls: list[dict[str, Any]] = []
    cleaned = content

    for pattern in _TOOL_CALL_TAG_PATTERNS:
        def _replace(match: re.Match[str]) -> str:
            payload_text = match.group(1).strip()
            payload = _parse_tool_payload(payload_text)
            if not payload or not isinstance(payload, dict):
                logger.warning("Failed to parse tool_call payload: %s", payload_text[:200])
                return ""

            name = payload.get("name") or payload.get("tool") or payload.get("tool_name")
            if not name:
                logger.warning("Tool call payload missing name: %s", payload_text[:200])
                return ""

            raw_args = payload.get("arguments", payload.get("args", {}))
            args = _coerce_tool_args(raw_args)
            tool_call_id = payload.get("id") or payload.get("tool_call_id") or uuid4().hex
            tool_calls.append(
                {
                    "id": tool_call_id,
                    "name": name,
                    "args": args,
                }
            )
            return ""

        cleaned = pattern.sub(_replace, cleaned)

    return tool_calls, cleaned.strip()


def parse_llm_output(content: str) -> ParsedLlmOutput:
    if not content:
        return ParsedLlmOutput(content="", reasoning_content=None, tool_calls=[])

    reasoning_content, without_thinking = extract_thinking_blocks(content)
    tool_calls, without_tool_calls = extract_tool_calls(without_thinking)
    cleaned = without_tool_calls.strip()

    return ParsedLlmOutput(
        content=cleaned,
        reasoning_content=reasoning_content,
        tool_calls=tool_calls,
    )
