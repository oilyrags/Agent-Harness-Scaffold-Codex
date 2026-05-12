from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from .agent_runner import AgentRunner
from .config import WorkflowDefinition, load_workflow
from .issue import Issue
from .mcp_proxy import MCPProxy
from .workspace import WorkspaceManager

LOGGER = logging.getLogger(__name__)


class Supervisor:
    def __init__(self, workflow_path: Path, *, dry_run: bool, mode: str):
        self.workflow_path = workflow_path
        self.dry_run = dry_run
        self.mode = mode
        self._stop = asyncio.Event()

    async def run_forever(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._stop.set)

        LOGGER.info("starting Symphony supervisor mode=%s dry_run=%s", self.mode, self.dry_run)
        while not self._stop.is_set():
            workflow = load_workflow(self.workflow_path)
            await self.tick(workflow)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=workflow.polling_interval_ms / 1000)
            except asyncio.TimeoutError:
                continue
        LOGGER.info("stopped Symphony supervisor")

    async def run_once(self) -> None:
        workflow = load_workflow(self.workflow_path)
        LOGGER.info("running one Symphony supervisor tick mode=%s dry_run=%s", self.mode, self.dry_run)
        await self.tick(workflow)

    async def tick(self, workflow: WorkflowDefinition) -> None:
        proxy = MCPProxy(workflow.mcp_config_path, dry_run=self.dry_run)
        proxy.validate_required_servers()

        if self.dry_run:
            LOGGER.info("dry_run active_states=%s terminal_states=%s", workflow.active_states, workflow.terminal_states)
            return

        response = await proxy.call_tool(
            "jira",
            "read_issues",
            {"active_states": workflow.active_states, "terminal_states": workflow.terminal_states},
        )
        issues = _normalize_issues(response)
        workspace_manager = WorkspaceManager(workflow.workspace_root)
        runner = AgentRunner(workflow, dry_run=self.dry_run)
        for issue in issues:
            workspace = workspace_manager.create_for_issue(issue.identifier)
            await runner.run_issue(issue, workspace.path)


def _normalize_issues(response: object) -> list[Issue]:
    if isinstance(response, dict) and isinstance(response.get("issues"), list):
        raw_issues = response["issues"]
    elif isinstance(response, list):
        raw_issues = response
    else:
        raw_issues = []

    issues: list[Issue] = []
    for item in raw_issues:
        if isinstance(item, dict):
            issues.append(Issue.from_mapping(item))
    return issues
