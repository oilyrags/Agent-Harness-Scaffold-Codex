# Plan

Implement the Jira-backed onboarding task by adding the smallest production path first: read the issue through MCP, prepare the workspace, make the requested code change, and validate it before opening a PR.

## Vertical slice contract

### Slice outcome
The selected Jira issue is delivered as one independently testable behavior with a persisted plan and PR-ready evidence.

### Behavior contract
The agent reads the Jira issue through MCP, plans only the selected implementation slice, applies the requested code change, runs the selected validation commands, and prepares PR handoff evidence. The implementation must not add unrelated behavior, broaden the feature scope, or skip the persisted plan.

### Interface contract
The slice may use Jira MCP reads, repository files named in the plan, `.plans/<issue-id>.md`, validation commands from `README.md` or `AGENTS.md`, and the PR handoff summary. It must not use direct Jira API credentials or non-MCP external service access.

### Data contract
Plan files remain Markdown under `.plans/` and must not contain secrets. Project memory may record compact decisions, assumptions, validation summaries, and handoff notes without credentials or sensitive values.

### Non-goals
Do not implement unrelated Jira issues, alternate tracker workflows, production deployment, broad refactors, or additional greenfield slices beyond the selected issue.

### Acceptance criteria
- [ ] The selected Jira behavior is implemented as one bounded, testable slice.
- [ ] The persisted plan records scope, validation, assumptions, and open questions for the selected issue.
- [ ] The implementation diff contains no unrelated file changes or hidden scope expansion.
- [ ] PR handoff evidence links the plan and validation summary.

### Verification contract
- [ ] Run `python scripts/validate_repo.py`.
- [ ] Run the project-specific tests named in `README.md` or `AGENTS.md`.
- [ ] Re-read `.plans/<issue-id>.md` and compare the completed diff against this contract.

### Independent verifier instructions
Review the completed diff against the persisted contract. Confirm behavior, interface, and data alignment; verify acceptance criteria and validation evidence; flag unrelated changes, hidden scope expansion, and plan-vs-implementation drift.

## Scope
- In: Jira issue discovery, focused code updates, tests, plan persistence, and PR-ready summary.
- Out: Direct Jira API authentication, alternate tracker workflows, unrelated refactors, and production deployment.

## Action items
[ ] Read the Jira issue through the Jira MCP server and capture the requested behavior.
[ ] Review README.md, AGENTS.md, WORKFLOW.md, and relevant source files for project constraints.
[ ] Create or update the branch for the Jira issue without committing to main.
[ ] Implement the smallest code change that satisfies the issue.
[ ] Add or update tests that prove the requested behavior and edge case handling.
[ ] Run the repository validation commands and capture failures for follow-up.
[ ] Re-read this plan and summarize plan-versus-implementation differences.
[ ] Open a PR that links this plan path and includes the validation summary.

## Validation
- Run `python scripts/validate_repo.py`.
- Run the project-specific tests named in README.md or AGENTS.md.

## Assumptions
- Jira MCP is authenticated through the operator's SSO-backed Codex session.

## Open questions
- None.
