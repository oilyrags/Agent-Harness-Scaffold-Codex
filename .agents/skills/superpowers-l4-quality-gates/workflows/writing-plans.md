# Writing Plans Gate

Use this gate before implementation begins or whenever a plan is materially revised.

## Requirements

- Start from the Jira issue, repository instructions, and project memory boot context.
- Persist the plan under `.plans/<issue-id>.md`.
- Include intent, in/out scope, 6-10 action items, validation, assumptions, and open questions.
- Break implementation into small tasks with exact files and commands.
- Avoid placeholders such as "TBD", "TODO", "handle edge cases", or "write tests later".
- In autonomous mode, record assumptions instead of stopping unless the missing detail is unsafe.

## Evidence

The run must preserve:

- Plan path.
- Summary of assumptions.
- Validation commands selected for the plan.
- Memory record for plan intent and assumptions.
