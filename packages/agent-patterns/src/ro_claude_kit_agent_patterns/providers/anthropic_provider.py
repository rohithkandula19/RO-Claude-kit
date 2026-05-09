"""Anthropic Claude provider — the default."""
from __future__ import annotations

from typing import Any

import anthropic

from ..types import Tool
from .base import LLMProvider, LLMResponse, Message, ToolCall


def _to_anthropic_messages(messages: list[Message]) -> list[dict[str, Any]]:
    """Translate neutral messages to Anthropic's wire format.

    Anthropic batches all tool_result blocks for one assistant turn into a single
    user message. So we walk the neutral list and merge consecutive ``tool``
    messages into one user message with multiple ``tool_result`` blocks.
    """
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(messages):
        m = messages[i]
        if m.role == "tool":
            blocks: list[dict[str, Any]] = []
            while i < len(messages) and messages[i].role == "tool":
                tm = messages[i]
                blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tm.tool_call_id,
                    "content": tm.content,
                    "is_error": tm.is_error,
                })
                i += 1
            out.append({"role": "user", "content": blocks})
            continue

        if m.role == "assistant":
            content_blocks: list[dict[str, Any]] = []
            if m.content:
                content_blocks.append({"type": "text", "text": m.content})
            for tc in m.tool_calls:
                content_blocks.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                })
            out.append({
                "role": "assistant",
                "content": content_blocks if content_blocks else m.content,
            })
        else:  # user
            out.append({"role": "user", "content": m.content})
        i += 1
    return out


class AnthropicProvider(LLMProvider):
    """Calls the Anthropic Messages API."""

    model: str = "claude-sonnet-4-6"
    api_key: str | None = None

    def _client(self) -> anthropic.Anthropic:
        return anthropic.Anthropic(api_key=self.api_key) if self.api_key else anthropic.Anthropic()

    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[Tool],
        max_tokens: int = 4096,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "system": system,
            "messages": _to_anthropic_messages(messages),
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = [t.to_anthropic() for t in tools]

        response = self._client().messages.create(**kwargs)

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text_parts.append(block.text)
            elif block_type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input or {},
                ))

        return LLMResponse(
            text="\n".join(text_parts).strip(),
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )
