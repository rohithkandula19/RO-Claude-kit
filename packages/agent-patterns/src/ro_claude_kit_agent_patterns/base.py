from __future__ import annotations

import json
from typing import Any

import anthropic

from .types import Tool

DEFAULT_MODEL = "claude-sonnet-4-6"


def make_client(api_key: str | None = None) -> anthropic.Anthropic:
    """Build an Anthropic client. ``api_key=None`` falls back to ``ANTHROPIC_API_KEY``."""
    return anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()


def execute_tool_call(tool: Tool, args: dict[str, Any]) -> tuple[str, bool]:
    """Run a tool. Returns ``(result_str, is_error)``.

    Tool handlers may return any JSON-serializable value; non-strings are dumped to JSON.
    Exceptions are caught and turned into error strings so the agent can recover.
    """
    try:
        out = tool.handler(**args) if isinstance(args, dict) else tool.handler(args)
    except Exception as exc:  # noqa: BLE001 — agent must see the error to recover
        return f"{type(exc).__name__}: {exc}", True
    if isinstance(out, str):
        return out, False
    return json.dumps(out, default=str), False


def text_from_response(response: Any) -> str:
    """Extract assistant text from an Anthropic response, ignoring tool_use blocks."""
    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()


def has_tool_use(response: Any) -> bool:
    return any(getattr(b, "type", None) == "tool_use" for b in response.content)
