# Project Memory

Project memory gives long-running autonomous runs a durable local context store without adding another service or secret boundary.

## Storage

- Database: `.memory/project-memory.sqlite3`
- Container path: `/workspace/.memory/project-memory.sqlite3`
- Docker environment: `PROJECT_MEMORY_DB=/workspace/.memory/project-memory.sqlite3`
- Git status: ignored by `.gitignore`

The schema stores memory records and run events. Records include kind, title, body, issue id, source, tags, confidence, timestamps, and secret scan status.

Search uses SQLite FTS5 when available. If the Python SQLite build does not include FTS5, the same API falls back to safe parameterized text search.

## CLI

Initialize memory:

```bash
python scripts/project_memory.py init
```

Capture a decision:

```bash
python scripts/project_memory.py capture \
  --kind decision \
  --title "Use local memory" \
  --body "Store compact autonomous run context in SQLite." \
  --issue-id HACK-123 \
  --tag architecture
```

Search:

```bash
python scripts/project_memory.py search "local memory" --issue-id HACK-123
```

Generate boot context:

```bash
python scripts/project_memory.py boot-context --issue-id HACK-123
```

Record a validation checkpoint:

```bash
python scripts/project_memory.py record-run \
  --issue-id HACK-123 \
  --event-type validation \
  --summary "Repository validation and Docker demo passed."
```

## MCP Surface

The `memory` MCP server runs with:

```bash
python -m symphony_l4_runner.mcp_memory_server
```

Tools:

- `capture`: store a non-secret memory record.
- `search`: find relevant memories.
- `boot_context`: produce compact context for a Jira issue.
- `record_run`: store autonomous execution checkpoints.
- `record_decision`: store durable decisions and assumptions.

## Workflow Usage

`WORKFLOW.md` requires memory in the MCP server list. Autonomous runs should:

1. Let the runner inject issue-aware `boot_context` before invoking `create-plan-symphony`.
2. Record plan intent and assumptions after `.plans/<issue-id>.md` is committed.
3. Record validation results and plan-vs-implementation diff before PR.
4. Record PR handoff notes after opening the PR.

## Security

Memory writes call the same secret detection used by the rest of the runner. Likely API keys, tokens, passwords, client secrets, authorization headers, and OpenAI-style secret keys are rejected before SQLite writes occur.

Do not put credentials, raw connector responses, access tokens, or private customer data in project memory.
