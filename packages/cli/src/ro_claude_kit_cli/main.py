"""csk — Claude-powered CLI for startup ops.

Subcommands:
    csk init              — create a config file (interactive or --demo).
    csk ask "<question>"  — one-shot agent run against your configured tools.
    csk chat              — interactive REPL (multi-turn with short-term memory).
    csk tools             — list the tools registered for the current config.
    csk doctor            — health check.
    csk save NAME "Q"     — save a question for later recall.
    csk run NAME          — run a saved question.
    csk queries           — list saved questions.
    csk eval ...          — eval suite (golden datasets, drift detection).
    csk version           — print version.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
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
from .saved_queries import QueryStore, default_path as queries_path
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


# ---------- saved queries ----------

@app.command()
def save(
    name: str = typer.Argument(..., help="Short slug-style name. Letters / digits / '-' / '_' only."),
    query: list[str] = typer.Argument(..., help="The question to save. Quote multi-word questions."),
    description: str = typer.Option("", "--description", "-d", help="Optional one-line description."),
) -> None:
    """Save a question under NAME for later recall via `csk run NAME`."""
    path = queries_path()
    store = QueryStore.load(path)
    text = " ".join(query)
    try:
        store.add(name, text, description=description)
    except ValueError as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(2)
    store.save(path)
    console.print(f"[green]✓[/green] saved [bold]{name}[/bold]: {text}")
    console.print(f"[dim]run it with:[/dim] [bold]csk run {name}[/bold]")


@app.command()
def run(
    name: str = typer.Argument(..., help="Name of a saved query."),
    raw: bool = typer.Option(False, "--raw", help="Plain output."),
) -> None:
    """Run a saved query as if you typed `csk ask "<saved text>"`."""
    store = QueryStore.load(queries_path())
    try:
        saved = store.get(name)
    except KeyError:
        console.print(f"[red]✗[/red] no saved query named [bold]{name}[/bold]. See [bold]csk queries[/bold].")
        raise typer.Exit(2)

    config = load_config()
    if not config.has_provider_auth():
        console.print(
            f"[red]✗[/red] No credentials for provider [bold]{config.provider}[/bold]. Run [bold]csk init[/bold] first."
        )
        raise typer.Exit(2)

    console.print(f"[dim]running saved query[/dim] [bold]{name}[/bold]: {saved.query}")
    result = run_ask(config, saved.query, console=console)
    _print_result(result, raw=raw)


@app.command()
def queries() -> None:
    """List all saved queries."""
    store = QueryStore.load(queries_path())
    items = store.list_all()
    if not items:
        console.print("[dim]no saved queries yet. Try:[/dim] [bold]csk save mrr \"what is our MRR right now\"[/bold]")
        return
    table = Table(title="Saved queries", box=box.ROUNDED)
    table.add_column("name", style="cyan", no_wrap=True)
    table.add_column("query", overflow="fold")
    table.add_column("description", style="dim", overflow="fold")
    for q in items:
        table.add_row(q.name, q.query, q.description or "")
    console.print(table)


@app.command(name="unsave")
def unsave(name: str = typer.Argument(..., help="Name of the saved query to remove.")) -> None:
    """Remove a saved query."""
    path = queries_path()
    store = QueryStore.load(path)
    if not store.remove(name):
        console.print(f"[red]✗[/red] no saved query named [bold]{name}[/bold]")
        raise typer.Exit(2)
    store.save(path)
    console.print(f"[green]✓[/green] removed [bold]{name}[/bold]")


# ---------- eval (delegates to the csk-eval entry point) ----------

eval_app = typer.Typer(help="Eval suite: golden datasets, judge runs, drift detection.")
app.add_typer(eval_app, name="eval")


@eval_app.command("run", help="Run a golden dataset against a target model.")
def eval_run(
    dataset: Path = typer.Argument(..., help="Path to JSONL dataset."),
    target: str = typer.Option("claude-sonnet-4-6", "--target"),
    judge: str = typer.Option("claude-opus-4-7", "--judge"),
    criteria: str = typer.Option(
        "task_success,faithfulness,helpfulness,safety", "--criteria",
        help="Comma-separated rubric criteria.",
    ),
    label: Optional[str] = typer.Option(None, "--label"),
    json_out: str = typer.Option("eval-report.json", "--json-out"),
    out: Optional[str] = typer.Option(None, "--out", help="Optional HTML report path."),
) -> None:
    from ro_claude_kit_eval_suite.cli import main as eval_main

    argv = ["run", str(dataset), "--target", target, "--judge", judge, "--criteria", criteria, "--json-out", json_out]
    if label:
        argv += ["--label", label]
    if out:
        argv += ["--out", out]
    raise typer.Exit(eval_main(argv))


@eval_app.command("drift", help="Compare two run reports; exit non-zero on regression.")
def eval_drift(
    baseline: Path = typer.Argument(...),
    candidate: Path = typer.Argument(...),
    threshold: float = typer.Option(0.5, "--threshold"),
) -> None:
    from ro_claude_kit_eval_suite.cli import main as eval_main

    argv = ["drift", str(baseline), str(candidate), "--threshold", str(threshold)]
    raise typer.Exit(eval_main(argv))


# ---------- plugins ----------

@app.command()
def plugins() -> None:
    """List user plugins loaded from .csk/plugins/."""
    from .plugins import load_plugins

    results = load_plugins()
    if not results:
        console.print(
            "[dim]no plugins. Drop a Python file in[/dim] [bold].csk/plugins/[/bold] "
            "[dim]exporting[/dim] [bold]register_tools() -> list[Tool][/bold]."
        )
        return
    table = Table(title="Loaded plugins", box=box.ROUNDED)
    table.add_column("plugin", style="cyan", no_wrap=True)
    table.add_column("tools", overflow="fold")
    table.add_column("status", style="dim", overflow="fold")
    for r in results:
        tools_str = ", ".join(t.name for t in r.tools) or "[dim](none)[/dim]"
        status = "[green]ok[/green]" if r.error is None else f"[red]error:[/red] {r.error}"
        table.add_row(r.name, tools_str, status)
    console.print(table)


# ---------- serve ----------

@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Expose the configured agent as a REST API (POST /ask + GET /health)."""
    config = load_config()
    if not config.has_provider_auth():
        console.print(f"[red]✗[/red] No credentials for provider [bold]{config.provider}[/bold]. Run [bold]csk init[/bold] first.")
        raise typer.Exit(2)

    import uvicorn
    from .server import make_app

    console.print(Panel.fit(
        f"[bold cyan]csk serve[/bold cyan] — agent over HTTP\n"
        f"[dim]provider:[/dim] {config.provider} ({config.resolved_model()})\n"
        f"[dim]listening:[/dim] http://{host}:{port}\n\n"
        f"POST /ask     {{\"question\": \"...\"}}\n"
        f"GET  /health",
        border_style="cyan",
    ))
    app_fastapi = make_app(config)
    uvicorn.run(app_fastapi, host=host, port=port, log_level="info")


