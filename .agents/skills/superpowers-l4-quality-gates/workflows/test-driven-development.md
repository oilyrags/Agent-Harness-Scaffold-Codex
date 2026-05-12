# Test-Driven Development Gate

Use this gate before behavior-changing code edits.

## Requirements

- Write a focused failing test before production behavior changes.
- Run the test and confirm it fails for the expected reason.
- Implement the smallest change that makes the test pass.
- Re-run the focused test and the relevant broader suite.
- Refactor only after tests are green.

## Exceptions

For docs-only, config-only, or generated evidence changes, explain why TDD is not applicable and run structural validation instead.

## Evidence

The run must preserve:

- Failing test command and failure summary.
- Passing test command and result.
- Broader validation command and result.
- Reason when TDD is not applicable.
