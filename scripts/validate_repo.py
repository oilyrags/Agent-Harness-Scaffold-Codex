#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "AGENTS.md",
    ".agents/skills/create-plan-symphony/SKILL.md",
    ".agents/skills/create-plan-symphony/agents/openai.yaml",
    ".agents/skills/create-plan-symphony/scripts/persist_plan.py",
    ".agents/skills/create-plan-symphony/scripts/escalate_to_human.py",
    ".agents/skills/superpowers-l4-quality-gates/SKILL.md",
    ".agents/skills/superpowers-l4-quality-gates/agents/openai.yaml",
    ".agents/skills/superpowers-l4-quality-gates/workflows/writing-plans.md",
    ".agents/skills/superpowers-l4-quality-gates/workflows/executing-plans.md",
    ".agents/skills/superpowers-l4-quality-gates/workflows/test-driven-development.md",
    ".agents/skills/superpowers-l4-quality-gates/workflows/systematic-debugging.md",
    ".agents/skills/superpowers-l4-quality-gates/workflows/verification-before-completion.md",
    ".agents/skills/superpowers-l4-quality-gates/workflows/requesting-code-review.md",
    ".agents/skills/superpowers-l4-quality-gates/workflows/finishing-development-branch.md",
    ".env.example",
    "WORKFLOW.md",
    ".plans/EXAMPLE.md",
    "README.md",
    "Dockerfile",
    "docker-compose.yml",
    "config/mcp.servers.yaml",
    "scripts/demo_test_run.py",
    "scripts/project_memory.py",
    "scripts/e2e_scenario.py",
    "docs/PROJECT_MEMORY.md",
    "docs/QUALITY_GATES.md",
    "src/symphony_l4_runner/memory.py",
    "src/symphony_l4_runner/mcp_memory_server.py",
    "tests/test_project_memory.py",
    "tests/test_project_memory_cli.py",
    "tests/test_agent_memory_context.py",
    "tests/test_quality_gates.py",
)

REQUIRED_PLAN_SECTIONS = (
    "# Plan",
    "## Vertical slice contract",
    "### Slice outcome",
    "### Behavior contract",
    "### Interface contract",
    "### Data contract",
    "### Non-goals",
    "### Acceptance criteria",
    "### Verification contract",
    "### Independent verifier instructions",
    "## Scope",
    "## Action items",
    "## Validation",
    "## Assumptions",
    "## Open questions",
)

README_INSTALL_PATHS = (
    ".agents/skills/create-plan-symphony/",
    ".agents/skills/superpowers-l4-quality-gates/",
    ".plans/",
    ".memory/",
    "~/.codex",
    "/root/.codex:ro",
    "/workspace",
    "scripts/project_memory.py",
    "scripts/e2e_scenario.py",
)


def main() -> int:
    checks = [
        check_required_files,
        check_skill_frontmatter_yaml,
        check_quality_gate_skill_frontmatter_yaml,
        check_openai_yaml,
        check_mcp_yaml,
        check_agents_contract_policy,
        check_workflow,
        check_create_plan_contract_policy,
        check_example_plan,
        check_readme,
        check_scripts_run,
        check_no_disallowed_tracker_terms,
    ]
    failures: list[str] = []
    for check in checks:
        try:
            check()
            print(f"PASS {check.__name__}")
        except Exception as exc:
            failures.append(f"{check.__name__}: {exc}")
            print(f"FAIL {check.__name__}: {exc}", file=sys.stderr)

    if failures:
        print("\nValidation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("All repository validation checks passed.")
    return 0


def check_required_files() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"missing files: {', '.join(missing)}")


def check_skill_frontmatter_yaml() -> None:
    text = (ROOT / ".agents/skills/create-plan-symphony/SKILL.md").read_text(encoding="utf-8")
    frontmatter = extract_frontmatter(text)
    data = yaml.safe_load(frontmatter)
    assert data["name"] == "create-plan-symphony"
    assert "Jira" in data["description"]


def check_quality_gate_skill_frontmatter_yaml() -> None:
    skill_dir = ROOT / ".agents/skills/superpowers-l4-quality-gates"
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = extract_frontmatter(text)
    data = yaml.safe_load(frontmatter)
    assert data["name"] == "superpowers-l4-quality-gates"
    assert "autonomous" in data["description"]
    expected = {
        "writing-plans.md",
        "executing-plans.md",
        "test-driven-development.md",
        "systematic-debugging.md",
        "verification-before-completion.md",
        "requesting-code-review.md",
        "finishing-development-branch.md",
    }
    actual = {path.name for path in (skill_dir / "workflows").glob("*.md")}
    missing = sorted(expected.difference(actual))
    if missing:
        raise AssertionError(f"missing quality-gate workflow files: {', '.join(missing)}")


