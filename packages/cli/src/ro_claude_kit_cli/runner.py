"""Agent execution glue — wraps ReActAgent + the configured tool set."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

from ro_claude_kit_agent_patterns import ReActAgent, Tool
from ro_claude_kit_hardening import InjectionScanner

from .config import CSKConfig
from .tools import build_tools


SYSTEM_PROMPT_TEMPLATE = """You are csk — a CLI agent that helps a startup founder query their own data.
You have read-only tools for the configured services. You do NOT have write access; refuse politely
if asked to mutate state.

When you call a tool, prefer specific filters (customer_id, state, etc.) over listing everything.
Synthesize a tight answer; cite the data you used. If the user's question can't be answered with the
tools you have, say so honestly.

Configured services: {services}.
"""


@dataclass
class AgentResultRich:
    success: bool
    output: str
    iterations: int
    trace: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    demo_mode: bool = False


def _serialize_trace(trace: list) -> list[dict[str, Any]]:
    return [{"kind": s.kind, "content": s.content} for s in trace]


def _build_agent(config: CSKConfig, tools: list[Tool]) -> ReActAgent:
    services = config.configured_services()
    system = SYSTEM_PROMPT_TEMPLATE.format(services=", ".join(services) or "none")
    api_key = config.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
    return ReActAgent(
        system=system,
        tools=tools,
        model=config.model,
        max_iterations=8,
        api_key=api_key,
    )


def run_ask(config: CSKConfig, question: str, *, console: Console | None = None) -> AgentResultRich:
    """One-shot agent invocation. Shows a spinner while Claude is thinking (when console given)."""
    scan = InjectionScanner().scan(question)
    if scan.flagged:
        return AgentResultRich(
            success=False,
            output="[blocked] your question was flagged as a potential prompt-injection attempt.",
            iterations=0,
            error=f"injection-scan flagged: {[h['label'] for h in scan.hits]}",
            demo_mode=config.demo_mode,
        )

    tools = build_tools(config)
    agent = _build_agent(config, tools)

    if console is not None:
        with Live(Spinner("dots", text="[cyan]thinking…[/cyan]"), console=console, refresh_per_second=10):
            result = agent.run(question)
    else:
        result = agent.run(question)

    return AgentResultRich(
        success=result.success,
        output=result.output,
        iterations=result.iterations,
        trace=_serialize_trace(result.trace),
        usage=result.usage,
        error=result.error,
        demo_mode=config.demo_mode,
    )


def start_chat(config: CSKConfig, *, console: Console, raw: bool = False) -> None:
    """Interactive REPL. Memory is in-process — exit and you start fresh."""
    from ro_claude_kit_memory import ShortTermMemory

    memory = ShortTermMemory(keep_recent=8, compress_threshold_tokens=6000)
    tools = build_tools(config)
    agent = _build_agent(config, tools)
    api_key = config.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
    if api_key is not None:
        agent.api_key = api_key

    while True:
        try:
            user = console.input("[bold cyan]you ›[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye[/dim]")
            return
        if not user:
            continue
        if user in (":q", "/quit", "/exit"):
            console.print("[dim]bye[/dim]")
            return

        memory.add_turn("user", user)
        prior = "\n\n".join(f"{t.role.upper()}: {t.content}" for t in memory.turns[:-1]) or "(start of conversation)"
        prompt = f"Conversation so far:\n{prior}\n\nUser's new message: {user}"

        with Live(Spinner("dots", text="[cyan]thinking…[/cyan]"), console=console, refresh_per_second=10):
            result = agent.run(prompt)

        memory.add_turn("assistant", result.output)
        memory.maybe_compress()

        if raw:
            sys.stdout.write(result.output + "\n")
        else:
            console.print(f"[bold green]csk ›[/bold green] {result.output}\n")
