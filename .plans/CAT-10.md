# Plan

Add dependency-aware Jira dispatch gating so the Symphony runner can safely work a long active backlog by dispatching only slices whose declared dependencies are terminal. This slice is limited to Jira polling eligibility; it does not add SQLite skip evidence, Jira issue-link parsing, status transitions, or Codex behavior changes.

## Vertical slice contract

### Slice outcome
The Symphony runner can poll a long active Jira backlog and dispatch only issues whose declared dependencies are terminal, skipping blocked issues safely.

### Behavior contract
Parse dependency declarations from Jira issue descriptions using explicit lines such as `Dependencies: CAT-6, CAT-7` and existing contract wording such as `Depends on CAT-6`. During live Jira polling, before returning issues to the supervisor for dispatch, resolve declared dependency issue statuses through Jira MCP. An active issue with no dependencies remains eligible. An active issue with all dependencies in configured terminal states remains eligible. An active issue with any dependency not terminal or not resolvable is skipped for that tick. Skipping blocked issues must not fail the whole poll when independent issues remain eligible. Existing Epic exclusion and active-state filtering must remain unchanged.

### Interface contract
Internal helpers in `src/symphony_l4_runner/mcp_proxy.py` may parse dependency text, build dependency JQL, and filter normalized Jira issues. The external supervisor interface remains `read_issues` returning `{"issues": [...]}`. No new CLI command is required.

### Data contract
Dependency declarations are Jira issue keys in text lines beginning with `Dependencies:` or `Depends on`. Terminal dependency statuses are compared against the workflow `terminal_states` argument already passed to `read_issues`. Returned issue dictionaries keep the existing shape expected by `Issue.from_mapping`. No raw prompts, connector commands, secrets, or OAuth material are persisted or returned.

### Non-goals
Do not add SQLite persistence of skipped or blocked reasons in this slice. Do not implement Jira issue-link dependency reading in this slice. Do not auto-transition Jira issues. Do not change Codex execution behavior after an issue is dispatched. Do not implement WIP limits beyond the existing runner behavior.

### Acceptance criteria
- [ ] Dependency parser extracts keys from `Dependencies: CAT-6, CAT-7`.
- [ ] Dependency parser extracts keys from `Depends on CAT-6` wording.
- [ ] Issues with non-terminal dependencies are filtered out before dispatch.
- [ ] Issues with terminal dependencies remain eligible.
- [ ] Issues with unresolved dependencies are filtered out fail-closed.
- [ ] Existing active Jira JQL still scopes project/status and excludes Epics.

### Verification contract
- [ ] `.venv/bin/python -m unittest tests.test_mcp_jira_adapter`
- [ ] `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
- [ ] `.venv/bin/python scripts/validate_repo.py`
- [ ] `PYTHONPATH=src .venv/bin/python -m symphony_l4_runner --workflow WORKFLOW.md --once --dry-run`
- [ ] Read-only Docker Jira probe confirms CAT-7/CAT-8 style dependent issues are skipped until dependencies are terminal.

### Independent verifier instructions
Review the completed diff against this contract. Confirm the implementation only gates Jira issue eligibility by declared dependencies, preserves Epic exclusion and active-state filtering, fails closed for unresolved dependencies, does not add SQLite persistence, does not read Jira issue links, and does not alter Codex dispatch semantics for eligible issues.

## Scope
- In: dependency text parsing, dependency status JQL builder, in-memory issue eligibility filtering, focused tests, and read-only probe evidence.
- Out: SQLite skip persistence, Jira issue links, Jira status transitions, Codex execution changes, WIP policy changes, and unrelated refactors.

## Action items
[ ] Add failing tests for dependency parsing from `Dependencies:` and `Depends on` lines.
[ ] Add failing tests for filtering terminal, non-terminal, and unresolved dependencies.
[ ] Add failing test or assertion that active issue JQL still excludes Epics.
[ ] Implement minimal dependency parser and dependency JQL builder.
[ ] Integrate dependency status lookup and filtering into live Jira `read_issues`.
[ ] Run targeted and full verification commands.
[ ] Run a read-only Docker Jira probe against CAT issues to confirm dependent backlog behavior.
[ ] Perform independent contract verification and prepare handoff evidence.

## Validation
- `.venv/bin/python -m unittest tests.test_mcp_jira_adapter`
- `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
- `.venv/bin/python scripts/validate_repo.py`
- `PYTHONPATH=src .venv/bin/python -m symphony_l4_runner --workflow WORKFLOW.md --once --dry-run`

## Assumptions
- CAT-9 is the parent Epic for dependency-aware autonomous dispatch.
- CAT-10 is the selected first safe implementation slice.
- Jira Link Issue permission may still be unavailable, so this slice intentionally reads dependency declarations from issue descriptions.
- Unknown dependency status should block the dependent issue for the current tick.

## Open questions
- None
