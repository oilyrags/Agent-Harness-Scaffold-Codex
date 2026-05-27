# Plan

Add a machine-readable JSON output mode to the existing local config doctor so automation can consume preflight results without parsing text. The slice keeps the CAT-2 text output unchanged, adds only the bounded `doctor --format json` interface, and verifies the JSON contains stable readiness fields without exposing raw connector command values.

## Vertical slice contract

### Slice outcome
Automation can run the local preflight command with JSON output and receive a structured readiness result for CAT-3.

### Behavior contract
`python -m symphony_l4_runner doctor` continues to emit the existing human-readable text output and exit with the same readiness code. `python -m symphony_l4_runner doctor --format json` evaluates the same environment checks, emits valid JSON to stdout, returns `0` when there are no blocking checks, returns `1` when blockers exist, includes blocking findings in `errors`, includes non-blocking findings in `warnings`, and represents auto-discovery notes without requiring a Jira MCP call. Unsupported format values fail during CLI parsing with a clear error and nonzero exit.

### Interface contract
Update `src/symphony_l4_runner/cli.py` so the `doctor` subcommand accepts `--format text` and `--format json`, with text as the default. Update `src/symphony_l4_runner/doctor.py` behind `run_doctor` so callers can choose the output format while preserving the existing `run_doctor(env, stdout)` behavior for text callers. Cover the interface through `tests/test_doctor.py` subprocess tests.

### Data contract
JSON mode reads environment variables only and writes JSON only to stdout. The top-level JSON object contains stable keys `ready`, `project_key_present`, `cloud_id_present`, `dry_run`, `mode`, `errors`, and `warnings`; it may include sanitized check metadata, but it must not include raw `MCP_JIRA_COMMAND` values, tokens, OAuth material, bearer strings, or secrets. `ready` is `true` exactly when no evaluated check is blocking.

### Non-goals
Do not contact Jira MCP from the doctor command. Do not change Docker Compose configuration, autonomous polling behavior, MCP proxy behavior, project memory behavior, or documentation/runbook content from CAT-4. Do not broaden the preflight beyond the existing environment checks.

### Acceptance criteria
- [ ] JSON mode emits syntactically valid JSON for both ready and blocked environment configurations.
- [ ] JSON mode preserves the same readiness decision and exit code as the existing text mode.
- [ ] JSON output includes the stable fields named in the CAT-3 data contract.
- [ ] JSON output omits raw connector command strings and other secret-bearing values.
- [ ] Existing text mode behavior and tests from CAT-2 still pass.

### Verification contract
- [ ] `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
- [ ] `.venv/bin/python scripts/validate_repo.py`
- [ ] `PYTHONPATH=src .venv/bin/python -m symphony_l4_runner doctor --format json`
- [ ] `PYTHONPATH=src .venv/bin/python -m symphony_l4_runner --workflow WORKFLOW.md --once --dry-run`
- [ ] Manual JSON parse check confirms stable fields and no raw connector command values.

### Independent verifier instructions
Compare the completed diff against CAT-3 and this plan. Confirm the change only adds machine-readable output for the existing local preflight behavior, default text output is preserved, JSON mode reports the stable contract fields, raw connector command values are absent, no Jira calls are added to the doctor command, and live-mode polling behavior is unchanged.

## Scope
- In: `src/symphony_l4_runner/cli.py`, `src/symphony_l4_runner/doctor.py`, and focused tests in `tests/test_doctor.py` for text compatibility, JSON output, blocked output, secret omission, and invalid format handling.
- Out: Jira MCP calls inside the doctor command, Docker Compose changes, workflow polling changes, project memory changes, docs/runbook updates, unrelated refactors, and additional preflight checks.

## Action items
[ ] Reconfirm the CAT-3 contract from Jira, repository instructions, and project memory boot context before implementation.
[ ] Add failing doctor CLI tests for `--format json`, blocked JSON output, redacted connector values, and invalid format handling.
[ ] Implement CLI parsing for the doctor subcommand with a default text format and explicit JSON format.
[ ] Implement structured doctor output from the existing check results while preserving text output and exit-code semantics.
[ ] Run the targeted doctor tests and use systematic debugging if any command fails unexpectedly.
[ ] Run the full validation commands listed in this plan, including the runtime dry-run check required by AGENTS.md.
[ ] Perform an independent contract verification pass for behavior, interface, data, acceptance criteria, unrelated changes, and plan drift.
[ ] Prepare PR handoff evidence with validation results, plan-vs-implementation differences, known risks, and quality-gate evidence.

## Validation
- `.venv/bin/python -m unittest tests.test_doctor`
- `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
- `.venv/bin/python scripts/validate_repo.py`
- `PYTHONPATH=src .venv/bin/python -m symphony_l4_runner doctor --format json`
- `PYTHONPATH=src .venv/bin/python -m symphony_l4_runner --workflow WORKFLOW.md --once --dry-run`
- Manual JSON parse and grep check for stable keys and absence of the sample raw connector command.

## Assumptions
- CAT-3 is an existing concrete implementation slice; no new child Jira tickets are needed.
- Project memory boot context for CAT-3 contains no prior durable records.
- The mounted `/workspace` repository is read-only for writes in this session, so implementation, commits, and validation are performed in the writable clone at `/workspace/CAT-3/repo`.

## Open questions
- None