def check_openai_yaml() -> None:
    data = yaml.safe_load((ROOT / ".agents/skills/create-plan-symphony/agents/openai.yaml").read_text(encoding="utf-8"))
    assert data["interface"]["display_name"] == "Create Plan Symphony"
    assert "$create-plan-symphony" in data["interface"]["default_prompt"]
    quality = yaml.safe_load((ROOT / ".agents/skills/superpowers-l4-quality-gates/agents/openai.yaml").read_text(encoding="utf-8"))
    assert quality["interface"]["display_name"] == "Superpowers L4 Quality Gates"
    assert "$superpowers-l4-quality-gates" in quality["interface"]["default_prompt"]


def check_mcp_yaml() -> None:
    data = yaml.safe_load((ROOT / "config/mcp.servers.yaml").read_text(encoding="utf-8"))
    assert data["auth"]["api_keys_allowed"] is False
    servers = data["servers"]
    for name in ("filesystem", "shell", "memory", "browser", "github", "jira", "notion", "miro", "figma", "lovable", "postgres", "chroma"):
        assert name in servers
        assert servers[name]["capabilities"]
    assert data["servers"]["memory"]["command"] == ["python", "-m", "symphony_l4_runner.mcp_memory_server"]
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    symphony = compose["services"]["symphony"]
    compose_env = symphony["environment"]
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
        assert variable in compose_env
    assert "3334:3334" in symphony["ports"]
    assert "${HOME}/.mcp-auth:/root/.mcp-auth" in symphony["volumes"]
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "MCP_JIRA_COMMAND=npx -y mcp-remote https://mcp.atlassian.com/v1/sse 3334" in env_example
    assert "--host 0.0.0.0" in env_example
    assert "--auth-timeout 120" in env_example
    assert "--transport sse-only" in env_example


def check_workflow() -> None:
    text = (ROOT / "WORKFLOW.md").read_text(encoding="utf-8")
    data = yaml.safe_load(extract_frontmatter(text))
    assert data["tracker"]["kind"] == "jira"
    assert data["codex"]["host_surface"] == "desktop_app"
    assert data["codex"]["container_surface"] == "cli_or_app_server"
    assert data["codex"]["command"].startswith("codex exec")
    assert "--ephemeral" in data["codex"]["command"]
    assert "--skip-git-repo-check" in data["codex"]["command"]
    assert "--ask-for-approval" not in data["codex"]["command"]
    assert data["codex"]["app_server_command"] == "codex app-server"
    assert data["memory"]["db_path"] == "/workspace/.memory/project-memory.sqlite3"
    assert data["quality_gates"]["skill"] == "superpowers-l4-quality-gates"
    assert "verification-before-completion" in data["quality_gates"]["required_workflows"]
    assert "memory" in data["mcp"]["required_servers"]
    assert data["security"]["api_keys_allowed"] is False
    assert "create-plan-symphony" in text
    assert "Step 1" in text and "Step 5" in text
    required_phrases = (
        "concrete implementation slice",
        "broad issue",
        "greenfield project",
        "missing Jira ticket",
        "Vertical slice contract",
        "create the contracted Jira slice tickets before implementation",
        "independent verifier pass",
        "plan-vs-implementation drift",
    )
    missing = [phrase for phrase in required_phrases if phrase not in text]
    if missing:
        raise AssertionError(f"workflow missing contract-first policy text: {', '.join(missing)}")


def check_agents_contract_policy() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    required_phrases = (
        "## Contract-First Vertical Slicing",
        "All coding work must be delivered as contract-first vertical slices.",
        "A builder may implement only one bounded, testable behavior at a time.",
        "Do not proceed to implementation until the persisted plan contains the vertical slice contract.",
        "If Jira tickets do not exist for a greenfield project, create the required contracted Jira slices before coding.",
        "Implement only the selected contracted slice, not the entire initiative.",
    )
    missing = [phrase for phrase in required_phrases if phrase not in text]
    if missing:
        raise AssertionError(f"AGENTS.md missing contract-first policy text: {', '.join(missing)}")


