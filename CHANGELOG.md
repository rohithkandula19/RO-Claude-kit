# Changelog

All notable changes to this project will be documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **End-to-end examples** with mermaid architecture diagrams and cookbook docs:
  - `examples/customer-support/` — SupervisorAgent orchestrating triage / billing-lookup / KB-lookup / Linear-lookup specialists, Pydantic `DraftReply` schema, 25-case golden dataset.
  - `examples/code-reviewer/` — three specialists (style / bugs / security) aggregating into a typed `CodeReview`, with a deliberately-buggy sample file.
  - `examples/README.md` — gallery + adapt-it pattern.
- **Tavily web-search MCP server** — `TavilyTools` + `tavily_tools()` factory.
- **Examples smoke tests** — end-to-end run via FakeProvider, validates the golden dataset.
- Multi-provider support shipped earlier in [0.1.0] now exercised via the customer-support example.

### Repo stats
- 165 tests, green on every push.

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
