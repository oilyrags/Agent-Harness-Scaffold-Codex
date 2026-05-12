from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class WorkflowConfigError(ValueError):
    """Raised when WORKFLOW.md cannot be used by the runner."""


@dataclass(frozen=True)
class WorkflowDefinition:
    path: Path
    config: dict[str, Any]
    prompt_template: str

    @property
    def polling_interval_ms(self) -> int:
        return int(self.config.get("polling", {}).get("interval_ms", 30_000))

    @property
    def workspace_root(self) -> Path:
        raw = self.config.get("workspace", {}).get("root", "/workspace")
        return Path(str(raw)).expanduser().resolve()

    @property
    def plans_dir(self) -> Path:
        raw = self.config.get("workspace", {}).get("plans_dir", str(self.workspace_root / ".plans"))
        return Path(str(raw)).expanduser().resolve()

    @property
    def mcp_config_path(self) -> Path:
        raw = self.config.get("mcp", {}).get("config_path", "config/mcp.servers.yaml")
        path = Path(str(raw)).expanduser()
        if not path.is_absolute():
            path = self.path.parent / path
        return path.resolve()

    @property
    def active_states(self) -> list[str]:
        return list(self.config.get("tracker", {}).get("active_states", ["To Do", "In Progress"]))

    @property
    def terminal_states(self) -> list[str]:
        return list(self.config.get("tracker", {}).get("terminal_states", ["Done", "Closed", "Canceled"]))

    @property
    def codex_command(self) -> str:
        return str(self.config.get("codex", {}).get("command", "codex exec")).strip()

    @property
    def codex_app_server_command(self) -> str:
        return str(self.config.get("codex", {}).get("app_server_command", "codex app-server")).strip()

    @property
    def codex_host_surface(self) -> str:
        return str(self.config.get("codex", {}).get("host_surface", "desktop_app")).strip()

    @property
    def codex_container_surface(self) -> str:
        return str(self.config.get("codex", {}).get("container_surface", "cli_or_app_server")).strip()

    @property
    def memory_db_path(self) -> Path | None:
        raw = os.environ.get("PROJECT_MEMORY_DB") or self.config.get("memory", {}).get("db_path")
        if not raw:
            return None
        path = Path(str(raw)).expanduser()
        if not path.is_absolute():
            path = self.path.parent / path
        return path.resolve()

    @property
    def memory_boot_context_limit(self) -> int:
        return int(self.config.get("memory", {}).get("boot_context_limit", 8))


def load_workflow(path: str | Path) -> WorkflowDefinition:
    workflow_path = Path(path).expanduser().resolve()
    if not workflow_path.exists():
        raise WorkflowConfigError(f"missing workflow file: {workflow_path}")

    text = workflow_path.read_text(encoding="utf-8")
    config: dict[str, Any] = {}
    prompt = text

    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) < 3:
            raise WorkflowConfigError("workflow_parse_error: unterminated YAML front matter")
        raw_yaml = parts[1]
        prompt = parts[2].strip()
        loaded = yaml.safe_load(raw_yaml) or {}
        if not isinstance(loaded, dict):
            raise WorkflowConfigError("workflow_front_matter_not_a_map")
        config = loaded
    else:
        prompt = text.strip()

    workflow = WorkflowDefinition(path=workflow_path, config=config, prompt_template=prompt)
    validate_workflow(workflow)
    return workflow


def validate_workflow(workflow: WorkflowDefinition) -> None:
    tracker = workflow.config.get("tracker", {})
    if tracker.get("kind") != "jira":
        raise WorkflowConfigError("tracker.kind must be jira")
    forbidden = {"api_key", "token", "password", "client_secret"}
    present_forbidden = forbidden.intersection(tracker.keys())
    if present_forbidden:
        names = ", ".join(sorted(present_forbidden))
        raise WorkflowConfigError(f"tracker config must not contain secrets: {names}")
    if workflow.codex_host_surface != "desktop_app":
        raise WorkflowConfigError("codex.host_surface must be desktop_app")
    if workflow.codex_container_surface != "cli_or_app_server":
        raise WorkflowConfigError("codex.container_surface must be cli_or_app_server")
    if not workflow.codex_command:
        raise WorkflowConfigError("codex.command must be non-empty")
    if not workflow.codex_app_server_command:
        raise WorkflowConfigError("codex.app_server_command must be non-empty")
    if "create-plan-symphony" not in workflow.prompt_template:
        raise WorkflowConfigError("WORKFLOW.md must reference create-plan-symphony")