def check_create_plan_contract_policy() -> None:
    text = (ROOT / ".agents/skills/create-plan-symphony/SKILL.md").read_text(encoding="utf-8")
    required_phrases = (
        "## Work Item Classification",
        "Existing concrete Jira implementation slice",
        "Broad Jira issue that needs child slices",
        "Greenfield project with no Jira breakdown",
        "Missing or nonexistent Jira issue reference",
        "## Vertical slice contract",
        "### Slice outcome",
        "### Behavior contract",
        "### Interface contract",
        "### Data contract",
        "### Non-goals",
        "### Acceptance criteria",
        "### Verification contract",
        "### Independent verifier instructions",
        "Do not implement multiple greenfield slices in one pass.",
    )
    missing = [phrase for phrase in required_phrases if phrase not in text]
    if missing:
        raise AssertionError(f"create-plan-symphony missing contract-first policy text: {', '.join(missing)}")


def check_example_plan() -> None:
    text = (ROOT / ".plans/EXAMPLE.md").read_text(encoding="utf-8")
    missing = [section for section in REQUIRED_PLAN_SECTIONS if section not in text]
    if missing:
        raise AssertionError(f"example plan missing sections: {', '.join(missing)}")
    action_count = sum(1 for line in text.splitlines() if line.startswith("[ ] "))
    assert 6 <= action_count <= 10


def check_readme() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "codex login" in text
    assert "docker compose up" in text
    assert "desktop app itself does not run inside Docker" in text
    assert "Project Memory" in text
    assert "SQLite" in text
    assert "Superpowers L4 Quality Gates" in text
    assert "scripts/demo_test_run.py" in text
    assert "scripts/e2e_scenario.py" in text
    assert "End-To-End Evidence Scenario" in text
    for path in README_INSTALL_PATHS:
        assert path in text


def check_scripts_run() -> None:
    example = ROOT / ".plans/EXAMPLE.md"
    persist = ROOT / ".agents/skills/create-plan-symphony/scripts/persist_plan.py"
    escalate = ROOT / ".agents/skills/create-plan-symphony/scripts/escalate_to_human.py"
    with tempfile.TemporaryDirectory() as temp_dir:
        with example.open("rb") as stdin:
            result = subprocess.run(
                [sys.executable, str(persist), "--issue-id", "VAL-1", "--plans-dir", temp_dir],
                cwd=ROOT,
                stdin=stdin,
                text=False,
                capture_output=True,
                check=False,
            )
        if result.returncode != 0:
            raise AssertionError(result.stderr.decode("utf-8", "replace"))
        assert (Path(temp_dir) / "VAL-1.md").exists()

        result = subprocess.run(
            [
                sys.executable,
                str(escalate),
                "--issue-id",
                "VAL-1",
                "--reason",
                "Need product clarification",
                "--plans-dir",
                temp_dir,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        assert (Path(temp_dir) / "escalations.log").exists()

        memory = ROOT / "scripts/project_memory.py"
        db_path = Path(temp_dir) / "project-memory.sqlite3"
        result = subprocess.run(
            [
                sys.executable,
                str(memory),
                "--db",
                str(db_path),
                "capture",
                "--kind",
                "decision",
                "--title",
                "Validation memory",
                "--body",
                "Repository validation verifies durable SQLite project memory.",
                "--issue-id",
                "VAL-1",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        result = subprocess.run(
            [
                sys.executable,
                str(memory),
                "--db",
                str(db_path),
                "boot-context",
                "--issue-id",
                "VAL-1",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        assert "Validation memory" in result.stdout


def check_no_disallowed_tracker_terms() -> None:
    ignored = {
        ".git",
        ".pytest_cache",
        "__pycache__",
        ".demo-workspaces",
        ".e2e-workspaces",
        ".evidence",
        "evidence",
        ".memory",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
    }
    offenders: list[str] = []
    for path in ROOT.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        disallowed = ("Lin" + "ear", "lin" + "ear")
        if any(term in text for term in disallowed):
            offenders.append(str(path.relative_to(ROOT)))
    if offenders:
        raise AssertionError(f"disallowed tracker term found in: {', '.join(offenders)}")


def extract_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        raise AssertionError("file does not start with YAML front matter")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise AssertionError("unterminated YAML front matter")
    return parts[1]


if __name__ == "__main__":
    raise SystemExit(main())
