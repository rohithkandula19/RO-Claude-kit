from __future__ import annotations

from unittest.mock import MagicMock, patch

from ro_claude_kit_agent_patterns import ReActAgent, Tool

from .conftest import make_block, make_response


def test_react_no_tools_returns_immediately() -> None:
    fake_client = MagicMock()
    fake_client.messages.create.return_value = make_response(
        "end_turn", [make_block("text", text="Hello!")]
    )
    with patch("ro_claude_kit_agent_patterns.react.make_client", return_value=fake_client):
        result = ReActAgent(system="be helpful").run("hi")

    assert result.success
    assert "Hello" in result.output
    assert result.iterations == 1
    assert result.usage["input_tokens"] == 10


def test_react_calls_tool_then_finishes() -> None:
    calls: list[str] = []

    def calc(expression: str) -> str:
        calls.append(expression)
        return "42"

    tool = Tool(
        name="calc",
        description="evaluate math",
        input_schema={"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
        handler=calc,
    )

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        make_response("tool_use", [make_block("tool_use", name="calc", input={"expression": "6*7"}, id="t1")]),
        make_response("end_turn", [make_block("text", text="The answer is 42.")]),
    ]
    with patch("ro_claude_kit_agent_patterns.react.make_client", return_value=fake_client):
        result = ReActAgent(system="...", tools=[tool]).run("what is 6*7?")

    assert result.success
    assert calls == ["6*7"]
    assert "42" in result.output
    kinds = [s.kind for s in result.trace]
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    assert "final" in kinds


def test_react_iteration_cap() -> None:
    """Tool-use loop that never ends should fail with iteration cap."""
    tool = Tool(
        name="loop",
        description="loops",
        input_schema={"type": "object", "properties": {}},
        handler=lambda: "more",
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = make_response(
        "tool_use", [make_block("tool_use", name="loop", input={}, id="t")]
    )
    with patch("ro_claude_kit_agent_patterns.react.make_client", return_value=fake_client):
        result = ReActAgent(system="...", tools=[tool], max_iterations=3).run("loop forever")

    assert not result.success
    assert "max_iterations" in (result.error or "")
    assert result.iterations == 3


def test_react_unknown_tool_does_not_crash() -> None:
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        make_response("tool_use", [make_block("tool_use", name="ghost", input={}, id="t1")]),
        make_response("end_turn", [make_block("text", text="ok done")]),
    ]
    with patch("ro_claude_kit_agent_patterns.react.make_client", return_value=fake_client):
        result = ReActAgent(system="...", tools=[]).run("call ghost")

    assert result.success
    errors = [s for s in result.trace if s.kind == "error"]
    assert any("ghost" in str(s.content) for s in errors)


def test_react_tool_exception_surfaces_as_error() -> None:
    def boom(**_: object) -> str:
        raise RuntimeError("kaboom")

    tool = Tool(
        name="boom",
        description="explodes",
        input_schema={"type": "object", "properties": {}},
        handler=boom,
    )
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        make_response("tool_use", [make_block("tool_use", name="boom", input={}, id="t1")]),
        make_response("end_turn", [make_block("text", text="recovered")]),
    ]
    with patch("ro_claude_kit_agent_patterns.react.make_client", return_value=fake_client):
        result = ReActAgent(system="...", tools=[tool]).run("call boom")

    assert result.success
    tool_results = [s for s in result.trace if s.kind == "tool_result"]
    assert tool_results and tool_results[0].content["is_error"] is True
    assert "kaboom" in tool_results[0].content["result"]
