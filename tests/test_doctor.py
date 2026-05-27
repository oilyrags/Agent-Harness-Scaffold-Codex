from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DoctorCliTests(unittest.TestCase):
    def test_valid_live_mode_env_reports_ready_without_printing_connector_command(self) -> None:
        raw_command = "npx -y mcp-remote https://mcp.example.invalid/v1/sse 3334 --auth-timeout 120"
        result = run_doctor(
            {
                "JIRA_PROJECT_KEY": "CAT",
                "JIRA_CLOUD_ID": "a07744f6-77ab-456e-b5ee-2fe4a3418b3b",
                "SYMPHONY_DRY_RUN": "false",
                "SYMPHONY_MODE": "autonomous",
                "MCP_JIRA_COMMAND": raw_command,
            }
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("READY: live-mode preflight passed", result.stdout)
        self.assertIn("JIRA_PROJECT_KEY: CAT", result.stdout)
        self.assertIn("MCP_JIRA_COMMAND: configured (value redacted)", result.stdout)
        self.assertNotIn(raw_command, result.stdout)

    def test_missing_project_key_reports_blocking_error(self) -> None:
        result = run_doctor(
            {
                "SYMPHONY_DRY_RUN": "false",
                "SYMPHONY_MODE": "autonomous",
                "MCP_JIRA_COMMAND": "npx -y mcp-remote https://mcp.example.invalid/v1/sse 3334",
            }
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("BLOCKER JIRA_PROJECT_KEY: missing", result.stdout)
        self.assertIn("NOT READY:", result.stdout)

    def test_missing_cloud_id_is_allowed_as_auto_discovery(self) -> None:
        result = run_doctor(
            {
                "JIRA_PROJECT_KEY": "CAT",
                "SYMPHONY_DRY_RUN": "false",
                "SYMPHONY_MODE": "autonomous",
                "MCP_JIRA_COMMAND": "npx -y mcp-remote https://mcp.example.invalid/v1/sse 3334",
            }
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("INFO JIRA_CLOUD_ID: missing; Jira cloud auto-discovery enabled", result.stdout)

    def test_dry_run_true_is_not_live_ready(self) -> None:
        result = run_doctor(
            {
                "JIRA_PROJECT_KEY": "CAT",
                "SYMPHONY_DRY_RUN": "true",
                "SYMPHONY_MODE": "autonomous",
                "MCP_JIRA_COMMAND": "npx -y mcp-remote https://mcp.example.invalid/v1/sse 3334",
            }
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("BLOCKER SYMPHONY_DRY_RUN: true disables live mode", result.stdout)


def run_doctor(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    command_env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(ROOT / "src"),
        **env,
    }
    return subprocess.run(
        [sys.executable, "-m", "symphony_l4_runner", "doctor"],
        cwd=ROOT,
        env=command_env,
        text=True,
        capture_output=True,
        check=False,
    )


if __name__ == "__main__":
    unittest.main()
