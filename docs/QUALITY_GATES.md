# Superpowers L4 Quality Gates

This repository vendors a curated Superpowers-style quality-gate skill for autonomous Codex + Symphony runs:

`.agents/skills/superpowers-l4-quality-gates/`

The goal is not to copy the whole Superpowers plugin into Docker. The goal is to make the autonomous path more reliable by enforcing the parts that matter most for Level 4 engineering work: planning, task execution, TDD, debugging, verification, review, and finishing.

## Included Workflows

- `writing-plans`
- `executing-plans`
- `test-driven-development`
- `systematic-debugging`
- `verification-before-completion`
- `requesting-code-review`
- `finishing-development-branch`

## Runtime Behavior

`WORKFLOW.md` requires the `superpowers-l4-quality-gates` skill and names each required workflow in front matter. The workflow prompt tells autonomous Codex runs to apply the gates at the correct lifecycle points.

In autonomous mode, the gates are non-interactive by default. When blocked, the agent must either make a safe assumption and record it in the plan and project memory, or escalate through the Jira escalation script.

## Evidence

Before PR or final handoff, autonomous runs must produce quality-gate evidence:

- Plan path and plan intent.
- Implementation task summary.
- TDD or debugging evidence.
- Validation commands and results.
- Review findings or self-review.
- Project memory records written.

The E2E scenario verifies the skill exists, the workflow requires it, and the Docker runtime can see the repo-owned skill files.
