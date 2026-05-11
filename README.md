# RO-Claude-kit

> The agent CLI for startup ops. Install once, configure once, then ask questions about your data — backed by Claude or any open-source LLM you choose.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.1.0-blue)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-212%20passing-green)](https://github.com/rohithkandula19/RO-Claude-kit/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Providers](https://img.shields.io/badge/providers-Claude%20·%20Ollama%20·%20OpenAI%20·%20Together%20·%20Groq%20·%20Fireworks-d4a373)](#-supported-providers)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

```bash
$ pipx install ro-claude-kit-cli
$ csk init --demo
$ csk ask "how many active subscriptions do we have, and what's our MRR?"

🤔 thinking…
✅ You have 2 active subscriptions: Alice (Pro $49/mo) and Bob (Starter $29/mo).
   Total MRR from active subs: $78/mo.
```

## What is `csk`?

`csk` is the CLI you point at your startup's data. Configure once with read-only credentials for the services you care about — Stripe, Linear, Slack, Notion, Postgres — then ask questions in plain English. The agent reaches for the right tool, queries the right data, and answers.

No more clicking through five dashboards to answer "which customers churned this month and what did their last support thread say?"

## 🧠 Supported providers

`csk` works with any LLM — proprietary or open-source. Switch providers with one config change.

| Provider | Backend | Default model | Auth |
|---|---|---|---|
| **Anthropic** (default) | native SDK | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| **Ollama** (local, free) | OpenAI-compat | `llama3.1` | none — runs on your machine |
| **OpenAI** | OpenAI-compat | `gpt-4o-mini` | `OPENAI_API_KEY` |
| **Together** | OpenAI-compat | `Llama-3.3-70B-Instruct-Turbo` | `OPENAI_API_KEY` |
| **Groq** | OpenAI-compat | `llama-3.3-70b-versatile` | `OPENAI_API_KEY` |
| **Fireworks** | OpenAI-compat | `llama-v3p3-70b-instruct` | `OPENAI_API_KEY` |
| **Custom** | OpenAI-compat | (you specify) | (you specify) |

Switch providers:
```toml
# .csk/config.toml
provider = "ollama"
model = "llama3.1"
```

## Install

```bash
pipx install ro-claude-kit-cli                # recommended (isolated venv)
# or
pip install ro-claude-kit-cli
```

For Postgres support: `pipx install 'ro-claude-kit-cli[postgres]'`.

## 30-second quickstart (no real credentials)

```bash
csk init --demo                                 # ships fake Stripe + Linear data
csk ask "what ENG issues are in progress?"
csk ask "which customers have active subscriptions?"
csk chat                                        # multi-turn REPL
```

Demo mode is wired so you can play with the CLI before connecting any real services. Without an API key, an offline keyword router answers — set a key for full natural-language responses.

## Real config

```bash
csk init                                        # interactive — picks provider + service creds
```

Or write `.csk/config.toml`:

```toml
provider = "anthropic"
model = "claude-sonnet-4-6"
anthropic_api_key = "sk-ant-..."

stripe_api_key = "rk_live_..."                  # use a Restricted Key
linear_api_key = "lin_api_..."
slack_bot_token = "xoxb-..."
notion_token = "secret_..."
database_url = "postgres://readonly_user:...@host:5432/db"
```

Add `.csk/` to `.gitignore` — the file is plaintext credentials.

## Commands

| Command | What it does |
|---|---|
| `csk init [--demo]` | Create a config file (interactive or demo). |
| `csk ask "<question>"` | One-shot — print answer + typed trace. |
| `csk chat` | Multi-turn REPL with short-term memory. |
| `csk save NAME "..."` | Save a question for later (turns ad-hoc into reusable). |
| `csk run NAME` | Run a saved query. |
| `csk queries` / `csk unsave NAME` | List or remove saved queries. |
| `csk serve --port 8000` | Expose the agent as an HTTP API (`POST /ask`). |
| `csk plugins` | List user plugins discovered in `.csk/plugins/`. |
| `csk costs [--by model\|day]` | Token + cost usage recorded by previous runs. |
| `csk tools` | List the tools registered for the current config. |
| `csk doctor` | Health check: provider, auth, services. |
| `csk eval run <dataset>` | LLM-as-judge eval over a golden dataset (HTML report optional). |
| `csk eval drift <a> <b>` | Compare two runs; non-zero exit on regression. CI-friendly. |
| `csk version` | Print the version. |

## Why csk vs ...

| | csk | aider | langchain | crewai |
|---|---|---|---|---|
| Built specifically for startup ops (Stripe / Linear / Slack / Notion / Postgres) | ✅ | ❌ | ❌ | ❌ |
| Read-only by default for every integration | ✅ | n/a | ❌ | ❌ |
| Built-in prompt-injection scanner | ✅ | ❌ | ❌ | ❌ |
| Works with Claude AND open-source LLMs | ✅ | ✅ | ✅ | ✅ |
| Zero-config offline demo (`--demo`) | ✅ | ❌ | ❌ | ❌ |
| Hand-rolled agent loop (no LangChain dependency) | ✅ | ✅ | n/a | ❌ |
| LLM-as-judge eval suite included | ✅ | ❌ | ❌ | ❌ |

aider is the gold standard for *coding* agents. CrewAI / LangChain are agent frameworks — useful but heavyweight. `csk` is a focused product for one thing: asking your operational data questions.

## Safety by default

Every input passes through a prompt-injection scanner before reaching the LLM. Every tool is read-only. There is no path through `csk` to mutate your data — even if the LLM tries, the kit's `ToolAllowlist` blocks it. Adding write paths is a deliberate fork-and-wrap operation through `ApprovalGate`.

PII (emails, SSNs, credit cards, API keys) is redacted from traces before anything leaves your process.

## What's under the hood

`csk` is the user-facing wrapper. The substance lives in seven packages you can also use independently:

| Package | What it does | Tests |
|---|---|---|
| `agent-patterns` | ReAct, Planner-Executor, Multi-Agent Supervisor, Reflexion + LLM provider abstraction | 20 |
| `eval-suite` | LLM-as-a-judge, golden datasets, drift detection, HTML reports | 11 |
| `memory` | Short-term (rolling summary), long-term (pluggable vector store), user preferences | 11 |
| `hardening` | Prompt-injection scanner, tool allowlist, approval gates, output validator | 20 |
| `mcp-servers` | Read-only Postgres, Stripe, Linear, Slack, Notion, Tavily, GitHub templates | 67 |
| `cli` | The `csk` binary | 36 |
| `deployment-templates` | Docker Compose, Modal, Vercel, Railway | — |
| `apps/demo` | AgentLab — interactive FastAPI playground | 5 |

**152 tests** across all packages, green on every push (see CI).

## Use the modules without the CLI

Build an agent in 5 lines:

```python
from ro_claude_kit_agent_patterns import ReActAgent, Tool

agent = ReActAgent(
    system="You are a helpful research assistant.",
    tools=[Tool(name="search", description="...", input_schema={...}, handler=my_search)],
)
print(agent.run("What is the ReAct pattern?").output)
```

Use it with Ollama instead of Claude:

```python
from ro_claude_kit_agent_patterns import OllamaProvider, ReActAgent

agent = ReActAgent(
    system="...",
    tools=[...],
    provider=OllamaProvider(model="llama3.1"),
)
```

Add an eval suite:

```python
from ro_claude_kit_eval_suite import EvalSuite, Rubric, GoldenDataset

suite = EvalSuite(
    rubric=Rubric(criteria=["task_success", "faithfulness", "safety"]),
    target_runner=lambda case: agent.run(case.input).output,
)
report = suite.run(GoldenDataset.from_jsonl("./golden.jsonl"))
```

## Examples

End-to-end agents you can run today:

| Example | What it shows |
|---|---|
| [`research-agent/`](examples/research-agent/) | ReAct with a toy KB — smallest, simplest |
| [`customer-support/`](examples/customer-support/) | Supervisor + 4 sub-agents, Pydantic-validated `DraftReply`, 25-case golden dataset |
| [`code-reviewer/`](examples/code-reviewer/) | 3 specialist sub-agents (style / bugs / security) aggregating into a typed `CodeReview` |

```bash
export ANTHROPIC_API_KEY=sk-ant-...
uv run python examples/customer-support/main.py "I was charged twice for my Pro plan!"
uv run python examples/code-reviewer/main.py examples/code-reviewer/sample_buggy_code.py
```

## Try AgentLab — the interactive playground

A FastAPI app that lets you click through all four agent patterns side-by-side:

```bash
git clone https://github.com/rohithkandula19/RO-Claude-kit
cd RO-Claude-kit
uv sync --all-packages --all-groups
uv run uvicorn app.main:app --port 8000 --app-dir apps/demo
```

Open http://localhost:8000.

## Repository layout

```
RO-Claude-kit/
├── packages/
│   ├── cli/                  # the csk binary
│   ├── agent-patterns/       # core loop patterns + provider abstraction
│   ├── eval-suite/           # LLM-as-a-judge
│   ├── memory/               # 3-layer memory
│   ├── mcp-servers/          # 5 read-only service templates
│   ├── hardening/            # injection / allowlist / approval / validation
│   └── deployment-templates/ # docker-compose, modal, vercel, railway
├── apps/
│   ├── demo/                 # AgentLab — interactive playground
│   └── docs/                 # Mintlify documentation site
├── examples/
└── ...
```

## Documentation

- [Documentation site](apps/docs/) — concepts, production checklist, ADRs (run `mintlify dev` from `apps/docs/` to preview)
- [CHANGELOG.md](CHANGELOG.md) — what's new
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to add MCP servers, providers, etc.

## License

MIT. See [LICENSE](LICENSE).

## Star history

If this saves you a weekend, ⭐️ the repo. It's the only metric I'll see.

---

Built for [Claude](https://www.anthropic.com/claude). Not affiliated with Anthropic.
