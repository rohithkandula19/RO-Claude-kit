"""In-memory provider for tests. Returns a queue of canned ``LLMResponse``s in order."""
from __future__ import annotations

from pydantic import Field, PrivateAttr

from ..types import Tool
from .base import LLMProvider, LLMResponse, Message


class FakeProvider(LLMProvider):
    """Yields ``responses`` in order on successive ``complete()`` calls.

    Records every call's ``messages`` and ``tools`` for assertions in tests.
    """

    model: str = "fake-model"
    responses: list[LLMResponse] = Field(default_factory=list)

    _calls: list[dict] = PrivateAttr(default_factory=list)
    _index: int = PrivateAttr(default=0)

    @property
    def calls(self) -> list[dict]:
        return self._calls

    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[Tool],
        max_tokens: int = 4096,
    ) -> LLMResponse:
        self._calls.append({
            "system": system,
            "messages": [m.model_dump() for m in messages],
            "tool_names": [t.name for t in tools],
            "max_tokens": max_tokens,
        })
        if self._index >= len(self.responses):
            raise RuntimeError(
                f"FakeProvider exhausted: {self._index + 1} calls but only "
                f"{len(self.responses)} responses queued"
            )
        response = self.responses[self._index]
        self._index += 1
        return response
