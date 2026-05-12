# Codex + Symphony L4 Hackathon Infra

This repository is a Dockerized starter system for Level 4 autonomous AI-assisted programming with Codex, OpenAI Symphony-style orchestration, Jira, and MCP connectors.

Run it with one command:

```bash
docker compose up
```

## What It Includes

- A Symphony-compatible supervisor loop in `src/symphony_l4_runner/`.
- A Jira planning skill at `.agents/skills/create-plan-symphony/`.
- Persisted plans in `.plans/`.
- Local long-term project memory in `.memory/` backed by SQLite.
- Repo-owned Superpowers L4 quality gates in `.agents/skills/superpowers-l4-quality-gates/`.
- A repository-owned workflow contract in `WORKFLOW.md`.
- MCP server configuration in `config/mcp.servers.yaml`.
- Secret redaction and guarded writes in `src/symphony_l4_runner/security.py`.
- Docker with Python 3.11, Node.js, Git, Playwright, and Codex CLI.

## Runtime Split

Use the Codex desktop app on your host machine. It is the human command center for supervising threads, reviewing diffs, and coordinating work.

Use Docker for autonomous execution. Inside the container, Symphony launches the headless Codex worker through `codex exec --skip-git-repo-check --ephemeral --sandbox workspace-write --ask-for-approval never -`, with `codex app-server` documented in `WORKFLOW.md` for orchestrators that speak the App Server protocol.

```text
Host desktop app -> Docker Compose -> Symphony supervisor -> Codex CLI/App Server -> MCP tools
```

The desktop app itself does not run inside Docker.

## Project Memory

This repo includes local long-term project memory for autonomous engineering runs. It is intentionally simple and inspectable: a SQLite database at `.memory/project-memory.sqlite3` with full-text search when SQLite FTS5 is available, plus a safe fallback search.

Use it from the host or container:

```bash
python scripts/project_memory.py init
python scripts/project_memory.py capture \
  --kind decision \
  --title "Validation policy" \
  --body "Run repository validation before merging." \
  --tag validation
python scripts/project_memory.py boot-context --issue-id HACK-123
```

The runner injects issue-aware boot context into the Codex prompt before execution. The `memory` MCP server exposes the same surface to agents: `capture`, `search`, `boot_context`, `record_run`, and `record_decision`. The workflow records plan, validation, and PR handoff checkpoints after major steps.

Memory is local-only and ignored by Git. Secret scanning rejects likely tokens, passwords, API keys, and authorization headers before any memory record is written.

## Superpowers L4 Quality Gates

Autonomous runs use a curated, repo-owned Superpowers workflow layer at `.agents/skills/superpowers-l4-quality-gates/`. This is included in the Docker workspace and does not depend on the desktop app plugin cache.

The included workflows are:

- `writing-plans`
- `executing-plans`
- `test-driven-development`
- `systematic-debugging`
- `verification-before-completion`
- `requesting-code-review`
- `finishing-development-branch`

`WORKFLOW.md` applies these gates at the plan, implementation, debugging, verification, review, and finish stages. In autonomous mode, blocked gates must either proceed with a logged safe assumption or escalate through Jira.

## Setup

1. Install Docker Desktop.
2. Sign in to Codex on the host machine:

```bash
codex login
```

Use your enterprise SSO provider such as Google, Okta, or Microsoft. This creates local Codex credentials under `~/.codex`.

3. Start the stack:

```bash
docker compose up
```

Docker mounts your credentials read-only:

```yaml
~/.codex:/root/.codex:ro
```

The container never copies credentials into the image or repository.

4. Run the local demo:

```bash
docker compose run --rm --no-deps symphony python scripts/demo_test_run.py
```

The demo confirms the container can see the Codex CLI, validates the App Server command name, renders a sample Symphony prompt, creates a sample workspace under `/workspace`, and performs a dry-run dispatch without contacting external services.
It also writes and searches a demo project-memory database in the throwaway demo workspace.

## Modes

Interactive mode is the default:

```bash
docker compose up
```

In this mode, `create-plan-symphony` may ask at most one or two multiple-choice questions only when blocked.

Autonomous mode:

```bash
SYMPHONY_MODE=autonomous docker compose up
```

