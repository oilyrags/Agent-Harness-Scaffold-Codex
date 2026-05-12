from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .memory import MemorySecretError, ProjectMemory


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    memory = ProjectMemory(args.db or default_db_path())

    try:
        if args.command == "init":
            memory.initialize()
            _print_json({"status": "initialized", "db": str(memory.db_path)})
            return 0
        if args.command == "capture":
            record_id = memory.capture(
                kind=args.kind,
                title=args.title,
                body=args.body,
                issue_id=args.issue_id,
                source=args.source,
                tags=args.tag or [],
                confidence=args.confidence,
            )
            _print_json({"id": record_id, "db": str(memory.db_path)})
            return 0
        if args.command == "search":
            _print_json(
                memory.search(
                    " ".join(args.query),
                    issue_id=args.issue_id,
                    kind=args.kind,
                    limit=args.limit,
                )
            )
            return 0
        if args.command == "boot-context":
            sys.stdout.write(memory.boot_context(issue_id=args.issue_id, limit=args.limit))
            return 0
        if args.command == "record-run":
            payload = _parse_json_object(args.payload_json)
            event_id = memory.record_run(
                issue_id=args.issue_id,
                event_type=args.event_type,
                summary=args.summary,
                payload=payload,
            )
            _print_json({"event_id": event_id, "db": str(memory.db_path)})
            return 0
        if args.command == "record-decision":
            record_id = memory.record_decision(
                issue_id=args.issue_id,
                title=args.title,
                body=args.body,
                tags=args.tag or [],
                source=args.source,
            )
            _print_json({"id": record_id, "db": str(memory.db_path)})
            return 0
    except MemorySecretError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    parser.error("missing command")
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read and write local Symphony project memory.")
    parser.add_argument("--db", type=Path, default=None, help="SQLite database path.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("init", help="Initialize the project-memory database.")

    capture = subcommands.add_parser("capture", help="Capture a memory record.")
    capture.add_argument("--kind", required=True)
    capture.add_argument("--title", required=True)
    capture.add_argument("--body", required=True)
    capture.add_argument("--issue-id")
    capture.add_argument("--source")
    capture.add_argument("--tag", action="append")
    capture.add_argument("--confidence", type=float, default=1.0)

    search = subcommands.add_parser("search", help="Search project memory.")
    search.add_argument("query", nargs="+")
    search.add_argument("--issue-id")
    search.add_argument("--kind")
    search.add_argument("--limit", type=int, default=10)

    boot = subcommands.add_parser("boot-context", help="Print a compact boot context for an issue.")
    boot.add_argument("--issue-id")
    boot.add_argument("--limit", type=int, default=8)

    run = subcommands.add_parser("record-run", help="Record an autonomous run event.")
    run.add_argument("--issue-id", required=True)
    run.add_argument("--event-type", required=True)
    run.add_argument("--summary", required=True)
    run.add_argument("--payload-json", default="{}")

    decision = subcommands.add_parser("record-decision", help="Record an architectural or workflow decision.")
    decision.add_argument("--title", required=True)
    decision.add_argument("--body", required=True)
    decision.add_argument("--issue-id")
    decision.add_argument("--source", default="decision")
    decision.add_argument("--tag", action="append")

    return parser


def default_db_path() -> Path:
    env_path = os.environ.get("PROJECT_MEMORY_DB")
    if env_path:
        return Path(env_path)
    return Path.cwd() / ".memory" / "project-memory.sqlite3"


def _parse_json_object(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("--payload-json must decode to an object")
    return parsed


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))
