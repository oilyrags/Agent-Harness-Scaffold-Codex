from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from symphony_l4_runner.config import load_workflow


class QualityGateSkillTests(unittest.TestCase):
    def test_superpowers_quality_gate_skill_is_repo_owned(self) -> None:
        skill_dir = ROOT / ".agents/skills/superpowers-l4-quality-gates"
        skill = skill_dir / "SKILL.md"
        self.assertTrue(skill.exists())

        frontmatter = extract_frontmatter(skill.read_text(encoding="utf-8"))
        metadata = yaml.safe_load(frontmatter)
        self.assertEqual("superpowers-l4-quality-gates", metadata["name"])
        self.assertIn("autonomous", metadata["description"])

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
        self.assertTrue(expected.issubset(actual))

    def test_workflow_requires_quality_gates(self) -> None:
        workflow = load_workflow(ROOT / "WORKFLOW.md")
        quality_gates = workflow.config["quality_gates"]

        self.assertEqual("superpowers-l4-quality-gates", quality_gates["skill"])
        self.assertIn("verification-before-completion", quality_gates["required_workflows"])
        self.assertIn("superpowers-l4-quality-gates", workflow.prompt_template)
        self.assertIn("Quality Gate", workflow.prompt_template)


def extract_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        raise AssertionError("file does not start with YAML front matter")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise AssertionError("unterminated YAML front matter")
    return parts[1]


if __name__ == "__main__":
    unittest.main()
