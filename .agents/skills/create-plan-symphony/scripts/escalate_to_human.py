#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|client[_-]?secret)\s*[:=]\s*['\"]?[^'\"\s]+"),
    re.compile(r"(?i)authorization:\s*(bearer|basic)\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Escalate a blocked autonomous plan to a human through Jira.")
    parser.add_argument("--issue-id", required=True, help="Jira issue identifier, for example HACK-123")
    parser.add_argument("--reason", required=True, help="Short blocker reason")
    parser.add_argument("--plans-dir", default=os.environ.get("PLANS_DIR", ".plans"), help="Plan directory")
    args = parser.parse_args()

    issue_id = sanitize_issue_id(args.issue_id)
    reason = redact(args.reason.strip())
    if not reason:
        print("escalate_to_human error: reason is required", file=sys.stderr)
        return 2

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "issue_id": issue_id,
        "reason": reason,
        "target_status": "needs-clarification",
    }
    plans_dir = Path(args.plans_dir).expanduser().resolve()
    plans_dir.mkdir(parents=True, exist_ok=True)
    with (plans_dir / "escalations.log").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")

    # TODO: Implement Jira transition API call
    # Example:
    # POST /rest/api/3/issue/{issueIdOrKey}/transitions
    print(f"escalated {issue_id} to needs-clarification")
    return 0


def sanitize_issue_id(issue_id: str) -> str:
    candidate = issue_id.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", candidate):
        raise SystemExit("issue id must look like a Jira key, for example HACK-123")
    return candidate


def redact(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


if __name__ == "__main__":
    raise SystemExit(main())
