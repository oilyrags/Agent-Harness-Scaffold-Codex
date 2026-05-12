---
tracker:
  kind: jira
  source: mcp
  project_key_env: JIRA_PROJECT_KEY
  active_states:
    - To Do
    - In Progress
    - Selected for Development
    - needs-clarification
  terminal_states:
    - Done
    - Closed
    - Canceled
polling:
  interval_ms: 30000
workspace:
  root: /workspace
  plans_dir: /workspace/.plans
hooks:
  timeout_ms: 60000
  before_run: |
    python scripts/validate_repo.py
    python scripts/project_memory.py init >/dev/null
memory:
  db_path: /workspace/.memory/project-memory.sqlite3
  boot_context_limit: 8
  retention: local_sqlite
quality_gates:
  skill: superpowers-l4-quality-gates
  mode: curated_autonomous
  required_workflows:
    - writing-plans
    - executing-plans
    - test-driven-development
    - systematic-debugging
    - verification-before-completion
    - requesting-code-review
    - finishing-development-branch
  evidence_required: true
agent:
  max_concurrent_agents: 2
  max_turns: 20
  max_retry_backoff_ms: 300000
codex:
  host_surface: desktop_app
  container_surface: cli_or_app_server
  command: codex exec --skip-git-repo-check --ephemeral --sandbox workspace-write --ask-for-approval never -
  app_server_command: codex app-server
  turn_timeout_ms: 3600000
  read_timeout_ms: 5000
  stall_timeout_ms: 300000
mcp:
  config_path: config/mcp.servers.yaml
  required_servers:
    - filesystem
    - shell
    - memory
    - browser
    - github
    - jira
    - notion
    - miro
    - figma
    - lovable
    - postgres
    - chroma
security:
  auth: codex_login_sso
  codex_home: /root/.codex
  credential_mount: /root/.codex:ro
  api_keys_allowed: false
  output_redaction: true
---

# Symphony L4 Workflow

You are running inside the Codex + Symphony hackathon workspace for Jira issue `{{ issue.identifier }}`: `{{ issue.title }}`.

The Codex desktop app stays outside Docker as the human command center. Autonomous execution inside Docker uses the headless Codex CLI or App Server process configured in front matter.

Use only MCP connectors for external services. Credentials come from the read-only `/root/.codex` mount created by `codex login`; do not request, print, or write secrets.

## Quality Gate Preflight

Invoke `superpowers-l4-quality-gates` before planning. Use its curated Superpowers workflows throughout this run: writing plans, executing plans, test-driven development, systematic debugging, verification before completion, requesting code review, and finishing the development branch.

In autonomous mode, do not pause for broad process questions. If a quality gate is blocked, either proceed with an explicit safe assumption recorded in the plan and project memory, or escalate to Jira.

## Memory Preflight

Before Step 1, call the `memory` MCP server `boot_context` tool for `{{ issue.identifier }}` and include relevant durable context in the planning prompt. The SQLite database lives at `/workspace/.memory/project-memory.sqlite3`, is local-only, and must never contain secrets.

## Step 1

Invoke `create-plan-symphony` on Jira issue `{{ issue.identifier }}`.

The plan skill must read the Jira issue through MCP, read repository instructions, analyze relevant code, use project memory context when relevant, and generate a plan with Scope, Action items, Validation, Assumptions, and Open questions.

Quality Gate: apply `writing-plans` and record the selected validation commands.

## Step 2

Commit plan:

`.plans/{{ issue.identifier }}.md`

Commit message:

`chore(plan): {{ issue.identifier }} initial plan`

After the commit, call `memory.record_decision` or `memory.capture` with a compact summary of plan intent, assumptions, and validation strategy.

Quality Gate: apply `executing-plans` before implementation begins.

## Step 3

Implement code based on the persisted plan.

Use the Docker sandbox and `/workspace` for all file operations. Use MCP for filesystem, shell, memory, browser, GitHub, Jira, Notion, Miro, Figma, Lovable, Postgres, and Chroma access.

Quality Gate: apply `test-driven-development` for behavior-changing code and `systematic-debugging` before fixing any failed command.

## Step 4

Before PR:

- Re-read `.plans/{{ issue.identifier }}.md`.
- Generate a concise plan vs implementation diff summary.
- Run validation commands from the plan and repository docs.
- Call `memory.record_run` with the validation summary and implementation diff summary.

Quality Gate: apply `verification-before-completion` and `requesting-code-review`.

## Step 5

Open PR with:

- Plan path: `.plans/{{ issue.identifier }}.md`.
- Diff summary.
- Validation summary.
- Jira issue link.

Record the PR link and final handoff notes with `memory.record_run`.

Quality Gate: apply `finishing-development-branch` and include a Quality Gate Evidence section in the PR or handoff.

Do not commit directly to main.
