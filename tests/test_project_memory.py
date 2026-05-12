from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from symphony_l4_runner.memory import MemorySecretError, ProjectMemory


class ProjectMemoryTests(unittest.TestCase):
    def test_capture_and_search_records_issue_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = ProjectMemory(Path(temp_dir) / "memory.sqlite3")
            record_id = memory.capture(
                kind="decision",
                title="Use SQLite project memory",
                body="Persist compact Symphony run context with SQLite FTS5 boot context search.",
                issue_id="MEM-1",
                source="unit-test",
                tags=["sqlite", "symphony"],
            )

            results = memory.search("SQLite boot context", issue_id="MEM-1")

            self.assertGreater(record_id, 0)
            self.assertEqual(1, len(results))
            self.assertEqual("decision", results[0]["kind"])
            self.assertEqual("MEM-1", results[0]["issue_id"])
            self.assertIn("sqlite", results[0]["tags"])

    def test_boot_context_prefers_issue_and_global_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = ProjectMemory(Path(temp_dir) / "memory.sqlite3")
            memory.capture(
                kind="decision",
                title="Global validation policy",
                body="Always run repository validation before merging.",
                source="architecture",
                tags=["validation"],
            )
            memory.capture(
                kind="assumption",
                title="MEM-2 works offline",
                body="The test run should not contact live Jira or GitHub MCP servers.",
                issue_id="MEM-2",
                source="plan",
                tags=["offline"],
            )
            memory.capture(
                kind="assumption",
                title="Unrelated issue detail",
                body="This belongs to a different Jira issue.",
                issue_id="MEM-9",
                source="plan",
            )

            context = memory.boot_context(issue_id="MEM-2", limit=10)

            self.assertIn("# Project Memory Boot Context", context)
            self.assertIn("Global validation policy", context)
            self.assertIn("MEM-2 works offline", context)
            self.assertNotIn("Unrelated issue detail", context)

    def test_secret_material_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = ProjectMemory(Path(temp_dir) / "memory.sqlite3")

            with self.assertRaises(MemorySecretError):
                memory.capture(
                    kind="decision",
                    title="Unsafe credential note",
                    body="api_key=abc1234567890 should never be persisted",
                )

    def test_record_run_is_searchable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = ProjectMemory(Path(temp_dir) / "memory.sqlite3")
            event_id = memory.record_run(
                issue_id="MEM-3",
                event_type="validation",
                summary="Repository validation and Docker demo completed successfully.",
                payload={"commands": ["python scripts/validate_repo.py"]},
            )

            results = memory.search("Docker demo", issue_id="MEM-3")

            self.assertGreater(event_id, 0)
            self.assertEqual(1, len(results))
            self.assertEqual("run-summary", results[0]["kind"])


if __name__ == "__main__":
    unittest.main()
