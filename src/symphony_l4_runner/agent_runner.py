from __future__ import annotations

import asyncio
import logging
import re
import shlex
from pathlib import Path
from typing import Any

from .config import WorkflowDefinition
from .issue import Issue
from .security import redacted_environment, redact

LOGGER = logging.getLogger(__name__)


class PromptRenderError(ValueError):
    """Raised when WORKFLOW.md contains an unknown template variable."""


class AgentRunner:
    def __init__(self, workflow: WorkflowDefinition, *, dry_run: bool):
        self.workflow = workflow
        self.dry_run = dry_run

    async def run_issue(self, issue: Issue, workspace_path: Path, attempt: int | None = None) -> int:
        prompt = render_prompt(self.workflow.prompt_template, issue, attempt)
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
        return int(process.returncode or 0)


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
