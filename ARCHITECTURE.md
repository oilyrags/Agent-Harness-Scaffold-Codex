# Architecture

## Runtime Shape

The system runs as a Docker Compose stack. The `symphony` service mounts this repository at `/workspace` and mounts host Codex credentials at `/root/.codex:ro`.

```text
Host Codex desktop app -> Docker Compose -> Symphony supervisor -> Codex CLI/App Server -> MCP proxy -> MCP servers -> external services
```

The desktop app remains outside Docker. Docker runs only the headless execution surface: Codex CLI via `codex exec`, or Codex App Server via `codex app-server` for orchestrators that implement the App Server protocol.

## Components

- `WORKFLOW.md`: repository-owned Symphony contract with tracker, workspace, agent, MCP, and security settings.
- `src/symphony_l4_runner/supervisor.py`: long-running poll loop and dispatch boundary.
- `src/symphony_l4_runner/mcp_proxy.py`: MCP-only external-service access and workspace path enforcement.
- `src/symphony_l4_runner/memory.py`: local SQLite project memory with secret rejection and issue-aware boot context.
- `src/symphony_l4_runner/mcp_memory_server.py`: MCP surface for memory capture, search, run checkpoints, and decisions.
- `src/symphony_l4_runner/agent_runner.py`: Codex CLI subprocess handoff for autonomous execution, including issue-aware memory boot context injection.
- `src/symphony_l4_runner/security.py`: redaction, secret-write rejection, and path containment helpers.
- `.agents/skills/create-plan-symphony/`: Jira-backed planning skill and deterministic helper scripts.
- `.agents/skills/superpowers-l4-quality-gates/`: repo-owned autonomous planning, TDD, debugging, verification, review, and finishing gates.

## Data Flow

1. The supervisor loads `WORKFLOW.md`.
2. The supervisor validates `config/mcp.servers.yaml`.
3. The workflow requires `superpowers-l4-quality-gates`.
4. The runner loads a compact boot context from `.memory/project-memory.sqlite3`.
5. Jira issues are read through the Jira MCP server.
6. Each issue gets a deterministic workspace under `/workspace`.
7. `create-plan-symphony` persists `.plans/<issue-id>.md`.
8. Codex executes the workflow in the issue workspace using quality gates for plan, TDD/debugging, verification, review, and finish stages.
9. Plan, validation, and handoff checkpoints are recorded to project memory.
10. GitHub PR operations happen through MCP.

## Project Memory

Project memory is local-first. The default database is `/workspace/.memory/project-memory.sqlite3`, mounted from the repository directory but ignored by Git. It stores compact decisions, assumptions, run summaries, validation checkpoints, and handoff notes.

The implementation uses SQLite because it is durable, beginner-friendly, and needs no extra service. When SQLite FTS5 is available, searches use full-text ranking. If FTS5 is unavailable, the same API falls back to parameterized `LIKE` search. Chroma remains available as a separate MCP for vector workflows, but durable engineering memory starts with SQLite so the system works with `docker compose up`.

## Security Boundaries

- Credentials remain in host `~/.codex`.
- Docker mounts credentials read-only at `/root/.codex`.
- The desktop app reads host configuration directly and is never copied into the container.
- External services are accessed through MCP only.
- Logs and plan writes use redaction and secret rejection.
- Project memory rejects likely secret material before writing.
- Filesystem and shell tools are restricted to `/workspace`.
