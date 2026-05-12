from __future__ import annotations

import asyncio
import logging
import re
import sqlite3
import shlex
from pathlib import Path
from typing import Any

from .config import WorkflowDefinition
from .issue import Issue
from .memory import ProjectMemory
from .security import redacted_environment, redact

LOGGER = logging.getLogger(__name__)


class PromptRenderError(ValueError):
    """Raised when WORKFLOW.md contains an unknown template variable."""


class AgentRunner:
    def __init__(self, workflow: WorkflowDefinition, *, dry_run: bool):
        self.workflow = workflow
        self.dry_run = dry_run

    async def run_issue(self, issue: Issue, workspace_path: Path, attempt: int | None = None) -> int:
        prompt = self.build_prompt(issue, attempt=attempt)
        if self.dry_run:
            LOGGER.info(
                "dry_run agent dispatch issue_identifier=%s workspace=%s prompt_chars=%s",
                issue.identifier,
                workspace_path,
                len(prompt),
            )
            return 0

        command = self.workflow.codex_command
        argv = shlex.split(command)
        LOGGER.info("starting Codex issue_identifier=%s command=%s", issue.identifier, redact(command))
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(workspace_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=redacted_environment(),
        )
        stdout, stderr = await process.communicate(prompt.encode("utf-8"))
        if stdout:
            LOGGER.info("codex stdout issue_identifier=%s output=%s", issue.identifier, redact(stdout.decode("utf-8", "replace")))
        if stderr:
            LOGGER.warning("codex stderr issue_identifier=%s output=%s", issue.identifier, redact(stderr.decode("utf-8", "replace")))
        return_code = int(process.returncode or 0)
        self._record_run_event(issue, return_code)
        return return_code

    def build_prompt(self, issue: Issue, attempt: int | None = None) -> str:
        prompt = render_prompt(self.workflow.prompt_template, issue, attempt)
        memory_context = self._memory_context(issue)
        if not memory_context:
            return prompt
        return f"{prompt}\n\n## Project Memory\n\n{memory_context.strip()}\n"

    def _memory_context(self, issue: Issue) -> str:
        db_path = self.workflow.memory_db_path
        if db_path is None:
            return ""
        try:
            return ProjectMemory(db_path).boot_context(
                issue_id=issue.identifier,
                limit=self.workflow.memory_boot_context_limit,
            )
        except (OSError, ValueError, sqlite3.Error) as exc:
            LOGGER.warning("project memory unavailable issue_identifier=%s error=%s", issue.identifier, redact(str(exc)))
            return ""

    def _record_run_event(self, issue: Issue, return_code: int) -> None:
        db_path = self.workflow.memory_db_path
        if db_path is None:
            return
        event_type = "codex-run-completed" if return_code == 0 else "codex-run-failed"
        summary = f"Codex autonomous execution finished with exit code {return_code}."
        try:
            ProjectMemory(db_path).record_run(
                issue_id=issue.identifier,
                event_type=event_type,
                summary=summary,
                payload={"return_code": return_code},
            )
        except (OSError, ValueError, sqlite3.Error) as exc:
            LOGGER.warning("project memory run checkpoint failed issue_identifier=%s error=%s", issue.identifier, redact(str(exc)))


def render_prompt(template: str, issue: Issue, attempt: int | None) -> str:
    values: dict[str, Any] = {
        "issue.id": issue.id,
        "issue.identifier": issue.identifier,
        "issue.title": issue.title,
        "issue.description": issue.description or "",
        "issue.state": issue.state,
        "issue.url": issue.url or "",
        "attempt": "" if attempt is None else str(attempt),
    }

    def replace(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        if name not in values:
            raise PromptRenderError(f"template_render_error: unknown variable {name}")
        return str(values[name])

    return re.sub(r"\{\{\s*([^}]+?)\s*\}\}", replace, template)
