---
name: superpowers-l4-quality-gates
description: Curated Superpowers workflow gates for Codex + Symphony autonomous L4 programming runs, adapted for Jira, MCP, Docker, and evidence-backed completion.
---

# Superpowers L4 Quality Gates

Use this skill whenever a Symphony autonomous run asks for Superpowers workflows, quality gates, Level 4 execution discipline, or evidence-backed completion.

This is a repo-owned, curated subset of Superpowers-style workflows for autonomous Codex execution. It is intentionally smaller than the full plugin: only the workflows that improve long-running engineering reliability are mandatory.

## Required Workflows

Load and apply the relevant workflow files from `workflows/`:

- `writing-plans.md`: before implementation or plan revision.
- `executing-plans.md`: while implementing a persisted plan.
- `test-driven-development.md`: before behavior-changing code edits.
- `systematic-debugging.md`: before fixing failing tests or unexpected behavior.
- `verification-before-completion.md`: before any completion, PR, merge, or success claim.
- `requesting-code-review.md`: before PR or merge.
- `finishing-development-branch.md`: when wrapping a branch or PR handoff.

## Autonomous Mode Rules

When `SYMPHONY_MODE=autonomous`:

- Do not ask open-ended questions unless the work is blocked and no safe assumption exists.
- If blocked, either proceed with an explicit assumption recorded in `.plans/<issue-id>.md` and project memory, or escalate through the Jira escalation script.
- Treat validation output as evidence. Do not claim success until commands have been run and read.
- Record major decisions, assumptions, validation summaries, and handoff notes through the `memory` MCP server or `scripts/project_memory.py`.
- Use MCP for external services. Do not request, print, or persist secrets.

## Gate Order

1. **Plan Gate:** read Jira, repo instructions, project memory, and create a concrete plan.
2. **Implementation Gate:** execute the plan task-by-task; use TDD for behavior changes.
3. **Debugging Gate:** when anything fails, investigate root cause before fixing.
4. **Verification Gate:** run the plan validation commands and repository validation.
5. **Review Gate:** produce a plan-vs-implementation diff and perform review before PR.
6. **Finish Gate:** create PR/handoff evidence and record final memory.

## Required Output

Before PR or final handoff, include a short quality-gate evidence summary:

```markdown
## Quality Gate Evidence

- Plan gate: <plan path and summary>
- Implementation gate: <tasks completed>
- TDD/debugging gate: <tests added or reason not applicable>
- Verification gate: <commands and pass/fail result>
- Review gate: <diff summary and review result>
- Memory gate: <records written>
```

If any gate cannot be completed, stop the autonomous run or escalate to Jira with the reason.
