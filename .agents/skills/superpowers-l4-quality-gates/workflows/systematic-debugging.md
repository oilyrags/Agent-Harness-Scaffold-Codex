# Systematic Debugging Gate

Use this gate before fixing failed tests, build errors, or unexpected runtime behavior.

## Requirements

- Read the full error output.
- Reproduce the failure with the smallest command.
- Check recent changes that could explain the failure.
- Identify the failing component boundary.
- Form one hypothesis and test it with the smallest change.
- Fix root cause, not symptoms.

## Stop Conditions

Stop or escalate when:

- The failure cannot be reproduced.
- Three independent fix attempts fail.
- The issue indicates an architecture mismatch with the plan.

## Evidence

The run must preserve:

- Reproduction command.
- Root-cause hypothesis.
- Fix summary.
- Verification command that proves the issue is resolved.
