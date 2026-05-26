---
name: create-plan-symphony
description: Create and persist a Symphony-compatible implementation plan from a Jira issue. Use when planning Codex autonomous work from Jira, when a workflow asks to create a plan before implementation, or when SYMPHONY_MODE is interactive or autonomous.
metadata:
  short-description: Create Jira Symphony plans
---

# Create Plan Symphony

## Goal

Create a concise, executable Symphony plan for one contract-first vertical slice from a Jira issue, persist it to `.plans/<issue-id>.md`, and keep the planning workflow safe for autonomous Codex execution.

This skill is a Jira-focused adaptation of OpenAI's experimental `create-plan` skill. It keeps the same small-plan discipline, but adds Jira input, Symphony workflow handoff, local persistence, and autonomous escalation behavior.

## Required Inputs

- Jira issue identifier, such as `HACK-123`.
- Repository root mounted at `/workspace`.
- Jira access through MCP only. Do not call Jira directly from the agent and do not request API keys.

## Required Context Scan

Before writing the plan, read:

1. The Jira issue through the Jira MCP server.
2. Existing linked or child Jira issues when the issue may be broad or greenfield.
3. Project memory through the configured memory MCP context when available.
4. `README.md`.
5. `AGENTS.md` if it exists.
6. `CLAUDE.md` if it exists.
7. `ARCHITECTURE.md` if it exists.
8. Relevant code and configuration files needed to make the plan concrete.

## Work Item Classification

Before planning, classify the input as exactly one of:

- Existing concrete Jira implementation slice.
- Broad Jira issue that needs child slices.
- Greenfield project with no Jira breakdown.
- Missing or nonexistent Jira issue reference.

If the item is already a concrete implementation slice, plan only that slice. If the item is broad, greenfield, or missing, do not proceed directly to coding from the broad request.

For greenfield work or broad issues without child implementation tickets:

1. Create or propose a parent Jira issue or Epic for the initiative.
2. Decompose the initiative into the smallest useful contract-first vertical slices.
3. Create one Jira ticket per contracted vertical slice.
4. Create enabling-task tickets only when necessary and give each one its own verification path.
5. Make dependencies and ordering explicit.
6. Select the first safe, reversible, independently testable slice for implementation.

Each generated Jira slice ticket must include slice outcome, behavior contract, interface contract, data contract if applicable, non-goals, acceptance criteria, verification contract, independent verifier instructions, and dependencies or ordering notes when applicable.

Create slice tickets autonomously only when the project goal is clear enough to define initial delivery slices, no destructive or privileged action is required, slices are reversible and independently verifiable, and assumptions are recorded clearly.

Escalate instead of creating tickets when the product goal is ambiguous, ownership or repository target is unclear, required external system behavior is unknown, ticket creation would affect a real production process without approval, or the first reversible slice cannot be identified safely.

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

## Vertical slice contract

### Slice outcome
<User-visible or API-visible outcome delivered by this slice.>

### Behavior contract
<Observable behavior, inputs, outputs, state changes, and edge cases.>

### Interface contract
<Routes, commands, components, functions, schemas, events, files, or APIs involved.>

### Data contract
<Fields, validation rules, defaults, migrations, compatibility rules, or "None".>

### Non-goals
<Explicit out-of-scope behavior and files/systems not to change.>

### Acceptance criteria
- [ ] <Observable criterion>
- [ ] <Observable criterion>

### Verification contract
- [ ] <Command, test, review, screenshot, log, or manual check>

### Independent verifier instructions
<Specific instructions for a verifier reviewing the completed diff against this contract.>

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

Action items must contain 6-10 verb-first, ordered items. Include discovery, contract review, implementation, tests, independent verification, edge cases or risk, and PR handoff.

The plan must select one bounded, independently testable implementation slice. Horizontal-only tasks are valid only when explicitly marked as enabling work with their own verification path. Do not plan a broad feature batch or an entire greenfield initiative in one implementation plan.

## Persistence

Persist the final plan locally before implementation:

```bash
python .agents/skills/create-plan-symphony/scripts/persist_plan.py \
  --issue-id <issue-id> \
  --plans-dir .plans < /tmp/plan.md
```

The script writes `.plans/<issue-id>.md` atomically, validates required sections including `## Vertical slice contract`, and rejects likely secret material.

## Safety Rules

- Use Jira MCP for issue tracking.
- Use SSO-derived local credentials through `codex login`; never ask for API keys.
- Do not log or persist secrets.
- Do not write outside `.plans/` when persisting a plan.
- Do not proceed to implementation until the selected slice plan has been written successfully.
- Do not implement multiple greenfield slices in one pass.
- If the contract must change, update and re-persist the plan before implementation continues.
