# Agent Operating Rules

This repository is built for Codex + Symphony autonomous execution against Jira-backed work.

## Security

- Authenticate with `codex login`; do not use OpenAI, Jira, GitHub, Notion, Miro, Figma, or Lovable API keys.
- Treat `/root/.codex` as a read-only credential boundary inside Docker.
- Access external services through MCP only: Agent -> MCP -> External Service.
- Do not print, persist, commit, or summarize secrets. Use the redaction layer in `symphony_l4_runner.security`.

## Workflow

- Use Jira issue identifiers such as `HACK-123`; do not introduce other tracker terminology.
- Create and persist plans under `.plans/<issue-id>.md`.
- Follow `WORKFLOW.md` for plan, implementation, validation, and PR handoff.
- Do not commit directly to `main`.

## Validation

- Run `python scripts/validate_repo.py` after editing repository structure or skill files.
- Run `python -m symphony_l4_runner --workflow WORKFLOW.md --once --dry-run` before changing runtime behavior.
