from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_REPO_PATH = ROOT / "scripts/validate_repo.py"


def load_validate_repo_module():
    spec = importlib.util.spec_from_file_location("validate_repo", VALIDATE_REPO_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load validate_repo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ValidateRepoTests(unittest.TestCase):
    def test_tracker_term_check_ignores_local_virtualenvs(self) -> None:
        validate_repo = load_validate_repo_module()
        fixture = ROOT / ".venv/validate-repo-ignore-test.txt"
        fixture.parent.mkdir(exist_ok=True)
        fixture.write_text("third-party dependency may contain " + "Lin" + "ear", encoding="utf-8")
        try:
            validate_repo.check_no_disallowed_tracker_terms()
        finally:
            fixture.unlink(missing_ok=True)

    def test_compose_passes_mcp_command_environment_variables(self) -> None:
        compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
        environment = compose["services"]["symphony"]["environment"]

        for variable in (
            "JIRA_PROJECT_KEY",
            "JIRA_CLOUD_ID",
            "MCP_GITHUB_COMMAND",
            "MCP_JIRA_COMMAND",
            "MCP_NOTION_COMMAND",
            "MCP_MIRO_COMMAND",
            "MCP_FIGMA_COMMAND",
            "MCP_LOVABLE_COMMAND",
            "MCP_POSTGRES_COMMAND",
            "MCP_CHROMA_COMMAND",
        ):
            self.assertIn(variable, environment)

    def test_compose_exposes_jira_oauth_callback_and_auth_cache(self) -> None:
        compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
        symphony = compose["services"]["symphony"]

        self.assertIn("3334:3334", symphony["ports"])
        self.assertIn("${HOME}/.mcp-auth:/root/.mcp-auth", symphony["volumes"])

        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("MCP_JIRA_COMMAND=npx -y mcp-remote https://mcp.atlassian.com/v1/sse 3334", env_example)
        self.assertIn("--host 0.0.0.0", env_example)
        self.assertIn("--auth-timeout 120", env_example)
        self.assertIn("--transport sse-only", env_example)

    def test_workflow_codex_command_uses_supported_exec_flags(self) -> None:
        workflow = (ROOT / "WORKFLOW.md").read_text(encoding="utf-8")
        frontmatter = workflow.split("---\n", 2)[1]
        command = yaml.safe_load(frontmatter)["codex"]["command"]

        self.assertNotIn("--ask-for-approval", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("--ephemeral", command)
        self.assertIn("--sandbox workspace-write", command)


if __name__ == "__main__":
    unittest.main()
