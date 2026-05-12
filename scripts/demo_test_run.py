#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from symphony_l4_runner.agent_runner import AgentRunner, render_prompt
from symphony_l4_runner.config import load_workflow
from symphony_l4_runner.issue import Issue
from symphony_l4_runner.workspace import WorkspaceManager


def main() -> int:
    workflow = load_workflow(ROOT / "WORKFLOW.md")
    issue = Issue(
        id="DEMO-1",
        identifier="DEMO-1",
        title="Verify Docker headless Codex execution path",
        description="Demo issue used to prove the desktop-app-outside, CLI-inside-Docker design.",
        state="To Do",
        labels=["demo"],
    )

    print("demo: host surface =", workflow.codex_host_surface)
    print("demo: container surface =", workflow.codex_container_surface)
    print("demo: codex command =", workflow.codex_command)
    print("demo: app server command =", workflow.codex_app_server_command)

    codex_path = shutil.which("codex")
    if not codex_path:
        raise RuntimeError("codex CLI is not installed in this container")
    print("demo: codex binary =", codex_path)

    version = subprocess.run(
        ["codex", "--version"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if version.returncode != 0:
        raise RuntimeError(version.stderr.strip() or "codex --version failed")
    print("demo: codex version =", version.stdout.strip())

    prompt = render_prompt(workflow.prompt_template, issue, attempt=None)
    if "create-plan-symphony" not in prompt or "DEMO-1" not in prompt:
        raise RuntimeError("rendered prompt did not include expected Symphony/Jira context")
    print("demo: rendered prompt chars =", len(prompt))

    workspace = WorkspaceManager(ROOT / ".demo-workspaces").create_for_issue(issue.identifier)
    runner = AgentRunner(workflow, dry_run=True)
    result = asyncio.run(runner.run_issue(issue, workspace.path))
    if result != 0:
        raise RuntimeError(f"dry-run dispatch failed with exit code {result}")
    print("demo: workspace =", workspace.path)
    print("demo: dry-run dispatch = ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
