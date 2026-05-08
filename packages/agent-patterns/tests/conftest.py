from __future__ import annotations

from types import SimpleNamespace
from typing import Any


def make_block(kind: str, **kwargs: Any) -> SimpleNamespace:
    """Build a fake Anthropic content block."""
    return SimpleNamespace(type=kind, **kwargs)


def make_response(stop_reason: str, blocks: list[SimpleNamespace]) -> SimpleNamespace:
    """Build a fake Anthropic Messages.create response."""
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=blocks,
        usage=SimpleNamespace(input_tokens=10, output_tokens=20),
    )
