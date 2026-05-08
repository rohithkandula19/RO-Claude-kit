"""Production-grade agent patterns for Claude.

Four patterns shipped:

- ``ReActAgent`` — Reason-Act-Observe loop with tool retry and iteration cap.
- ``PlannerExecutorAgent`` — Plan-then-execute with checkpoint/resume.
- ``SupervisorAgent`` — Orchestrator that delegates to specialist sub-agents.
- ``ReflexionAgent`` — Act → critique → retry-with-feedback.

Plus shared types: ``Tool``, ``AgentResult``, ``Step``.
"""
from .types import AgentResult, Step, Tool
from .react import ReActAgent
from .planner_executor import Plan, PlannerExecutorAgent
from .supervisor import SubAgent, SupervisorAgent
from .reflexion import Critique, ReflexionAgent

__all__ = [
    "AgentResult",
    "Critique",
    "Plan",
    "PlannerExecutorAgent",
    "ReActAgent",
    "ReflexionAgent",
    "Step",
    "SubAgent",
    "SupervisorAgent",
    "Tool",
]
