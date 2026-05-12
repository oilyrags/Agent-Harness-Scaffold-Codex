# Verification Before Completion Gate

Use this gate before claiming completion, opening a PR, merging, or handing off.

## Requirements

- Identify the commands that prove the claim.
- Run the commands fresh.
- Read stdout, stderr, and exit code.
- Report actual status from evidence.
- Do not claim success from stale runs, partial checks, or assumptions.

## Required Commands For This Repository

At minimum, run:

```bash
python scripts/validate_repo.py
python -m unittest discover -s tests
PYTHONPATH=src python -m symphony_l4_runner --workflow WORKFLOW.md --once --dry-run
```

For Docker runtime changes, also run the host-side E2E harness:

```bash
docker compose build symphony
python scripts/e2e_scenario.py
```

## Evidence

The run must preserve:

- Commands run.
- Exit codes.
- Summary of failures or pass counts.
- Path to evidence artifacts when available.
