from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from symphony_l4_runner.mcp_proxy import (
    build_jira_active_issues_jql,
    extract_json_payload,
    normalize_atlassian_jira_issues,
)


class JiraAdapterTests(unittest.TestCase):
    def test_build_jira_active_issues_jql_scopes_to_project_and_states(self) -> None:
        jql = build_jira_active_issues_jql("HACK", ["To Do", "In Progress"])

        self.assertEqual(
            'project = "HACK" AND status in ("To Do", "In Progress") '
            'AND issuetype not in ("Epic") ORDER BY updated DESC',
            jql,
        )

    def test_extract_json_payload_ignores_provider_notice(self) -> None:
        payload = extract_json_payload(
            "[IMPORTANT: provider notice]\n"
            + json.dumps({"issues": [{"key": "HACK-1", "fields": {"summary": "Do work"}}]})
        )

        self.assertEqual("HACK-1", payload["issues"][0]["key"])

    def test_normalize_atlassian_jira_issues_maps_required_fields(self) -> None:
        normalized = normalize_atlassian_jira_issues(
            {
                "issues": [
                    {
                        "id": "10001",
                        "key": "HACK-1",
                        "self": "https://example.atlassian.net/rest/api/3/issue/10001",
                        "fields": {
                            "summary": "Do work",
                            "description": "Contracted slice",
                            "status": {"name": "To Do"},
                        },
                    }
                ]
            }
        )

        self.assertEqual(
            [
                {
                    "id": "10001",
                    "identifier": "HACK-1",
                    "title": "Do work",
                    "description": "Contracted slice",
                    "status": "To Do",
                    "url": "https://example.atlassian.net/rest/api/3/issue/10001",
                }
            ],
            normalized,
        )


if __name__ == "__main__":
    unittest.main()
