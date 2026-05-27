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
  command: codex exec --skip-git-repo-check --ephemeral --sandbox workspace-write -
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

## Work Intake Classification

Before planning, determine whether the input is an existing concrete implementation slice, a broad issue that needs child slices, a greenfield project with no Jira breakdown, or a missing Jira ticket reference.

Identify the first smallest useful vertical slice. Avoid planning broad feature batches, horizontal implementation layers, or multiple greenfield slices in one pass.

If the work is greenfield or lacks child implementation tickets, create or propose a parent Jira issue or Epic, decompose the initiative into contract-first vertical slices, create one Jira ticket per contracted slice, create enabling-task tickets only when necessary, make dependencies explicit, and select the first safe, reversible, independently testable slice for implementation.

Create slice tickets autonomously only when the project goal is clear enough, no destructive or privileged action is required, slices are reversible and independently verifiable, and assumptions are recorded. Escalate to Jira instead of coding when the product goal is ambiguous, ownership or repository target is unclear, required external system behavior is unknown, ticket creation would affect a production process without approval, or the first reversible slice cannot be identified safely.

When one slice depends on another, declare the dependency in the Jira issue description with parser-friendly wording such as `Dependencies: CAT-6` or `Depends on CAT-6`. The supervisor skips active issues with non-terminal or unresolved dependencies before dispatching Codex.

## Step 1

Invoke `create-plan-symphony` on Jira issue `{{ issue.identifier }}`.

The plan skill must read the Jira issue through MCP, read repository instructions, analyze relevant code, use project memory context when relevant, and generate a plan with Vertical slice contract, Scope, Action items, Validation, Assumptions, and Open questions.

The `create-plan-symphony` plan must include a `Vertical slice contract` section defining slice outcome, behavior contract, interface contract, data contract if applicable, non-goals, acceptance criteria, verification contract, independent verifier instructions, and dependencies or ordering notes when applicable.

If the Jira issue is too broad, select or create the first safe contracted slice and record assumptions. If no Jira slice tickets exist for a greenfield project, create the contracted Jira slice tickets before implementation. If ticket creation is unsafe or ambiguous, escalate to Jira instead of coding.

Quality Gate: apply `writing-plans` and record the selected validation commands.

## Step 2

Commit plan:

`.plans/{{ issue.identifier }}.md`

Persist only the selected implementation slice plan to `.plans/{{ issue.identifier }}.md`. Record any greenfield slice breakdown, assumptions, dependencies, ordering notes, and ticket creation results in project memory.

Commit message:

`chore(plan): {{ issue.identifier }} initial plan`

After the commit, call `memory.record_decision` or `memory.capture` with a compact summary of plan intent, assumptions, and validation strategy.

Quality Gate: apply `executing-plans` before implementation begins.

## Step 3

Implement code based on the persisted plan. Implement only the selected slice, not the entire initiative or multiple greenfield slices in one pass.

Use the Docker sandbox and `/workspace` for all file operations. Use MCP for filesystem, shell, memory, browser, GitHub, Jira, Notion, Miro, Figma, Lovable, Postgres, and Chroma access.

Do not perform unrelated refactors, silently expand scope, or invent product behavior outside the contract. If implementation requires changing the contract, stop and update the persisted plan before changing code.

Quality Gate: apply `test-driven-development` for behavior-changing code and `systematic-debugging` before fixing any failed command.

## Step 4

Before PR:

- Re-read `.plans/{{ issue.identifier }}.md`.
- Generate a concise plan vs implementation diff summary.
- Run validation commands from the plan and repository docs.
- Run an independent verifier pass that compares the implementation against the persisted contract.
- Check behavior contract alignment, interface contract alignment, data contract alignment, acceptance criteria, verification evidence, unrelated file changes, hidden scope expansion, and plan-vs-implementation drift.
- Call `memory.record_run` with the validation summary and implementation diff summary.

Verification evidence, including independent verifier evidence, must be recorded before PR handoff.

Quality Gate: apply `verification-before-completion` and `requesting-code-review`.

## Step 5

Open PR with:

- Jira issue id: `{{ issue.identifier }}`.
- Plan path: `.plans/{{ issue.identifier }}.md`.
- Slice delivered.
- Contract implemented.
- Validation summary.
- Independent verifier evidence.
- Plan-vs-implementation differences.
- Known risks.
- Follow-up slices.
- Jira issue link.

Record the PR link and final handoff notes with `memory.record_run`.

Quality Gate: apply `finishing-development-branch` and include a Quality Gate Evidence section in the PR or handoff.

Do not commit directly to main.
