"""Provider-neutral message/tool-call types used by every agent pattern."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..types import Tool


class ToolCall(BaseModel):
    """A model-emitted call to a tool."""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """Provider-neutral conversation turn.

    Roles:
    - ``user`` — input from the user.
    - ``assistant`` — model output (text + optional tool_calls).
    - ``tool`` — tool execution result, addressed to a specific ``tool_call_id``.
    """

    role: Literal["user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None  # tool name (only for role=tool)
    is_error: bool = False


class LLMResponse(BaseModel):
    """One response from a provider."""

    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    stop_reason: str = "end_turn"  # "end_turn" | "tool_use" | "max_tokens" | "other"
    usage: dict[str, int] = Field(default_factory=dict)


class LLMProvider(BaseModel):
    """Base class. Subclass and implement ``complete``.

    The agent loop calls ``complete`` once per iteration, passing the full
    conversation so far. The provider is responsible for translating the neutral
    ``Message`` list to the provider's native wire format.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str

    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[Tool],
        max_tokens: int = 4096,
    ) -> LLMResponse:
        raise NotImplementedError
