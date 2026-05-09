"""OpenAI-compatible provider.

Works with anything exposing OpenAI's ``/chat/completions`` API:
- OpenAI itself (``base_url="https://api.openai.com/v1"``)
- Ollama (``base_url="http://localhost:11434/v1"``, no API key needed)
- Together (``base_url="https://api.together.xyz/v1"``)
- Groq (``base_url="https://api.groq.com/openai/v1"``)
- Fireworks (``base_url="https://api.fireworks.ai/inference/v1"``)
- vLLM, llama.cpp server, LM Studio (any local OpenAI-compat server)

Uses ``httpx`` directly — no ``openai`` SDK dependency.
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

from ..types import Tool
from .base import LLMProvider, LLMResponse, Message, ToolCall


OPENAI_BASE_URL = "https://api.openai.com/v1"
OLLAMA_BASE_URL = "http://localhost:11434/v1"


def _to_openai_messages(system: str, messages: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"role": "system", "content": system}] if system else []
    for m in messages:
        if m.role == "tool":
            out.append({
                "role": "tool",
                "tool_call_id": m.tool_call_id or "",
                "content": m.content,
            })
        elif m.role == "assistant":
            msg: dict[str, Any] = {"role": "assistant"}
            if m.content:
                msg["content"] = m.content
            if m.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in m.tool_calls
                ]
            if "content" not in msg:
                msg["content"] = ""
            out.append(msg)
        else:
            out.append({"role": "user", "content": m.content})
    return out


class OpenAICompatProvider(LLMProvider):
    """Calls any OpenAI-compatible ``/chat/completions`` endpoint."""

    model_config = LLMProvider.model_config

    model: str
    base_url: str = OPENAI_BASE_URL
    api_key: str | None = None
    timeout: float = 120.0
    extra_headers: dict[str, str] = {}

    def _resolve_api_key(self) -> str | None:
        if self.api_key:
            return self.api_key
        return os.environ.get("OPENAI_API_KEY")

    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[Tool],
        max_tokens: int = 4096,
    ) -> LLMResponse:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": _to_openai_messages(system, messages),
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in tools
            ]

        headers: dict[str, str] = {"Content-Type": "application/json", **self.extra_headers}
        key = self._resolve_api_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                json=body,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        msg = choice["message"]
        text = (msg.get("content") or "").strip()

        tool_calls: list[ToolCall] = []
        for tc in msg.get("tool_calls") or []:
            args_raw = tc.get("function", {}).get("arguments", "{}")
            if isinstance(args_raw, str):
                try:
                    args = json.loads(args_raw)
                except json.JSONDecodeError:
                    args = {}
            else:
                args = args_raw or {}
            tool_calls.append(ToolCall(
                id=tc.get("id", ""),
                name=tc.get("function", {}).get("name", ""),
                arguments=args,
            ))

        finish = choice.get("finish_reason") or "end_turn"
        stop_reason = "tool_use" if tool_calls else (
            "end_turn" if finish in ("stop", "end_turn") else finish
        )

        usage = data.get("usage") or {}
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage={
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            },
        )


class OllamaProvider(OpenAICompatProvider):
    """Convenience subclass — runs against a local Ollama server, no API key needed.

    Default base_url is the Ollama default (``http://localhost:11434/v1``). Override
    with ``OLLAMA_BASE_URL`` env var or by passing ``base_url=...``.
    """

    base_url: str = os.environ.get("OLLAMA_BASE_URL") or OLLAMA_BASE_URL
    api_key: str | None = "ollama"  # ollama ignores auth but openai-format requires *something*
