# Plan

Create the first safe implementation slice for the sample greenfield preflight initiative. This slice adds a local, read-only, no-secret configuration doctor command so an operator can check live-mode readiness before autonomous Jira polling. Work intake classification: existing concrete Jira implementation slice.

## Vertical slice contract

### Slice outcome
An operator can run a local preflight command before live mode and see whether required Symphony/Jira settings are present without exposing secrets.

### Behavior contract
Add a read-only local command, for example `python -m symphony_l4_runner doctor`. The command reports whether `JIRA_PROJECT_KEY`, `JIRA_CLOUD_ID`, `SYMPHONY_DRY_RUN`, `SYMPHONY_MODE`, and `MCP_JIRA_COMMAND` are present or missing. Missing optional `JIRA_CLOUD_ID` is allowed and should be reported as auto-discovery enabled. The command exits nonzero only when required live-mode configuration is missing or unsafe. It must not contact Jira or write state.

### Interface contract
CLI entrypoint: `python -m symphony_l4_runner doctor`. Internal code should live under `src/symphony_l4_runner/` and follow the existing CLI/module patterns. Tests should use the existing Python unittest style under `tests/`.

### Data contract
Reads environment variables only. Does not read Jira issue data. Does not write files, databases, Jira tickets, or project memory. Output must use redacted or presence-only fields, not raw credential-bearing values.

### Non-goals
Do not contact Jira MCP in this slice. Do not add JSON output in this slice. Do not change autonomous polling behavior. Do not refactor unrelated runner or MCP code.

### Acceptance criteria
- [ ] Running the command with valid live-mode env reports the project key and safe readiness status.
- [ ] Running the command without `JIRA_PROJECT_KEY` reports a blocking configuration error.
- [ ] Output does not include raw connector command values or credential material.
- [ ] Existing dry-run and validation behavior remains unchanged.

### Verification contract
- [ ] `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
- [ ] `.venv/bin/python scripts/validate_repo.py`
- [ ] `PYTHONPATH=src .venv/bin/python -m symphony_l4_runner doctor`
- [ ] Manual review confirms no credential-bearing environment values are printed.

### Independent verifier instructions
Review the completed diff against this contract. Confirm the implementation is limited to the local no-secret preflight command, does not contact Jira, does not write state, and does not include the later JSON or Docker documentation slices.

## Scope
- In: Add the local text preflight command, focused tests, and any minimal CLI routing needed for `doctor`.
- Out: Jira MCP calls, JSON output, Docker documentation, polling behavior changes, unrelated refactors, and implementation of CAT-3 or CAT-4.

## Action items
[ ] Inspect existing CLI entrypoint and config patterns.
[ ] Add failing tests for valid env, missing `JIRA_PROJECT_KEY`, optional `JIRA_CLOUD_ID`, and redacted output.
[ ] Implement the minimal doctor command and env evaluation logic.
[ ] Keep output presence-based and avoid raw connector command values.
[ ] Run the selected verification commands and capture evidence.
[ ] Perform an independent verifier pass against this contract.
[ ] Prepare PR handoff with CAT-2, this plan path, validation evidence, risks, and follow-up slices.

## Validation
- `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
- `.venv/bin/python scripts/validate_repo.py`
- `PYTHONPATH=src .venv/bin/python -m symphony_l4_runner doctor`
- `PYTHONPATH=src python -m symphony_l4_runner --workflow WORKFLOW.md --once --dry-run`

## Assumptions
- CAT-1 is the [TEST] parent Epic for this sample spec.
- CAT-2 is the selected first safe implementation slice.
- CAT-3 and CAT-4 are follow-up slices and must not be implemented with CAT-2.
- Jira issue links could not be created because the current Jira account lacks Link Issue permission for CAT-1; parent/dependency references are recorded in ticket descriptions instead.
- The parent checkout at `/workspace` is read-only in this Codex session, so implementation proceeds in writable clone `/workspace/CAT-2/repo` on branch `codex/cat-2-local-config-preflight`.

## Open questions
- None
