from __future__ import annotations

from unittest.mock import MagicMock, patch

from ro_claude_kit_agent_patterns import SubAgent, SupervisorAgent

from conftest import make_block, make_response


def test_supervisor_delegates_and_synthesizes() -> None:
    """Orchestrator delegates to a sub-agent, then returns a synthesized answer."""
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        make_response(
            "tool_use",
            [make_block("tool_use", name="delegate_to_researcher", input={"query": "what is 2+2?"}, id="t1")],
        ),
        make_response("end_turn", [make_block("text", text="four")]),
        make_response("end_turn", [make_block("text", text="The researcher says four.")]),
    ]

    with patch("ro_claude_kit_agent_patterns.react.make_client", return_value=fake_client):
        researcher = SubAgent(
            name="researcher",
            description="finds facts",
            system="research stuff",
        )
        agent = SupervisorAgent(
            system="orchestrate",
            sub_agents=[researcher],
        )
        result = agent.run("ask the researcher what 2+2 is")

    assert result.success
    assert "four" in result.output.lower()
    sub_results = [s for s in result.trace if s.kind == "tool_result" and "sub_agent" in str(s.content)]
    assert sub_results