# ---------- costs ----------

@app.command()
def costs(
    by: str = typer.Option("model", "--by", help="Group by: model | day | none"),
) -> None:
    """Show token usage + estimated USD costs from .csk/usage.jsonl."""
    from .usage import load_records, summarize, usage_path

    path = usage_path()
    records = load_records()
    if not records:
        console.print(
            f"[dim]no usage recorded yet at[/dim] [bold]{path}[/bold]. "
            "[dim]Run[/dim] [bold]csk ask[/bold] [dim]with a real provider to start tracking.[/dim]"
        )
        return
    summary = summarize(records)

    header = Table(title="Total usage", box=box.ROUNDED, show_header=False)
    header.add_column(style="cyan")
    header.add_column()
    header.add_row("calls", str(summary.total_calls))
    header.add_row("input tokens", f"{summary.total_input_tokens:,}")
    header.add_row("output tokens", f"{summary.total_output_tokens:,}")
    header.add_row("estimated cost", f"${summary.total_cost_usd:.4f}")
    console.print(header)

    if by in ("model", "day"):
        breakdown = summary.by_model if by == "model" else summary.by_day
        if breakdown:
            t = Table(title=f"By {by}", box=box.ROUNDED)
            t.add_column(by, style="cyan")
            t.add_column("calls", justify="right")
            t.add_column("input", justify="right")
            t.add_column("output", justify="right")
            t.add_column("cost (USD)", justify="right")
            for key, s in sorted(breakdown.items()):
                t.add_row(
                    key, str(s.total_calls),
                    f"{s.total_input_tokens:,}", f"{s.total_output_tokens:,}",
                    f"${s.total_cost_usd:.4f}",
                )
            console.print(t)


# ---------- plugins ----------

