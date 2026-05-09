"""csk — Claude-powered CLI for startup ops.

Subcommands:
    csk init              — create a config file (interactive or --demo).
    csk ask "<question>"  — one-shot agent run against your configured tools.
    csk chat              — interactive REPL (multi-turn with short-term memory).
    csk tools             — list the tools registered for the current config.
    csk doctor            — health check.
    csk version           — print version.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from . import __version__
from .config import PROVIDER_PRESETS, CSKConfig, find_config_path, load_config, save_config
from .runner import AgentResultRich, run_ask, start_chat
from .tools import build_tools

app = typer.Typer(
    name="csk",
    help="Ask Claude questions about your Stripe / Linear / Slack / Notion / Postgres data.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


# ---------- init ----------

@app.command()
def init(
    demo: bool = typer.Option(False, "--demo", help="Skip credential prompts; use built-in demo data."),
    scope: str = typer.Option("project", "--scope", help="'project' (./.csk/) or 'user' (~/.config/csk/)."),
    yes: bool = typer.Option(False, "-y", "--yes", help="Overwrite existing config without confirmation."),
) -> None:
    """Create a csk config file."""
    existing = find_config_path()
    if existing and not yes:
        if not Confirm.ask(f"[yellow]A config already exists at[/yellow] {existing}. Overwrite?", default=False):
            console.print("[dim]aborted[/dim]")
            raise typer.Exit(1)

    if demo:
        cfg = CSKConfig(demo_mode=True)
        path = save_config(cfg, scope=scope)
        console.print(Panel.fit(
            f"[green]✓[/green] Demo config written to [cyan]{path}[/cyan]\n\n"
            "Try it now:\n"
            "  [bold]csk ask[/bold] [cyan]\"how many active subscriptions do we have?\"[/cyan]\n"
            "  [bold]csk tools[/bold]",
            title="Ready", border_style="green",
        ))
        return

    console.print(Panel.fit(
        "[bold]csk init[/bold] — pick an LLM provider, then add credentials for the services "
        "you want it to query.\n[dim]Values are stored in plaintext at .csk/config.toml — .gitignore "
        "that path.[/dim]",
        border_style="cyan",
    ))

    provider_choice = Prompt.ask(
        "LLM provider",
        choices=["anthropic", "ollama", "openai", "together", "groq", "fireworks", "custom"],
        default="anthropic",
    )
    preset = PROVIDER_PRESETS.get(provider_choice, {})
    model = Prompt.ask("Model", default=preset.get("model") or "")
    base_url: str | None = None
    if provider_choice == "custom":
        base_url = Prompt.ask("OpenAI-compatible base URL")
    elif provider_choice not in ("anthropic", "ollama"):
        base_url = preset.get("base_url") or ""

    anthropic_key: str | None = None
    openai_key: str | None = None
    if provider_choice == "anthropic":
        anthropic_key = Prompt.ask(
            "ANTHROPIC_API_KEY",
            default=os.environ.get("ANTHROPIC_API_KEY") or "",
            password=True,
        ) or None
    elif provider_choice != "ollama":
        openai_key = Prompt.ask(
            f"API key for {provider_choice}",
            default=os.environ.get("OPENAI_API_KEY") or "",
            password=True,
        ) or None

    console.print()
    stripe = Prompt.ask("Stripe API key (rk_live_... recommended)", default="", password=True)
    linear = Prompt.ask("Linear API key", default="", password=True)
    slack_bot = Prompt.ask("Slack bot token (xoxb-...)", default="", password=True)
    notion = Prompt.ask("Notion integration token", default="", password=True)
    database_url = Prompt.ask("Postgres DATABASE_URL", default="")

    cfg = CSKConfig(
        provider=provider_choice,
        model=model or None,
        base_url=base_url or None,
        anthropic_api_key=anthropic_key,
        openai_api_key=openai_key,
        stripe_api_key=stripe or None,
        linear_api_key=linear or None,
        slack_bot_token=slack_bot or None,
        notion_token=notion or None,
        database_url=database_url or None,
    )
    path = save_config(cfg, scope=scope)
    console.print(f"\n[green]✓[/green] Wrote config to [cyan]{path}[/cyan]")
    services = cfg.configured_services()
    console.print(f"[dim]provider:[/dim] {provider_choice} ({cfg.resolved_model()})")
    console.print(f"[dim]configured services:[/dim] {', '.join(services) if services else '[red]none[/red]'}")


# ---------- ask ----------

@app.command()
def ask(
    question: list[str] = typer.Argument(..., help="The question to ask. Wrap multi-word questions in quotes."),
    raw: bool = typer.Option(False, "--raw", help="Print plain output instead of rich panels."),
) -> None:
    """One-shot: send a question to Claude with your configured tools, print answer + trace."""
    config = load_config()
    if not config.has_provider_auth():
        console.print(
            f"[red]✗[/red] No credentials for provider [bold]{config.provider}[/bold]. "
            "Run [bold]csk init[/bold] (or [bold]csk init --demo[/bold]) first."
        )
        raise typer.Exit(2)

    text = " ".join(question)
    result = run_ask(config, text, console=console)
    _print_result(result, raw=raw)


# ---------- chat ----------

@app.command()
def chat(
    raw: bool = typer.Option(False, "--raw", help="Plain output."),
) -> None:
    """Multi-turn REPL with short-term memory. Type :q or Ctrl-D to exit."""
    config = load_config()
    if not config.has_provider_auth():
        console.print(f"[red]✗[/red] No credentials for provider [bold]{config.provider}[/bold]. Run [bold]csk init[/bold] first.")
        raise typer.Exit(2)

    console.print(Panel.fit(
        "[bold cyan]csk chat[/bold cyan] — multi-turn. Type [bold]:q[/bold] or Ctrl-D to exit.",
        border_style="cyan",
    ))
    start_chat(config, console=console, raw=raw)


# ---------- tools ----------

@app.command()
def tools() -> None:
    """List the tools that are wired up for the current config."""
    config = load_config()
    services = config.configured_services()
    tool_list = build_tools(config)

    table = Table(title="Configured tools", box=box.ROUNDED, show_lines=False)
    table.add_column("Service", style="cyan")
    table.add_column("Tool", style="bold")
    table.add_column("Description", style="dim", overflow="fold")

    for tool in tool_list:
        service = tool.name.split("_", 1)[0]
        table.add_row(service, tool.name, tool.description)
    if not tool_list:
        table.add_row("[red]none[/red]", "", "Run [bold]csk init[/bold] or [bold]csk init --demo[/bold].")

    console.print(table)
    if config.demo_mode:
        console.print("[yellow]demo mode is on[/yellow] — calls go to in-process fixtures, not real APIs.")
    elif services:
        console.print(f"[dim]configured services:[/dim] {', '.join(services)}")


# ---------- doctor ----------

@app.command()
def doctor() -> None:
    """Health check: config location, Anthropic reachability, configured services."""
    config = load_config()
    path = find_config_path()

    table = Table(box=box.ROUNDED, show_header=False)
    table.add_column(style="cyan", no_wrap=True)
    table.add_column()

    table.add_row("config file", str(path) if path else "[red]none[/red] — run csk init")
    table.add_row("demo mode", "[green]yes[/green]" if config.demo_mode else "[dim]no[/dim]")
    table.add_row("provider", config.provider)
    table.add_row("model", config.resolved_model())
    if config.resolved_base_url():
        table.add_row("base_url", config.resolved_base_url() or "")
    table.add_row(
        f"{config.provider} auth",
        "[green]ok[/green]" if config.has_provider_auth() else "[red]missing[/red]",
    )
    services = config.configured_services()
    table.add_row("services", ", ".join(services) if services else "[red]none[/red]")
    table.add_row("csk version", __version__)

    console.print(table)


# ---------- version ----------

@app.command()
def version() -> None:
    """Print the csk version."""
    console.print(f"csk {__version__}")


def _print_result(result: AgentResultRich, *, raw: bool) -> None:
    if raw:
        sys.stdout.write(result.output + "\n")
        return

    console.print()
    console.print(Panel(result.output or "[dim](empty)[/dim]", title="Answer", border_style="green", padding=(1, 2)))
    if result.trace:
        table = Table(title=f"Trace ({len(result.trace)} steps)", box=box.SIMPLE, show_lines=False)
        table.add_column("kind", style="bold yellow", no_wrap=True)
        table.add_column("content", overflow="fold")
        for step in result.trace:
            content = step["content"]
            if not isinstance(content, str):
                import json as _json
                content = _json.dumps(content, indent=2, default=str)
            table.add_row(step["kind"], content[:600])
        console.print(table)
    meta = f"iterations: {result.iterations}"
    if result.usage:
        meta += f" · in: {result.usage.get('input_tokens', 0)} · out: {result.usage.get('output_tokens', 0)}"
    if result.demo_mode:
        meta += " · [yellow]demo mode[/yellow]"
    console.print(f"[dim]{meta}[/dim]")


if __name__ == "__main__":  # pragma: no cover
    app()
