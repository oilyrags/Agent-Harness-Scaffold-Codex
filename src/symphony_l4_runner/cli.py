from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from .config import load_workflow
from .logging_setup import configure_logging
from .supervisor import Supervisor


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Codex + Symphony L4 supervisor.")
    parser.add_argument("--workflow", default="WORKFLOW.md", help="Path to WORKFLOW.md")
    parser.add_argument("--once", action="store_true", help="Run a single poll/dispatch tick and exit")
    parser.add_argument("--dry-run", action="store_true", help="Do not call live MCP servers or Codex")
    parser.add_argument("--check", action="store_true", help="Validate workflow and MCP config, then exit")
    args = parser.parse_args()

    configure_logging()
    workflow_path = Path(args.workflow)
    dry_run = args.dry_run or os.environ.get("SYMPHONY_DRY_RUN", "false").lower() in {"1", "true", "yes"}
    mode = os.environ.get("SYMPHONY_MODE", "interactive").lower()

    if args.check:
        workflow = load_workflow(workflow_path)
        from .mcp_proxy import MCPProxy

        MCPProxy(workflow.mcp_config_path, dry_run=True).validate_required_servers()
        print("workflow and MCP config valid")
        return

    supervisor = Supervisor(workflow_path, dry_run=dry_run, mode=mode)
    if args.once:
        asyncio.run(supervisor.run_once())
    else:
        asyncio.run(supervisor.run_forever())
