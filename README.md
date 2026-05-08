# RO-Claude-kit

> The Claude-powered CLI for startup ops. Install once, configure once, then ask Claude to actually do things with your data.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.1.0-blue)](https://github.com/rohithkandula19/RO-Claude-kit)
[![Built for Claude](https://img.shields.io/badge/built%20for-Claude-d4a373)](https://www.anthropic.com)
[![Tests](https://img.shields.io/badge/tests-127%20passing-green)](https://github.com/rohithkandula19/RO-Claude-kit/actions)

```bash
$ pipx install ro-claude-kit-cli
$ csk init --demo
$ csk ask "how many active subscriptions do we have, and what's our MRR?"

🤔 thinking…
✅ You have 2 active subscriptions: Alice (Pro $49/mo) and Bob (Starter $29/mo).
   Total MRR from active subs: $78/mo.
```

## What is `csk`?

`csk` is the CLI you point at your startup's data. Configure once with read-only credentials for the services you care about — Stripe, Linear, Slack, Notion, Postgres — then ask questions in plain English. Claude reaches for the right tool, queries the right data, and answers.

No more clicking through five dashboards to answer "which customers churned this month and what was their last support thread?"

## Install

```bash
pipx install ro-claude-kit-cli                  # recommended (isolated venv)
# or
pip install ro-claude-kit-cli                   # for ad-hoc use
```

For Postgres support: `pipx install 'ro-claude-kit-cli[postgres]'`.

## 30-second quickstart (no real credentials)

```bash
csk init --demo                                  # ships fake Stripe + Linear data
csk ask "what ENG issues are in progress?"
csk ask "which customers have active subscriptions?"
csk chat                                         # multi-turn REPL
```

Demo mode is wired so you can play with the CLI before connecting any real services.

## Real config

```bash
csk init                                         # interactive prompts
```

Or write `.csk/config.toml`:

```toml
anthropic_api_key = "sk-ant-..."
stripe_api_key = "rk_live_..."                   # use a Restricted Key
linear_api_key = "lin_api_..."
slack_bot_token = "xoxb-..."
notion_token = "secret_..."
database_url = "postgres://readonly_user:...@host:5432/db"
```

`.gitignore` `.csk/` — the file is plaintext credentials.

## Commands

| Command | What it does |
|---|---|
| `csk init [--demo]` | Create a config file (interactive or demo). |
| `csk ask "<question>"` | One-shot agent run; prints answer + typed trace. |
| `csk chat` | Multi-turn REPL with short-term memory. |
| `csk tools` | List the tools registered for the current config. |
| `csk doctor` | Health check: config, auth, services. |
| `csk version` | Print the version. |

## Safety by default

Every input passes through a prompt-injection scanner before it reaches Claude. Every tool is read-only. There is no path through `csk` to mutate your data — even if Claude tries, the kit's `ToolAllowlist` blocks it. Adding write paths is a deliberate fork-and-wrap operation through `ApprovalGate`.

PII (emails, SSNs, credit cards, API keys) is redacted from traces before anything leaves your process.

## What's under the hood

`csk` is the user-facing wrapper. The substance lives in seven packages you can also use independently:

| Package | What it does | Tests |
|---|---|---|
| `agent-patterns` | ReAct, Planner-Executor, Multi-Agent Supervisor, Reflexion | 11 |
| `eval-suite` | LLM-as-a-judge, golden datasets, drift detection, HTML reports | 11 |
| `memory` | Short-term (rolling summary), long-term (pluggable vector store), user preferences | 11 |
| `hardening` | Prompt-injection scanner, tool allowlist, approval gates, output validator | 20 |
| `mcp-servers` | Read-only Postgres, Stripe, Linear, Slack, Notion templates | 49 |
| `cli` | The `csk` binary | 20 |
| `deployment-templates` | Docker Compose, Modal, Vercel, Railway one-click deploys | — |

127 tests across all packages, green on every push (see CI).

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

Add an eval suite:

```python
from ro_claude_kit_eval_suite import EvalSuite, Rubric, GoldenDataset

suite = EvalSuite(
    rubric=Rubric(criteria=["task_success", "faithfulness", "safety"]),
    target_runner=lambda case: agent.run(case.input).output,
)
report = suite.run(GoldenDataset.from_jsonl("./golden.jsonl"))
```

Add hardening:

```python
from ro_claude_kit_hardening import InjectionScanner, OutputValidator
```

## Try AgentLab — the live playground

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
│   ├── agent-patterns/       # core loop patterns
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

## License

MIT. See [LICENSE](LICENSE).

## Acknowledgements

Built for [Claude](https://www.anthropic.com/claude). Not affiliated with Anthropic.
