# examples/research-agent

End-to-end research agent built on the `ReActAgent` pattern with a toy knowledge-base search tool.

## Run

```bash
export ANTHROPIC_API_KEY=sk-ant-...
uv run python examples/research-agent/main.py "What is the ReAct pattern?"
```

## What it shows

- How to define a `Tool` with a JSON-schema input contract.
- How `ReActAgent` loops (reason → call tool → observe → loop).
- The shape of the typed `trace` you get back, for piping into Langfuse / your demo UI.

Swap the toy KB in `main.py` for real search (Tavily, Exa, Postgres full-text, your vector store) without changing the agent code.
