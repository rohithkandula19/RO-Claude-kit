"""Reference MCP server templates.

Currently shipped:
- ``postgres`` — read-only SQL with safety check, pluggable connection backend.

Planned (Week 2 follow-up): Stripe, Linear, Slack, Notion.
"""
from .postgres import (
    DangerousSQLError,
    PostgresQueryTool,
    is_readonly_sql,
    run_query,
)

__all__ = [
    "DangerousSQLError",
    "PostgresQueryTool",
    "is_readonly_sql",
    "run_query",
]
