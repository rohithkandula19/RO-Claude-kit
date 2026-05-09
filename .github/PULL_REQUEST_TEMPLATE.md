<!-- Thanks for the PR. Fill out everything below — incomplete PRs get closed without review. -->

## What does this change?

<!-- One paragraph. Why is this change needed? -->

## How does it work?

<!-- Walk through the approach. Mention anything subtle or non-obvious. -->

## Test plan

- [ ] Added / updated tests covering the change
- [ ] `uv run pytest packages/agent-patterns packages/eval-suite packages/memory packages/hardening packages/mcp-servers packages/cli apps/demo -q` passes locally
- [ ] (If user-facing) Tried it in the CLI / demo app and confirmed the output is right

## Checklist

- [ ] No vendor SDK added as a hard dependency (use `httpx` + an optional extra if needed)
- [ ] No write paths added to MCP servers (gate via `ApprovalGate` in user code instead)
- [ ] Docs / CHANGELOG updated if user-facing
- [ ] Commit message is imperative ("add X", not "added X")

## Related issues

<!-- Closes #XX, refs #YY -->
