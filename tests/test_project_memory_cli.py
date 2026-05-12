from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "project_memory.py"


class ProjectMemoryCliTests(unittest.TestCase):
    def test_capture_search_and_boot_context_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "memory.sqlite3"

            capture = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--db",
                    str(db_path),
                    "capture",
                    "--kind",
                    "decision",
                    "--title",
                    "CLI memory capture",
                    "--body",
                    "The CLI exposes durable project memory to Symphony.",
                    "--issue-id",
                    "CLI-1",
                    "--tag",
                    "cli",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, capture.returncode, capture.stderr)
            captured = json.loads(capture.stdout)
            self.assertGreater(captured["id"], 0)

            search = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--db",
                    str(db_path),
                    "search",
                    "durable project memory",
                    "--issue-id",
                    "CLI-1",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, search.returncode, search.stderr)
            results = json.loads(search.stdout)
            self.assertEqual("CLI memory capture", results[0]["title"])

            boot = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--db",
                    str(db_path),
                    "boot-context",
                    "--issue-id",
                    "CLI-1",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, boot.returncode, boot.stderr)
            self.assertIn("CLI memory capture", boot.stdout)


if __name__ == "__main__":
    unittest.main()
