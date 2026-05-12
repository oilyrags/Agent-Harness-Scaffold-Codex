# Requesting Code Review Gate

Use this gate before PR or local merge.

## Requirements

- Compare implementation against `.plans/<issue-id>.md`.
- Review correctness, security, secret handling, test coverage, and workflow compliance.
- If a reviewer agent is available, request review with a focused diff and requirements summary.
- If no reviewer agent is available in the autonomous runtime, perform a self-review and record it in the quality-gate evidence.
- Fix critical and important findings before PR or merge.

## Evidence

The run must preserve:

- Base and head commit or diff summary.
- Review findings.
- Fixes made from review.
- Explicit residual risks or test gaps.
