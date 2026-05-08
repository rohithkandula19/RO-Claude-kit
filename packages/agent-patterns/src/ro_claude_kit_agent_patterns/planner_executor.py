from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .base import DEFAULT_MODEL, make_client, text_from_response
from .react import ReActAgent
from .types import AgentResult, Step, Tool


class Plan(BaseModel):
    """Structured plan produced by the planner LLM."""

    goal: str
    steps: list[str]


class PlannerExecutorAgent(BaseModel):
    """Two-phase agent: planner emits a structured plan, executor runs it step-by-step.

    Pick this when:
    - The task has multiple distinct sub-tasks that benefit from upfront planning.
    - You want checkpoint/resume — completed steps survive a replan.
    - Replanning on failure beats retry-in-place.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    planner_system: str
    executor_system: str
    tools: list[Tool] = Field(default_factory=list)
    model: str = DEFAULT_MODEL
    max_replans: int = 1
    api_key: str | None = None

    def _make_plan(self, task: str, prior_failure: str | None) -> Plan:
        client = make_client(self.api_key)
        prompt = f"Task: {task}\n\n"
        if prior_failure:
            prompt += (
                f"A previous attempt failed: {prior_failure}\n"
                "Produce a revised plan that addresses the failure.\n\n"
            )
        prompt += (
            "Return your plan as a JSON object with two fields: 'goal' (string) "
            "and 'steps' (list of concise step descriptions). "
            "Wrap the JSON in <plan></plan> tags."
        )
        response = client.messages.create(
            model=self.model,
            system=self.planner_system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )
        text = text_from_response(response)
        match = re.search(r"<plan>(.*?)</plan>", text, re.DOTALL)
        if not match:
            raise ValueError(f"Planner did not emit <plan></plan>: {text[:200]}")
        try:
            return Plan.model_validate_json(match.group(1).strip())
        except ValidationError as exc:
            raise ValueError(f"Planner emitted invalid plan JSON: {exc}") from exc

    def run(self, task: str) -> AgentResult:
        trace: list[Step] = []
        completed: list[str] = []
        prior_failure: str | None = None

        for replan_idx in range(self.max_replans + 1):
            try:
                plan = self._make_plan(task, prior_failure)
            except Exception as exc:  # noqa: BLE001
                trace.append(Step(kind="error", content=f"plan failed: {exc}"))
                return AgentResult(
                    success=False,
                    output="",
                    iterations=replan_idx + 1,
                    trace=trace,
                    error=str(exc),
                )
            trace.append(Step(kind="plan", content=plan.model_dump()))

            remaining = plan.steps[len(completed):]
            executor = ReActAgent(
                system=self.executor_system,
                tools=self.tools,
                model=self.model,
                api_key=self.api_key,
            )

            failed = False
            for step in remaining:
                step_input = (
                    f"Goal: {plan.goal}\n"
                    f"Already completed: {completed or '(nothing)'}\n"
                    f"Now do this step: {step}"
                )
                step_result = executor.run(step_input)
                trace.extend(step_result.trace)
                if not step_result.success:
                    prior_failure = f"step '{step}' failed: {step_result.error}"
                    trace.append(Step(kind="error", content=prior_failure))
                    failed = True
                    break
                completed.append(step)

            if not failed:
                final = f"Goal '{plan.goal}' achieved across {len(completed)} steps."
                trace.append(Step(kind="final", content=final))
                return AgentResult(
                    success=True,
                    output=final,
                    iterations=replan_idx + 1,
                    trace=trace,
                )

        return AgentResult(
            success=False,
            output="",
            iterations=self.max_replans + 1,
            trace=trace,
            error=prior_failure or "all replans exhausted",
        )
