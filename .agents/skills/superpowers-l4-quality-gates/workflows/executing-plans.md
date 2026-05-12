# Executing Plans Gate

Use this gate while implementing a persisted plan.

## Requirements

- Re-read `.plans/<issue-id>.md` before editing code.
- Execute action items in order unless a dependency requires a documented reorder.
- Keep changes scoped to the plan and existing repository patterns.
- Mark or summarize completed action items in the run evidence.
- Record important decisions or deviations in project memory.

## Stop Conditions

Stop or escalate when:

- The plan has a critical gap.
- A validation command repeatedly fails after root-cause investigation.
- External credentials or unsafe secrets would be needed.
- The work would require direct commits to `main`.

## Evidence

The run must preserve:

- Completed action-item summary.
- Any plan deviations and reasons.
- Files changed.
- Memory record for implementation checkpoint.
