from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TextIO


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}
PROJECT_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


@dataclass(frozen=True)
class Check:
    level: str
    name: str
    message: str

    @property
    def blocking(self) -> bool:
        return self.level == "BLOCKER"

    def render(self) -> str:
        return f"{self.level} {self.name}: {self.message}"


def run_doctor(
    env: Mapping[str, str] | None = None,
    stdout: TextIO | None = None,
    output_format: str = "text",
) -> int:
    """Run the local no-secret live-mode preflight."""

    resolved_env = os.environ if env is None else env
    checks = evaluate_environment(resolved_env)
    output = stdout or sys.stdout

    if output_format == "json":
        json.dump(_build_json_payload(resolved_env, checks), output, sort_keys=True)
        print(file=output)
        return _exit_code(checks)
    if output_format != "text":
        raise ValueError(f"unsupported doctor output format: {output_format}")

    print("Symphony local config doctor", file=output)
    for check in checks:
        print(check.render(), file=output)

    blocker_count = _blocker_count(checks)
    if blocker_count:
        print(f"NOT READY: {blocker_count} blocking issue(s)", file=output)
        return 1

    print("READY: live-mode preflight passed", file=output)
    return 0


def evaluate_environment(env: Mapping[str, str]) -> list[Check]:
    checks = [
        _check_project_key(env.get("JIRA_PROJECT_KEY", "")),
        _check_cloud_id(env.get("JIRA_CLOUD_ID", "")),
        _check_dry_run(env.get("SYMPHONY_DRY_RUN", "")),
        _check_mode(env.get("SYMPHONY_MODE", "")),
        _check_jira_command(env.get("MCP_JIRA_COMMAND", "")),
    ]
    return checks


def _build_json_payload(env: Mapping[str, str], checks: list[Check]) -> dict[str, object]:
    return {
        "ready": _blocker_count(checks) == 0,
        "project_key_present": bool(env.get("JIRA_PROJECT_KEY", "").strip()),
        "cloud_id_present": bool(env.get("JIRA_CLOUD_ID", "").strip()),
        "dry_run": _json_bool(env.get("SYMPHONY_DRY_RUN", "")),
        "mode": env.get("SYMPHONY_MODE", "").strip().lower() or "interactive",
        "errors": [_check_json(check) for check in checks if check.blocking],
        "warnings": [_check_json(check) for check in checks if check.level == "INFO"],
    }


def _check_json(check: Check) -> dict[str, str]:
    return {"level": check.level, "name": check.name, "message": check.message}


def _json_bool(value: str) -> bool | None:
    stripped = value.strip().lower()
    if stripped in TRUE_VALUES:
        return True
    if stripped in FALSE_VALUES:
        return False
    return None


def _exit_code(checks: list[Check]) -> int:
    return 1 if _blocker_count(checks) else 0


def _blocker_count(checks: list[Check]) -> int:
    return sum(1 for check in checks if check.blocking)


def _check_project_key(value: str) -> Check:
    stripped = value.strip()
    if not stripped:
        return Check("BLOCKER", "JIRA_PROJECT_KEY", "missing")
    if not PROJECT_KEY_PATTERN.fullmatch(stripped):
        return Check("BLOCKER", "JIRA_PROJECT_KEY", "invalid project key format")
    return Check("OK", "JIRA_PROJECT_KEY", stripped)


def _check_cloud_id(value: str) -> Check:
    if not value.strip():
        return Check("INFO", "JIRA_CLOUD_ID", "missing; Jira cloud auto-discovery enabled")
    return Check("OK", "JIRA_CLOUD_ID", "configured")


def _check_dry_run(value: str) -> Check:
    stripped = value.strip().lower()
    if not stripped:
        return Check("INFO", "SYMPHONY_DRY_RUN", "missing; defaults to false for live mode")
    if stripped in TRUE_VALUES:
        return Check("BLOCKER", "SYMPHONY_DRY_RUN", "true disables live mode")
    if stripped in FALSE_VALUES:
        return Check("OK", "SYMPHONY_DRY_RUN", "false")
    return Check("BLOCKER", "SYMPHONY_DRY_RUN", "invalid boolean value")


def _check_mode(value: str) -> Check:
    stripped = value.strip().lower()
    if not stripped:
        return Check("INFO", "SYMPHONY_MODE", "missing; defaults to interactive")
    return Check("OK", "SYMPHONY_MODE", stripped)


def _check_jira_command(value: str) -> Check:
    if not value.strip():
        return Check("BLOCKER", "MCP_JIRA_COMMAND", "missing")
    return Check("OK", "MCP_JIRA_COMMAND", "configured (value redacted)")
