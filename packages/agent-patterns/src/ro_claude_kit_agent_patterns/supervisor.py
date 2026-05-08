from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .base import DEFAULT_MODEL
from .react import ReActAgent
from .types import AgentResult, Step, Tool


class SubAgent(BaseModel):
    """A specialist sub-agent the supervisor can delegate to."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    system: str
    tools: list[Tool] = Field(default_factory=list)
    model: str = DEFAULT_MODEL
    max_iterations: int = 10


class SupervisorAgent(BaseModel):
    """Orchestrator that delegates work to specialist sub-agents.

    Each sub-agent is exposed to the orchestrator as a ``delegate_to_<name>`` tool.
    When a sub-agent fails, the failure is surfaced as a tool error rather than
    crashing the orchestrator — failure isolation by construction.

    Pick this when:
    - The task has heterogeneous sub-tasks with different tool sets / personas.
    - You want failure isolation (one sub-agent erroring doesn't kill the run).
    - Different sub-tasks benefit from different system prompts or models.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    system: str
    sub_agents: list[SubAgent]
    model: str = DEFAULT_MODEL
    max_iterations: int = 10
    api_key: str | None = None

    def _delegate_tool(self, sub: SubAgent, parent_trace: list[Step]) -> Tool:
        def handler(query: str) -> str:
            agent = ReActAgent(
                system=sub.system,
                tools=sub.tools,
                model=sub.model,
                max_iterations=sub.max_iterations,
                api_key=self.api_key,
            )
            try:
                result = agent.run(query)
            except Exception as exc:  # noqa: BLE001 — failure must not propagate
                parent_trace.append(
                    Step(kind="error", content=f"sub-agent {sub.name} crashed: {exc}")
                )
                return f"SUB_AGENT_ERROR: {exc}"
            parent_trace.append(Step(
                kind="tool_result",
                content={
                    "sub_agent": sub.name,
                    "success": result.success,
                    "output": result.output,
                },
                metadata={"sub_iterations": result.iterations},
            ))
            if not result.success:
                return f"SUB_AGENT_FAILED: {result.error}\nPartial output: {result.output}"
            return result.output

        return Tool(
            name=f"delegate_to_{sub.name}",
            description=f"Delegate a task to {sub.name}. {sub.description}",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The task or question for the sub-agent.",
                    },
                },
                "required": ["query"],
            },
            handler=handler,
        )

    def run(self, task: str) -> AgentResult:
        parent_trace: list[Step] = []
        delegate_tools = [self._delegate_tool(sub, parent_trace) for sub in self.sub_agents]

        supervisor_system = (
            f"{self.system}\n\n"
            "You orchestrate specialist sub-agents. Delegate via the delegate_to_<name> tools, "
            "then synthesize their outputs into a final answer."
        )
        orchestrator = ReActAgent(
            system=supervisor_system,
            tools=delegate_tools,
            model=self.model,
            max_iterations=self.max_iterations,
            api_key=self.api_key,
        )
        result = orchestrator.run(task)
        return AgentResult(
            success=result.success,
            output=result.output,
            iterations=result.iterations,
            trace=parent_trace + result.trace,
            error=result.error,
            usage=result.usage,
        )
