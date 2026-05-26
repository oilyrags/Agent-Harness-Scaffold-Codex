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
- Use `.agents/skills/superpowers-l4-quality-gates/` for autonomous planning, TDD, debugging, verification, review, and branch finishing gates.
- Do not commit directly to `main`.

## Contract-First Vertical Slicing

- All coding work must be delivered as contract-first vertical slices.
- A builder may implement only one bounded, testable behavior at a time.
- Each slice must define behavior contract, interface contract, data contract if applicable, non-goals, acceptance criteria, verification contract, and independent verifier instructions.
- Horizontal-only tasks are not valid implementation slices unless explicitly marked as enabling work with their own verification path.
- Do not proceed to implementation until the persisted plan contains the vertical slice contract.
- If Jira tickets do not exist for a greenfield project, create the required contracted Jira slices before coding.
- Implement only the selected contracted slice, not the entire initiative.

## Validation

- Run `python scripts/validate_repo.py` after editing repository structure or skill files.
- Run `python -m symphony_l4_runner --workflow WORKFLOW.md --once --dry-run` before changing runtime behavior.
