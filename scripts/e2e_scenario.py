#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from symphony_l4_runner.security import redact


ISSUE_ID = "E2E-1"
REQUIRED_MCP_SERVERS = (
    "filesystem",
    "shell",
    "memory",
    "browser",
    "github",
    "jira",
    "notion",
    "miro",
    "figma",
    "lovable",
    "postgres",
    "chroma",
)


@dataclass
class StepResult:
    index: int
    name: str
    command: list[str]
    returncode: int
    passed: bool
    stdout_path: str
    stderr_path: str
    notes: str


class E2ERunner:
    def __init__(self, *, evidence_dir: Path, timeout: int):
        self.evidence_dir = evidence_dir
        self.logs_dir = evidence_dir / "logs"
        self.timeout = timeout
        self.results: list[StepResult] = []
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        name: str,
        command: list[str],
        *,
        expected_returncode: int = 0,
        notes: str = "",
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> StepResult:
        index = len(self.results) + 1
        slug = _slug(name)
        stdout_path = self.logs_dir / f"{index:02d}-{slug}.stdout.log"
        stderr_path = self.logs_dir / f"{index:02d}-{slug}.stderr.log"
        command_path = self.logs_dir / f"{index:02d}-{slug}.command.json"
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        started = datetime.now(timezone.utc).isoformat()

        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout or self.timeout,
                env=run_env,
            )
            stdout = redact(completed.stdout)
            stderr = redact(completed.stderr)
            returncode = completed.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = redact(exc.stdout or "")
            stderr = redact((exc.stderr or "") + f"\nTIMEOUT after {timeout or self.timeout}s")
            returncode = 124

        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        command_path.write_text(
            json.dumps(
                {
                    "name": name,
                    "command": command,
                    "started_at": started,
                    "expected_returncode": expected_returncode,
                    "actual_returncode": returncode,
                    "notes": notes,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        result = StepResult(
            index=index,
            name=name,
            command=command,
            returncode=returncode,
            passed=returncode == expected_returncode,
            stdout_path=str(stdout_path.relative_to(ROOT)),
            stderr_path=str(stderr_path.relative_to(ROOT)),
            notes=notes,
        )
        self.results.append(result)
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {index:02d} {name}")
        if not result.passed:
            print(stderr or stdout, file=sys.stderr)
        return result

    def write_summary(self) -> Path:
        summary = self.evidence_dir / "SUMMARY.md"
        results_json = self.evidence_dir / "results.json"
        passed_count = sum(1 for result in self.results if result.passed)
        failed = [result for result in self.results if not result.passed]
        results_json.write_text(
            json.dumps(
                {
                    "issue_id": ISSUE_ID,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "passed": not failed,
                    "passed_count": passed_count,
                    "total_count": len(self.results),
                    "results": [result.__dict__ for result in self.results],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        lines = [
            f"# E2E Scenario Evidence: {ISSUE_ID}",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            f"Overall result: {'PASS' if not failed else 'FAIL'}",
            f"Steps passed: {passed_count}/{len(self.results)}",
            "",
            "## Step Evidence",
            "",
            "| # | Step | Result | Evidence | Notes |",
            "|---|---|---|---|---|",
        ]
        for result in self.results:
            status = "PASS" if result.passed else f"FAIL ({result.returncode})"
            stdout_rel = Path(result.stdout_path).relative_to(self.evidence_dir.relative_to(ROOT)).as_posix()
            stderr_rel = Path(result.stderr_path).relative_to(self.evidence_dir.relative_to(ROOT)).as_posix()
            evidence = f"[stdout]({stdout_rel}) / [stderr]({stderr_rel})"
            lines.append(
                f"| {result.index} | {result.name} | {status} | {evidence} | {_escape_table(result.notes)} |"
            )

        lines.extend(
            [
                "",
                "## Feature Coverage",
                "",
                "| Feature | Evidence Step | Expected Proof |",
                "|---|---|---|",
                "| Docker runtime | Build Symphony image | Compose image builds successfully. |",
                "| Codex CLI in Docker | Codex CLI version | Container reports `codex --version`. |",
                "| Codex App Server in Docker | Codex App Server help | Container reports App Server help. |",
                "| External internet for research | Fetch Symphony SPEC and Playwright browser fetch | HTTPS and browser navigation return 200. |",
                "| SSO credential safety | Credential mount read-only | `/root/.codex` mount is present and read-only. |",
                "| No API keys | No forbidden API key env | Container does not receive common API key env vars. |",
                "| Repository contract | Repository validator | Skill, workflow, docs, MCP, and scripts validate. |",
                "| Test suite | Unit tests | Memory, CLI, and prompt-injection tests pass. |",
                "| Superpowers quality gates | Quality gate skill check | Repo-owned curated workflows are present and required by `WORKFLOW.md`. |",
                "| Plan persistence | Persist plan fixture | `.plans/E2E-1.md` is created with required sections. |",
                "| Jira escalation stub | Escalate to human | Escalation log contains `E2E-1`. |",
                "| Project memory | Memory capture/search/boot context | SQLite memory record is searchable and bootable. |",
                "| Secret rejection | Memory secret rejection | Unsafe secret-like memory write exits with code 2. |",
                "| MCP coverage | MCP matrix check | All required MCP servers and restrictions are declared. |",
                "| Symphony dry run | Supervisor dry run | Workflow loads and one supervisor tick completes. |",
                "| Demo run | Demo test run | Codex runtime, prompt render, workspace, memory, and dispatch are exercised. |",
                "",
                f"Machine-readable results: [results.json](./results.json)",
            ]
        )
        summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Codex + Symphony E2E evidence scenario.")
    parser.add_argument("--timeout", type=int, default=180, help="Default timeout per step in seconds.")
    parser.add_argument("--evidence-dir", type=Path, default=None, help="Evidence output directory.")
    args = parser.parse_args(argv)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    evidence_dir = args.evidence_dir or ROOT / "evidence" / f"e2e-{timestamp}"
    runner = E2ERunner(evidence_dir=evidence_dir, timeout=args.timeout)
    evidence_in_container = "/workspace/" + str(evidence_dir.relative_to(ROOT))
    memory_db = f"{evidence_in_container}/project-memory.sqlite3"

    runner.run("Build Symphony image", ["docker", "compose", "build", "symphony"], timeout=600)
    runner.run(
        "Codex CLI version",
        docker_run(["codex", "--version"]),
        notes="Confirms the autonomous container has the Codex CLI.",
    )
    runner.run(
        "Codex App Server help",
        docker_run(["codex", "app-server", "--help"]),
        notes="Confirms App Server entrypoint exists inside Docker.",
    )
    runner.run(
        "Credential mount read-only",
        docker_run(
            [
                "python",
                "-c",
                (
                    "from pathlib import Path\n"
                    "target='/root/.codex'\n"
                    "assert Path(target).exists(), 'missing /root/.codex mount'\n"
                    "for line in Path('/proc/self/mountinfo').read_text().splitlines():\n"
                    "    fields=line.split()\n"
                    "    if len(fields)>5 and fields[4]==target:\n"
                    "        print('mount_options=' + fields[5])\n"
                    "        assert 'ro' in fields[5].split(','), 'credential mount is not read-only'\n"
                    "        break\n"
                    "else:\n"
                    "    raise AssertionError('no mountinfo entry for /root/.codex')\n"
                ),
            ]
        ),
        notes="Verifies SSO credentials are mounted read-only, without writing to them.",
    )
    runner.run(
        "No forbidden API key env",
        docker_run(
            [
                "python",
                "-c",
                (
                    "import os\n"
                    "forbidden={'OPENAI_API_KEY','JIRA_API_TOKEN','GITHUB_TOKEN','ANTHROPIC_API_KEY'}\n"
                    "present=sorted(k for k in forbidden if os.environ.get(k))\n"
                    "print('present_forbidden_keys=' + ','.join(present))\n"
                    "assert not present, 'forbidden API key env vars present'\n"
                ),
            ]
        ),
        notes="Confirms common API key env vars are not passed into the container.",
    )
    runner.run(
        "Fetch Symphony SPEC",
        docker_run(
            [
                "python",
                "-c",
                (
                    "import urllib.request\n"
                    "url='https://raw.githubusercontent.com/openai/symphony/main/SPEC.md'\n"
                    "r=urllib.request.urlopen(url, timeout=20)\n"
                    "head=r.read(80).decode('utf-8','replace').splitlines()[0]\n"
                    "print(r.status)\n"
                    "print(head)\n"
                    "assert r.status == 200\n"
                ),
            ]
        ),
        notes="Confirms outbound HTTPS research from the autonomous container.",
    )
    runner.run(
        "Playwright browser fetch",
        docker_run(
            [
                "python",
                "-c",
                (
                    "from playwright.sync_api import sync_playwright\n"
                    "p=sync_playwright().start(); b=p.chromium.launch(headless=True)\n"
                    "page=b.new_page(); response=page.goto('https://example.com', wait_until='domcontentloaded', timeout=20000)\n"
                    "print(response.status if response else 'NO_RESPONSE'); print(page.title())\n"
                    "assert response and response.status == 200\n"
                    "b.close(); p.stop()\n"
                ),
            ]
        ),
        notes="Confirms browser-based research path works inside Docker.",
    )
    runner.run("Repository validator", docker_run(["python", "scripts/validate_repo.py"]))
    runner.run("Unit tests", docker_run(["python", "-m", "unittest", "discover", "-s", "tests"]))
    runner.run(
        "Quality gate skill check",
        docker_run(
            [
                "python",
                "-c",
                (
                    "from pathlib import Path\n"
                    "import yaml\n"
                    "skill=Path('.agents/skills/superpowers-l4-quality-gates/SKILL.md')\n"
                    "assert skill.exists()\n"
                    "frontmatter=skill.read_text().split('---\\n', 2)[1]\n"
                    "assert yaml.safe_load(frontmatter)['name'] == 'superpowers-l4-quality-gates'\n"
                    "workflow=yaml.safe_load(Path('WORKFLOW.md').read_text().split('---\\n', 2)[1])\n"
                    "required=set(workflow['quality_gates']['required_workflows'])\n"
                    "expected={'writing-plans','executing-plans','test-driven-development','systematic-debugging','verification-before-completion','requesting-code-review','finishing-development-branch'}\n"
                    "assert expected.issubset(required)\n"
                    "print('quality_gates=' + ','.join(sorted(required)))\n"
                ),
            ]
        ),
        notes="Confirms curated Superpowers workflows are repo-owned and required by WORKFLOW.md.",
    )
    runner.run(
        "Persist plan fixture",
        docker_run(
            [
                "sh",
                "-lc",
                (
                    f"rm -f .plans/{ISSUE_ID}.md .plans/escalations.log && "
                    f"python .agents/skills/create-plan-symphony/scripts/persist_plan.py --issue-id {ISSUE_ID} --plans-dir .plans < .plans/EXAMPLE.md && "
                    f"python -c \"from pathlib import Path; text=Path('.plans/{ISSUE_ID}.md').read_text(); "
                    "required=['## Scope','## Action items','## Validation','## Assumptions','## Open questions']; "
                    "missing=[s for s in required if s not in text]; assert not missing, missing; print('plan_sections_ok')\""
                ),
            ]
        ),
        notes="Exercises the create-plan-symphony persistence path with an E2E Jira issue id.",
    )
    runner.run(
        "Escalate to human",
        docker_run(
            [
                "sh",
                "-lc",
                (
                    f"python .agents/skills/create-plan-symphony/scripts/escalate_to_human.py --issue-id {ISSUE_ID} "
                    "--reason 'E2E needs clarification check' --plans-dir .plans && "
                    f"python -c \"from pathlib import Path; text=Path('.plans/escalations.log').read_text(); assert '{ISSUE_ID}' in text; print('escalation_logged')\""
                ),
            ]
        ),
        notes="Exercises the Jira escalation script and log evidence.",
    )
    runner.run(
        "Memory capture search boot context",
        docker_run(
            [
                "sh",
                "-lc",
                (
                    f"python scripts/project_memory.py --db {memory_db} capture --kind decision --title 'E2E memory decision' "
                    f"--body 'Durable E2E project memory is searchable and appears in boot context.' --issue-id {ISSUE_ID} --tag e2e && "
                    f"python scripts/project_memory.py --db {memory_db} search 'durable searchable' --issue-id {ISSUE_ID} > {evidence_in_container}/memory-search.json && "
                    f"python scripts/project_memory.py --db {memory_db} boot-context --issue-id {ISSUE_ID} > {evidence_in_container}/memory-boot-context.md && "
                    f"python -c \"from pathlib import Path; text=Path('{evidence_in_container}/memory-boot-context.md').read_text(); assert 'E2E memory decision' in text; print('memory_boot_context_ok')\""
                ),
            ]
        ),
        notes="Exercises local SQLite project memory and writes searchable evidence artifacts.",
    )
    runner.run(
        "Memory secret rejection",
        docker_run(
            [
                "sh",
                "-lc",
                (
                    f"python scripts/project_memory.py --db {memory_db} capture --kind decision --title Unsafe "
                    "--body 'api_key=abc1234567890' >/tmp/e2e-secret.out 2>/tmp/e2e-secret.err; "
                    "status=$?; cat /tmp/e2e-secret.err; test $status -eq 2"
                ),
            ]
        ),
        notes="Confirms memory rejects secret-like writes.",
    )
    runner.run(
        "MCP matrix check",
        docker_run(
            [
                "python",
                "-c",
                (
                    "import yaml\n"
                    "data=yaml.safe_load(open('config/mcp.servers.yaml'))\n"
                    f"required={list(REQUIRED_MCP_SERVERS)!r}\n"
                    "servers=data['servers']\n"
                    "missing=[name for name in required if name not in servers or not servers[name].get('capabilities')]\n"
                    "assert not missing, missing\n"
                    "assert servers['github']['restrictions']['no_main_branch_commits'] is True\n"
                    "assert data['auth']['api_keys_allowed'] is False\n"
                    "print('mcp_servers=' + ','.join(required))\n"
                ),
            ]
        ),
        notes="Verifies all required MCP declarations and GitHub main-branch restriction.",
    )
    runner.run(
        "Supervisor dry run",
        docker_run(["python", "-m", "symphony_l4_runner", "--workflow", "/workspace/WORKFLOW.md", "--once", "--dry-run"]),
        notes="Runs one Symphony supervisor tick without live external connector calls.",
    )
    runner.run(
        "Demo test run",
        docker_run(["python", "scripts/demo_test_run.py"]),
        notes="Runs the bundled demo, including Codex runtime detection, prompt render, workspace creation, memory, and dry-run dispatch.",
    )

    summary = runner.write_summary()
    print(f"summary={summary}")
    return 0 if all(result.passed for result in runner.results) else 1


def docker_run(command: list[str]) -> list[str]:
    return ["docker", "compose", "run", "--rm", "--no-deps", "symphony", *command]


def _slug(value: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "-" for char in value)
    return "-".join(part for part in safe.split("-") if part)[:80]


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
