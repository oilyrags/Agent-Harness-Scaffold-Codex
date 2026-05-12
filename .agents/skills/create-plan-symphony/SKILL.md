---
name: create-plan-symphony
description: Create and persist a Symphony-compatible implementation plan from a Jira issue. Use when planning Codex autonomous work from Jira, when a workflow asks to create a plan before implementation, or when SYMPHONY_MODE is interactive or autonomous.
metadata:
  short-description: Create Jira Symphony plans
---

# Create Plan Symphony

## Goal

Create a concise, executable Symphony plan from a Jira issue, persist it to `.plans/<issue-id>.md`, and keep the planning workflow safe for autonomous Codex execution.

This skill is a Jira-focused adaptation of OpenAI's experimental `create-plan` skill. It keeps the same small-plan discipline, but adds Jira input, Symphony workflow handoff, local persistence, and autonomous escalation behavior.

## Required Inputs

- Jira issue identifier, such as `HACK-123`.
- Repository root mounted at `/workspace`.
- Jira access through MCP only. Do not call Jira directly from the agent and do not request API keys.

## Required Context Scan

Before writing the plan, read:

1. The Jira issue through the Jira MCP server.
2. `README.md`.
3. `AGENTS.md` if it exists.
4. `CLAUDE.md` if it exists.
5. `ARCHITECTURE.md` if it exists.
6. Relevant code and configuration files needed to make the plan concrete.

## Modes

### Interactive Mode

This is the default. Ask at most one or two multiple-choice questions only when a missing answer blocks responsible planning. If a reasonable assumption is safe, proceed and record it in `## Assumptions`.

### Autonomous Mode

Autonomous mode is enabled when `SYMPHONY_MODE=autonomous`.

If blocked, choose one of these paths:

- Proceed with a clearly stated assumption and log it in `## Assumptions`.
- Escalate to Jira with:

```bash
python .agents/skills/create-plan-symphony/scripts/escalate_to_human.py \
  --issue-id <issue-id> \
  --reason "<short blocker reason>"
```

Do not ask the operator questions in autonomous mode.

## Required Plan Structure

Output exactly this structure:

```markdown
# Plan

<Intent paragraph: 1-3 sentences describing what will be done, why, and the high-level approach.>

## Scope
- In:
- Out:

## Action items
[ ] <Step 1>
[ ] <Step 2>
[ ] <Step 3>
[ ] <Step 4>
[ ] <Step 5>
[ ] <Step 6>

## Validation
- <Validation command or check>

## Assumptions
- <Assumption or "None">

## Open questions
- <Question or "None">
```

Action items must contain 6-10 verb-first, ordered items. Include discovery, implementation, tests, edge cases or risk, and PR handoff.

## Persistence

Persist the final plan locally before implementation:

```bash
python .agents/skills/create-plan-symphony/scripts/persist_plan.py \
  --issue-id <issue-id> \
  --plans-dir .plans < /tmp/plan.md
```

The script writes `.plans/<issue-id>.md` atomically, validates required sections, and rejects likely secret material.

## Safety Rules

- Use Jira MCP for issue tracking.
- Use SSO-derived local credentials through `codex login`; never ask for API keys.
- Do not log or persist secrets.
- Do not write outside `.plans/` when persisting a plan.
- Do not proceed to implementation until the plan has been written successfully.
