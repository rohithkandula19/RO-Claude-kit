# RO-Claude-kit

> An opinionated reference implementation for shipping production Claude agents in a weekend.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-under%20construction-orange)](https://github.com/rohithkandula19/RO-Claude-kit)
[![Built for Claude](https://img.shields.io/badge/built%20for-Claude-d4a373)](https://www.anthropic.com)

`RO-Claude-kit` is the agent-builder starter pack I wish existed when I was wiring my first production Claude system. It bundles the patterns, evals, memory, MCP integrations, and hardening that every AI-native startup ends up rebuilding — and bakes them into a fork-and-ship monorepo.

Think `create-next-app` for Claude agents.

## Why this exists

Most Claude agents in the wild fail in the same ways:

- **No evals.** "It seemed to work in our demo" is not a release criterion.
- **Brittle tool use.** One bad arg, one rate limit, and the agent crashes the loop.
- **Prompt-injection foot-guns.** User input flows straight into a tool-calling planner.
- **No memory strategy.** Conversation history just accumulates until the context window dies.
- **No observability.** When prod breaks, you're reading raw token streams.

The kit ships opinionated, batteries-included modules for each of these so you can spend your weekend building the *interesting* part of your product.

## Who it's for

- AI-native startup founders who need a working agent in production this month, not next quarter.
- Engineers who've shipped a chatbot demo and now need to make it survive real users.
- Teams evaluating Claude for an agentic product and want a credible reference implementation to point at.

## The six modules

| Module | What it does |
|---|---|
| `agent-patterns` | ReAct, Planner-Executor, Multi-Agent Supervisor, Reflexion — Python with a TS wrapper |
| `eval-suite` | LLM-as-a-judge with golden datasets, drift detection, HTML reports, CLI runner |
| `memory` | Short-term (compressed history) + long-term (pluggable vector store) + user preferences |
| `mcp-servers` | Reference MCP templates: Stripe, Linear, Slack, Notion, Postgres (read-only by default) |
| `hardening` | Prompt-injection defense, tool allowlists, output validation, Langfuse / Helicone tracing |
| `deployment-templates` | One-click deploys to Vercel, Railway, Modal, and Docker Compose |

## Quickstart

> Coming in Week 4. The TL;DR will look something like:

```bash
# clone + install
git clone https://github.com/rohithkandula19/RO-Claude-kit
cd RO-Claude-kit
pnpm install && uv sync

# pick a pattern, run an example
uv run python examples/customer-support/main.py

# evaluate the agent on a golden dataset
uv run csk eval run examples/customer-support/golden.jsonl
```

## Repository layout

```
RO-Claude-kit/
├── packages/            # the six modules above
├── apps/
│   ├── demo/            # AgentLab — interactive playground
│   └── docs/            # docs site
├── examples/            # end-to-end agents built with the kit
└── ...
```

## Status

`v0.0.1` — under construction, building in public. Following a [4-week build plan](https://github.com/rohithkandula19/RO-Claude-kit) with one module landing per week.

| Week | Modules |
|---|---|
| 1 | `agent-patterns` |
| 2 | `eval-suite`, `memory`, `mcp-servers` |
| 3 | `hardening`, `deployment-templates`, demo app |
| 4 | Docs, video walkthrough, public launch |

## License

MIT. See [LICENSE](LICENSE).

## Acknowledgements

Built for [Claude](https://www.anthropic.com/claude). Not affiliated with Anthropic.