@app.command()
def plugins() -> None:
    """Discover and list user plugins from .csk/plugins/."""
    from .plugins import find_plugin_dir, load_plugins

    plugin_dir = find_plugin_dir()
    results = load_plugins(plugin_dir)

    if not plugin_dir.exists():
        console.print(
            f"[dim]no plugin dir at[/dim] [cyan]{plugin_dir}[/cyan][dim] yet. "
            "Drop a .py file with a register_tools() function there to add custom tools.[/dim]"
        )
        return
    if not results:
        console.print(f"[dim]no plugins found in[/dim] [cyan]{plugin_dir}[/cyan]")
        return

    table = Table(title=f"Plugins from {plugin_dir}", box=box.ROUNDED)
    table.add_column("plugin", style="cyan", no_wrap=True)
    table.add_column("status", no_wrap=True)
    table.add_column("tools / error", overflow="fold")
    for r in results:
        if r.error:
            table.add_row(r.name, "[red]error[/red]", r.error)
        else:
            tool_names = ", ".join(t.name for t in r.tools) or "[dim](none)[/dim]"
            table.add_row(r.name, "[green]ok[/green]", tool_names)
    console.print(table)


# ---------- serve ----------

@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Run csk as an HTTP API. POST /ask, GET /health."""
    config = load_config()
    if not config.has_provider_auth():
        console.print(f"[red]✗[/red] No credentials for provider [bold]{config.provider}[/bold]. Run [bold]csk init[/bold] first.")
        raise typer.Exit(2)

    try:
        import uvicorn
    except ImportError:
        console.print("[red]✗[/red] uvicorn not installed. Run: [bold]uv pip install uvicorn[/bold]")
        raise typer.Exit(2)

    from .server import make_app

    app_obj = make_app(config)
    console.print(Panel.fit(
        f"[bold cyan]csk serve[/bold cyan]\n"
        f"http://{host}:{port}/health   →   health check\n"
        f"POST http://{host}:{port}/ask  →   {{\"question\": \"...\"}}\n\n"
        f"provider: {config.provider} · model: {config.resolved_model()} · "
        f"services: {', '.join(config.configured_services()) or 'none'}",
        title="ready", border_style="green",
    ))
    uvicorn.run(app_obj, host=host, port=port, log_level="info")


# ---------- costs ----------

@app.command()
def costs(
    by: str = typer.Option("model", "--by", help="Group by 'model' or 'day'."),
) -> None:
    """Show token + cost usage recorded by previous csk commands."""
    from .usage import load_records, summarize, usage_path

    records = load_records()
    if not records:
        console.print(
            f"[dim]no usage recorded yet at[/dim] [cyan]{usage_path()}[/cyan][dim]. "
            "Run [bold]csk ask[/bold] a few times to populate.[/dim]"
        )
        return

    summary = summarize(records)
    header = Table(box=box.ROUNDED, show_header=False)
    header.add_column(style="cyan", no_wrap=True)
    header.add_column(style="bold")
    header.add_row("total calls", str(summary.total_calls))
    header.add_row("input tokens", f"{summary.total_input_tokens:,}")
    header.add_row("output tokens", f"{summary.total_output_tokens:,}")
    header.add_row("total cost", f"${summary.total_cost_usd:.4f}")
    console.print(header)

    bucket = summary.by_model if by == "model" else summary.by_day
    label = "model" if by == "model" else "day"
    table = Table(title=f"By {label}", box=box.ROUNDED)
    table.add_column(label, style="cyan")
    table.add_column("calls", justify="right")
    table.add_column("input", justify="right")
    table.add_column("output", justify="right")
    table.add_column("cost", justify="right", style="bold")
    for key in sorted(bucket.keys()):
        s = bucket[key]
        table.add_row(
            key, str(s.total_calls),
            f"{s.total_input_tokens:,}", f"{s.total_output_tokens:,}",
            f"${s.total_cost_usd:.4f}",
        )
    console.print(table)


# ---------- tui ----------

@app.command()
def tui() -> None:
    """Launch a full-screen TUI (Textual) — chat pane + live trace + input box."""
    config = load_config()
    if not config.has_provider_auth():
        console.print(f"[red]✗[/red] No credentials for provider [bold]{config.provider}[/bold]. Run [bold]csk init[/bold] first.")
        raise typer.Exit(2)
    try:
        from .tui import run_tui
    except ImportError as exc:
        console.print(f"[red]✗[/red] textual not installed: {exc}. Try [bold]uv pip install textual[/bold].")
        raise typer.Exit(2)
    run_tui(config=config)


# ---------- tui ----------

@app.command()
def tui() -> None:
    """Full-screen Textual UI: chat pane (multi-turn) + live trace pane, with Ctrl-L to clear and F1 for help."""
    config = load_config()
    if not config.has_provider_auth():
        console.print(
            f"[red]✗[/red] No credentials for provider [bold]{config.provider}[/bold]. Run [bold]csk init[/bold] first "
            "(or [bold]csk init --demo[/bold] for an offline tour)."
        )
        raise typer.Exit(2)

    from .tui import run_tui

    run_tui(config=config)


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
