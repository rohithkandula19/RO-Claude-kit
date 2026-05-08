from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .base import (
    DEFAULT_MODEL,
    execute_tool_call,
    has_tool_use,
    make_client,
    text_from_response,
)
from .types import AgentResult, Step, Tool


class ReActAgent(BaseModel):
    """ReAct agent with reflection text, tool error tolerance, and an iteration cap.

    The classic Reason-Act-Observe loop. Pick this when:
    - The task fits a single execution thread (no parallel sub-agents needed).
    - Tools are reliable enough that one retry on failure is sufficient.
    - You want the simplest pattern that still survives prod.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    system: str
    tools: list[Tool] = Field(default_factory=list)
    model: str = DEFAULT_MODEL
    max_iterations: int = 10
    max_tokens: int = 4096
    api_key: str | None = None

    def run(self, user_message: str) -> AgentResult:
        client = make_client(self.api_key)
        tools_by_name = {t.name: t for t in self.tools}

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
        trace: list[Step] = []
        usage = {"input_tokens": 0, "output_tokens": 0}

        for i in range(self.max_iterations):
            kwargs: dict[str, Any] = {
                "model": self.model,
                "system": self.system,
                "messages": messages,
                "max_tokens": self.max_tokens,
            }
            if self.tools:
                kwargs["tools"] = [t.to_anthropic() for t in self.tools]

            response = client.messages.create(**kwargs)
            usage["input_tokens"] += response.usage.input_tokens
            usage["output_tokens"] += response.usage.output_tokens

            reasoning = text_from_response(response)
            if reasoning:
                trace.append(Step(kind="thought", content=reasoning))

            if not has_tool_use(response):
                final = reasoning or "(no output)"
                trace.append(Step(kind="final", content=final))
                return AgentResult(
                    success=True,
                    output=final,
                    iterations=i + 1,
                    trace=trace,
                    usage=usage,
                )

            messages.append({"role": "assistant", "content": response.content})
            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                name: str = block.name
                args: dict[str, Any] = block.input or {}
                trace.append(Step(kind="tool_call", content={"name": name, "input": args}))

                tool = tools_by_name.get(name)
                if tool is None:
                    err = f"tool '{name}' is not registered"
                    trace.append(Step(kind="error", content=err))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"ERROR: {err}",
                        "is_error": True,
                    })
                    continue

                result, is_err = execute_tool_call(tool, args)
                trace.append(Step(
                    kind="tool_result",
                    content={"name": name, "result": result, "is_error": is_err},
                ))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                    "is_error": is_err,
                })

            messages.append({"role": "user", "content": tool_results})

        return AgentResult(
            success=False,
            output="(iteration cap reached)",
            iterations=self.max_iterations,
            trace=trace,
            error=f"hit max_iterations={self.max_iterations}",
            usage=usage,
        )
