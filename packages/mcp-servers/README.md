# ro-claude-kit-mcp-servers

Reference MCP server templates. Read-only by default; write operations require explicit configuration. Auth via env vars.

## Status

| Server | Status |
|---|---|
| Postgres (read-only) | ✅ shipped |
| Stripe (read-only) | 🚧 planned |
| Linear | 🚧 planned |
| Slack | 🚧 planned |
| Notion | 🚧 planned |

## Postgres MCP server

Read-only SQL with two layers of defense:
1. Safety check rejects non-SELECT statements, multi-statement queries, `SELECT ... INTO`, and any query containing destructive keywords.
2. Defense-in-depth: in production, also bind the server to a Postgres role with SELECT-only privileges.

### Direct use (as an in-process tool)

```python
from ro_claude_kit_mcp_servers import PostgresQueryTool
import psycopg2

conn = psycopg2.connect(DATABASE_URL)
tool = PostgresQueryTool(connection=conn, max_rows=500)
rows = tool.query("SELECT id, email FROM users LIMIT 10")
```

Wire it into the agent-patterns toolkit:

```python
from ro_claude_kit_agent_patterns import Tool

pg = Tool(
    name="postgres_query",
    description=tool.description,
    input_schema={
        "type": "object",
        "properties": {"sql": {"type": "string"}},
        "required": ["sql"],
    },
    handler=tool.query,
)
```

### As an MCP server over stdio

```bash
pip install ro-claude-kit-mcp-servers[mcp,postgres]
export DATABASE_URL=postgres://readonly_user:...@host:5432/db
python -m ro_claude_kit_mcp_servers.postgres
```

Then point your MCP-aware client at the process.

### Safety check directly

If you want the safety check without the rest:

```python
from ro_claude_kit_mcp_servers import is_readonly_sql

allowed, reason = is_readonly_sql(user_sql)
if not allowed:
    raise BadInput(reason)
```

## Tests

```bash
uv run --frozen pytest packages/mcp-servers -q
```

Tests run against in-memory sqlite — no Postgres or `psycopg2` install needed.
