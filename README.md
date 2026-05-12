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
- Skill metadata: `.agents/skills/create-plan-symphony/agents/openai.yaml`
- Plan persistence script: `.agents/skills/create-plan-symphony/scripts/persist_plan.py`
- Escalation script: `.agents/skills/create-plan-symphony/scripts/escalate_to_human.py`
- Plan output directory: `.plans/`
- Codex SSO credential directory on host: `~/.codex`
- Docker credential mount: `/root/.codex:ro`
- Workspace mount: `/workspace`

## Workflow

`WORKFLOW.md` defines the autonomous loop:

1. Invoke `create-plan-symphony` on a Jira issue.
2. Commit `.plans/<issue-id>.md` with `chore(plan): <issue-id> initial plan`.
3. Implement based on the plan.
4. Re-read the plan and summarize plan vs implementation differences.
5. Open a PR with the plan path and validation summary.

## Validation

Run:

```bash
python scripts/validate_repo.py
python -m symphony_l4_runner --workflow WORKFLOW.md --once --dry-run
docker compose run --rm --no-deps symphony python scripts/demo_test_run.py
```

The validation script checks skill YAML, `openai.yaml`, plan examples, required docs, and both skill scripts.
