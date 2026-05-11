# Changelog

All notable changes to this project will be documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — TUI, extensibility, HTTP mode, cost tracking
- **`csk tui`**: full-screen Textual interface. Chat pane (multi-turn with in-session memory) + live trace pane, F1 help, Ctrl-L to clear, Ctrl-Q to quit. Runs the agent in a worker thread so the UI stays responsive while Claude is thinking.
- **Plugin loader**: drop a Python file in `.csk/plugins/` exposing `register_tools() -> list[Tool]` and it auto-loads. Broken plugins don't take down others — errors are surfaced via `csk plugins`. First-class extensibility without forking the kit.
- **`csk serve`**: exposes the configured agent as an HTTP API (`POST /ask`, `GET /health`). Pairs cleanly with the existing Vercel/Railway/Docker deployment templates — `docker compose up` and you have a real agent backend.
- **`csk costs`**: every `csk ask` / `csk chat` run now records token usage + cost to `.csk/usage.jsonl`. `csk costs` shows total + per-model + per-day. Pricing table for Anthropic, OpenAI, Together, Groq, Fireworks, Ollama (free).
- **`csk plugins`**: discover and inspect loaded plugins.
- **vhs tape** at `scripts/demo.tape` — declarative terminal-recording script so a 30-second GIF for the README is one `vhs scripts/demo.tape` away.

### Added — earlier in Unreleased
- **Saved queries**: `csk save NAME "..."`, `csk run NAME`, `csk queries`, `csk unsave NAME`. Persists to `.csk/queries.toml`.
- **Unified eval subcommand**: `csk eval run`/`drift` now built into the main `csk` binary (`csk-eval` still works for back-compat).
- **GitHub MCP server**: `GitHubReadOnlyTools` + `github_tools()` covering repos, issues, PRs, commits, code search. mcp-servers now ships 7 servers.
- **End-to-end examples**: `customer-support/` (Supervisor + 4 specialists + Pydantic `DraftReply`) and `code-reviewer/` (style/bugs/security specialists + typed `CodeReview`).
- **Tavily web-search MCP server** — `TavilyTools` + `tavily_tools()` factory.

### Repo stats
- 218 tests, green on every push.

## [0.1.0] — 2026-05-08

### Added — `csk` CLI

- New `ro-claude-kit-cli` package shipping the `csk` binary.
- Subcommands: `csk init`, `csk ask`, `csk chat`, `csk tools`, `csk doctor`, `csk version`.
- Demo mode (`csk init --demo`) ships fake Stripe + Linear data; runs zero-config.
- Offline `demo_brain` keyword router so `csk ask` works without any API key.
- Rich terminal output: tables, panels, spinners.
- Prompt-injection scanning at the CLI boundary before any tool call.
- Auto-loads `.csk/config.toml` (project-local) or `~/.config/csk/config.toml` (user-global); env-var overrides win over file values.

### Added — multi-provider support

- New `LLMProvider` abstraction in `agent-patterns`. Every pattern (`ReActAgent`, `PlannerExecutorAgent`, `SupervisorAgent`, `ReflexionAgent`) now accepts a `provider` kwarg.
- `AnthropicProvider` (default) — Claude.
- `OpenAICompatProvider` — OpenAI, Ollama, Together, Groq, Fireworks, vLLM, llama.cpp server, LM Studio, anything with `/chat/completions`.
- `OllamaProvider` convenience subclass — defaults to `http://localhost:11434/v1`, no API key needed.
- `FakeProvider` for tests.

### Added — modules

- `agent-patterns`: ReAct, Planner-Executor, Multi-Agent Supervisor, Reflexion.
- `eval-suite`: LLM-as-a-judge, golden datasets, drift detection, HTML reports, `csk-eval` CLI.
- `memory`: short-term (rolling summary), long-term (pluggable vector backend), user preferences.
- `hardening`: prompt-injection scanner, output-leak scanner, tool allowlist, approval gates, output validator with retry, PII-redacted tracing.
- `mcp-servers`: read-only Postgres, Stripe, Linear, Slack, Notion templates.
- `deployment-templates`: Docker Compose, Modal, Vercel, Railway one-click deploys.
- `apps/demo`: AgentLab — interactive FastAPI playground for all four agent patterns.
- `apps/docs`: Mintlify documentation site with eight content pages and Mermaid diagrams.

### Tests
- 152 tests across all packages, all passing on every push.

[Unreleased]: https://github.com/rohithkandula19/RO-Claude-kit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/rohithkandula19/RO-Claude-kit/releases/tag/v0.1.0
