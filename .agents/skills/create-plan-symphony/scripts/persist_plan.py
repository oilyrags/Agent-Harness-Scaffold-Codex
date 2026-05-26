#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

REQUIRED_SECTIONS = (
    "# Plan",
    "## Vertical slice contract",
    "### Slice outcome",
    "### Behavior contract",
    "### Interface contract",
    "### Data contract",
    "### Non-goals",
    "### Acceptance criteria",
    "### Verification contract",
    "### Independent verifier instructions",
    "## Scope",
    "## Action items",
    "## Validation",
    "## Assumptions",
    "## Open questions",
)

VERTICAL_SLICE_SUBSECTIONS = (
    "Slice outcome",
    "Behavior contract",
    "Interface contract",
    "Data contract",
    "Non-goals",
    "Acceptance criteria",
    "Verification contract",
    "Independent verifier instructions",
)

CHECKLIST_SUBSECTIONS = {"Acceptance criteria", "Verification contract"}

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|client[_-]?secret)\s*[:=]\s*['\"]?[^'\"\s]+"),
    re.compile(r"(?i)authorization:\s*(bearer|basic)\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
)


class PlanError(ValueError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist a Symphony plan to .plans/<issue-id>.md")
    parser.add_argument("--issue-id", required=True, help="Jira issue identifier, for example HACK-123")
    parser.add_argument("--plans-dir", default=os.environ.get("PLANS_DIR", ".plans"), help="Plan directory")
    parser.add_argument("--plan-file", help="Read plan markdown from this file instead of stdin")
    args = parser.parse_args()

    try:
        issue_id = sanitize_issue_id(args.issue_id)
        content = read_content(args.plan_file)
        validate_plan(content)
        reject_secrets(content)
        plans_dir = Path(args.plans_dir).expanduser().resolve()
        path = plans_dir / f"{issue_id}.md"
        ensure_under_directory(path, plans_dir)
        atomic_write(path, content)
    except PlanError as exc:
        print(f"persist_plan error: {exc}", file=sys.stderr)
        return 2

    print(path)
    return 0


def sanitize_issue_id(issue_id: str) -> str:
    candidate = issue_id.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", candidate):
        raise PlanError("issue id must look like a Jira key, for example HACK-123")
    return candidate


def read_content(plan_file: str | None) -> str:
    if plan_file:
        return Path(plan_file).read_text(encoding="utf-8")
    return sys.stdin.read()


def validate_plan(content: str) -> None:
    missing = [section for section in REQUIRED_SECTIONS if section not in content]
    if missing:
        raise PlanError(f"missing required sections: {', '.join(missing)}")
    validate_vertical_slice_contract(content)
    action_count = len(re.findall(r"(?m)^\[ \] .+", content))
    if action_count < 6 or action_count > 10:
        raise PlanError("plan must contain 6-10 unchecked action items")


def validate_vertical_slice_contract(content: str) -> None:
    for subsection in VERTICAL_SLICE_SUBSECTIONS:
        body = extract_subsection_body(content, subsection)
        if not body.strip():
            raise PlanError(f"Vertical slice contract subsection is empty: {subsection}")
        if subsection in CHECKLIST_SUBSECTIONS and not re.search(r"(?m)^- \[ \] .+", body):
            raise PlanError(f"Vertical slice contract subsection requires checklist items: {subsection}")


def extract_subsection_body(content: str, subsection: str) -> str:
    pattern = rf"(?ms)^### {re.escape(subsection)}\s*\n(?P<body>.*?)(?=^### |^## |\Z)"
    match = re.search(pattern, content)
    if not match:
        raise PlanError(f"missing vertical slice contract subsection: {subsection}")
    return match.group("body")


def reject_secrets(content: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(content):
            raise PlanError("refusing to persist likely secret material")


def ensure_under_directory(path: Path, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    resolved_dir = directory.resolve()
    resolved_path = path.resolve()
    if resolved_dir != resolved_path.parent:
        raise PlanError("plan path must be directly under the plans directory")


def atomic_write(path: Path, content: str) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            if not content.endswith("\n"):
                handle.write("\n")
        os.replace(temp_name, path)
    finally:
        temp_path = Path(temp_name)
        if temp_path.exists():
            temp_path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
