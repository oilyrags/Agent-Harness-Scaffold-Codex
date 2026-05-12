# Finishing Development Branch Gate

Use this gate when implementation and verification are complete.

## Requirements

- Verify the working tree state.
- Re-run required validation before final handoff.
- Re-read the plan and produce a plan-vs-implementation diff summary.
- Record final validation and handoff notes in project memory.
- Open a PR through GitHub MCP when live connectors are available.
- Do not commit directly to `main` during autonomous workflow execution.

## Local Merge Exception

Manual local merge is allowed only when the human operator explicitly requests it after successful validation. The merge itself must happen outside the autonomous issue workflow or as a supervised final action.

## Evidence

The run must preserve:

- Final validation commands and results.
- Plan-vs-implementation diff summary.
- PR link or local merge commit.
- Final memory record.
