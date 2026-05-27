from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from symphony_l4_runner.agent_runner import AgentRunner
from symphony_l4_runner.agent_runner import prepare_codex_runtime_home
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

    def test_prepare_codex_runtime_home_links_read_only_credentials_and_uses_writable_state_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source = temp_path / "readonly-codex"
            source.mkdir()
            for name in ("auth.json", "config.toml", "AGENTS.md"):
                (source / name).write_text("placeholder", encoding="utf-8")
            for name in ("agents", "rules", "skills", "plugins"):
                (source / name).mkdir()

            runtime = prepare_codex_runtime_home(source, temp_path / "runtime-root")

            self.assertTrue((runtime / "auth.json").is_symlink())
            self.assertEqual((runtime / "auth.json").resolve(), (source / "auth.json").resolve())
            self.assertTrue((runtime / "config.toml").is_symlink())
            self.assertTrue((runtime / "agents").is_symlink())
            for name in ("bin", "tmp", "sessions", "runs", "log", "cache"):
                path = runtime / name
                self.assertTrue(path.is_dir(), name)
                self.assertFalse(path.is_symlink(), name)
            self.assertTrue(os.access(runtime / "sessions", os.W_OK))


if __name__ == "__main__":
    unittest.main()
