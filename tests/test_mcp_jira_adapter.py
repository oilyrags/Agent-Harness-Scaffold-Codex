from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from symphony_l4_runner.mcp_proxy import (
    build_jira_issue_keys_jql,
    build_jira_active_issues_jql,
    extract_json_payload,
    filter_issues_ready_for_dispatch,
    issue_dependencies,
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

    def test_build_jira_issue_keys_jql_queries_specific_dependency_keys(self) -> None:
        jql = build_jira_issue_keys_jql(["CAT-7", "CAT-6"])

        self.assertEqual("key in (CAT-6, CAT-7)", jql)

    def test_issue_dependencies_extracts_explicit_dependency_line(self) -> None:
        dependencies = issue_dependencies("Parent: CAT-5\nDependencies: CAT-6, CAT-7\n")

        self.assertEqual(["CAT-6", "CAT-7"], dependencies)

    def test_issue_dependencies_extracts_depends_on_contract_wording(self) -> None:
        dependencies = issue_dependencies("## Dependencies or ordering notes\nDepends on CAT-6 before implementation starts.")

        self.assertEqual(["CAT-6"], dependencies)

    def test_filter_issues_ready_for_dispatch_skips_non_terminal_dependencies(self) -> None:
        issues = [
            {"identifier": "CAT-6", "title": "Ready", "description": "None"},
            {"identifier": "CAT-7", "title": "Blocked", "description": "Depends on CAT-6."},
            {"identifier": "CAT-8", "title": "Ready later", "description": "Dependencies: CAT-2"},
        ]

        ready = filter_issues_ready_for_dispatch(
            issues,
            dependency_statuses={"CAT-6": "Selected for Development", "CAT-2": "Done"},
            terminal_states=["Done", "Closed"],
        )

        self.assertEqual(["CAT-6", "CAT-8"], [issue["identifier"] for issue in ready])

    def test_filter_issues_ready_for_dispatch_fails_closed_for_unresolved_dependencies(self) -> None:
        issues = [{"identifier": "CAT-8", "title": "Blocked", "description": "Dependencies: CAT-7"}]

        ready = filter_issues_ready_for_dispatch(issues, dependency_statuses={}, terminal_states=["Done"])

        self.assertEqual([], ready)

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
