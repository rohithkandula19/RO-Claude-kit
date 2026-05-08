from __future__ import annotations

from unittest.mock import MagicMock, patch

from ro_claude_kit_agent_patterns import ReflexionAgent

from conftest import make_block, make_response


def test_reflexion_accepts_first_attempt() -> None:
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        make_response("end_turn", [make_block("text", text="answer one")]),
        make_response(
            "end_turn",
            [make_block("text", text="ACCEPTABLE: yes\nFEEDBACK: looks great")],
        ),
    ]
    with patch("ro_claude_kit_agent_patterns.reflexion.make_client", return_value=fake_client), \
         patch("ro_claude_kit_agent_patterns.react.make_client", return_value=fake_client):
        agent = ReflexionAgent(agent_system="do", critic_system="critique")
        result = agent.run("do the thing")

    assert result.success
    assert result.iterations == 1
    refl = [s for s in result.trace if s.kind == "reflection"]
    assert refl and refl[0].content["is_acceptable"] is True


def test_reflexion_retries_then_accepts() -> None:
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        make_response("end_turn", [make_block("text", text="weak answer")]),
        make_response("end_turn", [make_block("text", text="ACCEPTABLE: no\nFEEDBACK: be more specific")]),
        make_response("end_turn", [make_block("text", text="strong answer")]),
        make_response("end_turn", [make_block("text", text="ACCEPTABLE: yes\nFEEDBACK: nice")]),
    ]
    with patch("ro_claude_kit_agent_patterns.reflexion.make_client", return_value=fake_client), \
         patch("ro_claude_kit_agent_patterns.react.make_client", return_value=fake_client):
        agent = ReflexionAgent(agent_system="do", critic_system="critique", max_attempts=3)
        result = agent.run("do the thing")

    assert result.success
    assert result.iterations == 2
    assert "strong" in result.output


def test_reflexion_exhausts_attempts() -> None:
    fake_client = MagicMock()
    # Always rejects
    fake_client.messages.create.side_effect = [
        make_response("end_turn", [make_block("text", text="weak")]),
        make_response("end_turn", [make_block("text", text="ACCEPTABLE: no\nFEEDBACK: try again")]),
    ] * 3
    with patch("ro_claude_kit_agent_patterns.reflexion.make_client", return_value=fake_client), \
         patch("ro_claude_kit_agent_patterns.react.make_client", return_value=fake_client):
        agent = ReflexionAgent(agent_system="do", critic_system="critique", max_attempts=2)
        result = agent.run("do the thing")

    assert not result.success
    assert "max_attempts" in (result.error or "")