In autonomous mode, the agent proceeds with logged assumptions or escalates the Jira issue to `needs-clarification` using `.agents/skills/create-plan-symphony/scripts/escalate_to_human.py`.

The compose file defaults to `SYMPHONY_DRY_RUN=true` so beginners can verify the stack without contacting live MCP services. To run live:

```bash
SYMPHONY_DRY_RUN=false SYMPHONY_MODE=autonomous docker compose up
```

## Security Model

Authentication is SSO-based through `codex login`. Do not add service tokens or API keys to this repository.

All external service access follows this boundary:

```text
Agent -> MCP -> External Service
```

The agent sees MCP tools, not external service credentials. The MCP layer handles authentication internally through SSO-backed local configuration.

Secret safety is enforced in three places:

- Logs pass through a redacting formatter.
- Plan persistence rejects likely secret material.
- MCP proxy calls reject likely secret material before it can be sent as tool input.

## MCP Tools

The required MCP server entries live in `config/mcp.servers.yaml`.

Core tools:

- `filesystem`: restricted to `/workspace`.
- `shell`: restricted command execution through `symphony_l4_runner.mcp_shell_server`.
- `memory`: local SQLite project memory for boot context, decisions, run summaries, and validation checkpoints.
- `browser`: Playwright MCP.

Service tools:

- `github`: clone, branch, commit, and PR operations with no main-branch commits.
- `jira`: read issues, create/update tickets, and change status.
- `notion`: create pages and manage docs.
- `miro`: create boards and diagrams.
- `figma`: UI generation and component updates.
- `lovable`: generate apps and iterate product ideas.
- `postgres`: local-only database access.
- `chroma`: local vector database access.

For enterprise MCP connectors, set command variables such as `MCP_JIRA_COMMAND` and `MCP_GITHUB_COMMAND` in your shell or Codex MCP configuration. These variables name connector commands; they must not contain secrets.

## Install Paths

- Skill path: `.agents/skills/create-plan-symphony/`
- Quality gates skill path: `.agents/skills/superpowers-l4-quality-gates/`
- Skill metadata: `.agents/skills/create-plan-symphony/agents/openai.yaml`
- Plan persistence script: `.agents/skills/create-plan-symphony/scripts/persist_plan.py`
- Escalation script: `.agents/skills/create-plan-symphony/scripts/escalate_to_human.py`
- Plan output directory: `.plans/`
- Project memory directory: `.memory/`
- Project memory CLI: `scripts/project_memory.py`
- Codex SSO credential directory on host: `~/.codex`
- Docker credential mount: `/root/.codex:ro`
- Workspace mount: `/workspace`

## Workflow

`WORKFLOW.md` defines the autonomous loop:

1. Load `superpowers-l4-quality-gates`.
2. Load project memory boot context for the Jira issue.
3. Invoke `create-plan-symphony` on a Jira issue.
4. Commit `.plans/<issue-id>.md` with `chore(plan): <issue-id> initial plan`.
5. Implement based on the plan with TDD/debugging gates.
6. Re-read the plan, summarize plan vs implementation differences, and record validation memory.
7. Open a PR with the plan path, validation summary, and Quality Gate Evidence.

## Validation

Run:

```bash
python scripts/validate_repo.py
python -m unittest discover -s tests
PYTHONPATH=src python -m symphony_l4_runner --workflow WORKFLOW.md --once --dry-run
docker compose run --rm --no-deps symphony python scripts/demo_test_run.py
```

The validation script checks skill YAML, `openai.yaml`, plan examples, required docs, both skill scripts, and the project-memory CLI.

## End-To-End Evidence Scenario

Run the full local proof scenario from the host:

```bash
python scripts/e2e_scenario.py
```

The scenario builds the Docker image, verifies Codex CLI/App Server inside Docker, confirms outbound research access, checks the read-only SSO credential mount, validates MCP declarations, exercises plan persistence, Jira escalation logging, SQLite project memory, secret rejection, the Symphony dry-run supervisor, and the bundled demo run.

Each run writes redacted proof artifacts under `evidence/e2e-<timestamp>/`. Review `evidence/e2e-<timestamp>/SUMMARY.md` for the pass/fail matrix and links to stdout/stderr logs.
