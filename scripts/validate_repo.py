#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    ".agents/skills/create-plan-symphony/SKILL.md",
    ".agents/skills/create-plan-symphony/agents/openai.yaml",
    ".agents/skills/create-plan-symphony/scripts/persist_plan.py",
    ".agents/skills/create-plan-symphony/scripts/escalate_to_human.py",
    "WORKFLOW.md",
    ".plans/EXAMPLE.md",
    "README.md",
    "Dockerfile",
    "docker-compose.yml",
    "config/mcp.servers.yaml",
    "scripts/demo_test_run.py",
)

REQUIRED_PLAN_SECTIONS = (
    "# Plan",
    "## Scope",
    "## Action items",
    "## Validation",
    "## Assumptions",
    "## Open questions",
)

README_INSTALL_PATHS = (
    ".agents/skills/create-plan-symphony/",
    ".plans/",
    "~/.codex",
    "/root/.codex:ro",
    "/workspace",
)


def main() -> int:
    checks = [
        check_required_files,
        check_skill_frontmatter_yaml,
        check_openai_yaml,
        check_mcp_yaml,
        check_workflow,
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


def check_openai_yaml() -> None:
    data = yaml.safe_load((ROOT / ".agents/skills/create-plan-symphony/agents/openai.yaml").read_text(encoding="utf-8"))
    assert data["interface"]["display_name"] == "Create Plan Symphony"
    assert "$create-plan-symphony" in data["interface"]["default_prompt"]


def check_mcp_yaml() -> None:
    data = yaml.safe_load((ROOT / "config/mcp.servers.yaml").read_text(encoding="utf-8"))
    assert data["auth"]["api_keys_allowed"] is False
    servers = data["servers"]
    for name in ("filesystem", "shell", "browser", "github", "jira", "notion", "miro", "figma", "lovable", "postgres", "chroma"):
        assert name in servers
        assert servers[name]["capabilities"]


def check_workflow() -> None:
    text = (ROOT / "WORKFLOW.md").read_text(encoding="utf-8")
    data = yaml.safe_load(extract_frontmatter(text))
    assert data["tracker"]["kind"] == "jira"
    assert data["codex"]["host_surface"] == "desktop_app"
    assert data["codex"]["container_surface"] == "cli_or_app_server"
    assert data["codex"]["command"].startswith("codex exec")
    assert "--ephemeral" in data["codex"]["command"]
    assert "--skip-git-repo-check" in data["codex"]["command"]
    assert data["codex"]["app_server_command"] == "codex app-server"
    assert data["security"]["api_keys_allowed"] is False
    assert "create-plan-symphony" in text
    assert "Step 1" in text and "Step 5" in text


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
    assert "scripts/demo_test_run.py" in text
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


def check_no_disallowed_tracker_terms() -> None:
    ignored = {".git", ".pytest_cache", "__pycache__"}
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
