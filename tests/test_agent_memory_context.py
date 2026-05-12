from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from symphony_l4_runner.agent_runner import AgentRunner
from symphony_l4_runner.config import WorkflowDefinition
from symphony_l4_runner.issue import Issue
from symphony_l4_runner.memory import ProjectMemory


class AgentMemoryContextTests(unittest.TestCase):
    def test_build_prompt_includes_issue_memory_boot_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "memory.sqlite3"
            ProjectMemory(db_path).capture(
                kind="decision",
                title="Remember validation policy",
                body="Run unit tests and repository validation before merging.",
                issue_id="CTX-1",
                tags=["validation"],
            )
            workflow = WorkflowDefinition(
                path=ROOT / "WORKFLOW.md",
                config={
                    "tracker": {"kind": "jira"},
                    "codex": {
                        "host_surface": "desktop_app",
                        "container_surface": "cli_or_app_server",
                        "command": "codex exec",
                        "app_server_command": "codex app-server",
                    },
                    "memory": {"db_path": str(db_path), "boot_context_limit": 5},
                },
                prompt_template="Work on {{ issue.identifier }}.",
            )
            issue = Issue(id="CTX-1", identifier="CTX-1", title="Memory context")

            with patch.dict("os.environ", {"PROJECT_MEMORY_DB": str(db_path)}):
                prompt = AgentRunner(workflow, dry_run=True).build_prompt(issue)

            self.assertIn("## Project Memory", prompt)
            self.assertIn("Remember validation policy", prompt)


if __name__ == "__main__":
    unittest.main()
