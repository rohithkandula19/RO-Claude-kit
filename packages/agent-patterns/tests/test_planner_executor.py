from __future__ import annotations

from unittest.mock import MagicMock, patch

from ro_claude_kit_agent_patterns import PlannerExecutorAgent

from .conftest import make_block, make_response


def test_planner_executor_happy_path() -> None:
    plan_text = (
        "Here is the plan:\n"
        "<plan>\n"
        '{"goal": "greet user", "steps": ["say hello"]}\n'
        "</plan>"
    )
    planner_response = make_response("end_turn", [make_block("text", text=plan_text)])
    executor_response = make_response("end_turn", [make_block("text", text="hello!")])

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [planner_response, executor_response]

    with patch("ro_claude_kit_agent_patterns.planner_executor.make_client", return_value=fake_client), \
         patch("ro_claude_kit_agent_patterns.react.make_client", return_value=fake_client):
        agent = PlannerExecutorAgent(
            planner_system="plan things",
            executor_system="execute things",
        )
        result = agent.run("greet the user")

    assert result.success
    plan_steps = [s for s in result.trace if s.kind == "plan"]
    assert plan_steps and plan_steps[0].content["goal"] == "greet user"


def test_planner_executor_missing_plan_tags_fails_clearly() -> None:
    bad_response = make_response("end_turn", [make_block("text", text="here you go")])
    fake_client = MagicMock()
    fake_client.messages.create.return_value = bad_response

    with patch("ro_claude_kit_agent_patterns.planner_executor.make_client", return_value=fake_client):
        agent = PlannerExecutorAgent(
            planner_system="plan",
            executor_system="exec",
            max_replans=0,
        )
        result = agent.run("do something")

    assert not result.success
    assert "plan" in (result.error or "").lower()
