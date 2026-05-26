from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PERSIST_PLAN_PATH = ROOT / ".agents/skills/create-plan-symphony/scripts/persist_plan.py"


def load_persist_plan_module():
    spec = importlib.util.spec_from_file_location("persist_plan", PERSIST_PLAN_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load persist_plan.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALID_CONTRACT_PLAN = """# Plan

Implement one contracted slice.

## Vertical slice contract

### Slice outcome
An observable outcome.

### Behavior contract
The inputs, outputs, state changes, and edge cases.

### Interface contract
The commands, files, functions, routes, or APIs involved.

### Data contract
None.

### Non-goals
Do not change unrelated systems.

### Acceptance criteria
- [ ] The observable behavior is delivered.
- [ ] Unrelated behavior is unchanged.

### Verification contract
- [ ] Run `python scripts/validate_repo.py`.

### Independent verifier instructions
Compare the completed diff against this contract and report any drift.

## Scope
- In: One contracted implementation slice.
- Out: Broader initiative work.

## Action items
[ ] Read the Jira issue and confirm the selected slice.
[ ] Review the persisted contract and affected files.
[ ] Add tests for the accepted behavior.
[ ] Implement only the selected slice.
[ ] Run the verification contract.
[ ] Compare the diff against the contract.

## Validation
- Run `python scripts/validate_repo.py`.

## Assumptions
- None.

## Open questions
- None.
"""


class ContractFirstVerticalSlicingTests(unittest.TestCase):
    def test_persist_plan_requires_vertical_slice_contract(self) -> None:
        persist_plan = load_persist_plan_module()
        plan_without_contract = VALID_CONTRACT_PLAN.replace(
            "## Vertical slice contract",
            "## Implementation notes",
        )

        with self.assertRaisesRegex(persist_plan.PlanError, "Vertical slice contract"):
            persist_plan.validate_plan(plan_without_contract)

    def test_persist_plan_accepts_complete_vertical_slice_contract(self) -> None:
        persist_plan = load_persist_plan_module()

        persist_plan.validate_plan(VALID_CONTRACT_PLAN)

    def test_persist_plan_rejects_empty_contract_subsection(self) -> None:
        persist_plan = load_persist_plan_module()
        plan_with_empty_behavior_contract = VALID_CONTRACT_PLAN.replace(
            "### Behavior contract\nThe inputs, outputs, state changes, and edge cases.",
            "### Behavior contract\n",
        )

        with self.assertRaisesRegex(persist_plan.PlanError, "Behavior contract"):
            persist_plan.validate_plan(plan_with_empty_behavior_contract)

    def test_persist_plan_rejects_acceptance_criteria_without_checklist_items(self) -> None:
        persist_plan = load_persist_plan_module()
        plan_without_acceptance_checklist = VALID_CONTRACT_PLAN.replace(
            "- [ ] The observable behavior is delivered.\n- [ ] Unrelated behavior is unchanged.",
            "The observable behavior is delivered.",
        )

        with self.assertRaisesRegex(persist_plan.PlanError, "Acceptance criteria"):
            persist_plan.validate_plan(plan_without_acceptance_checklist)

    def test_create_plan_skill_declares_required_contract_template(self) -> None:
        text = (ROOT / ".agents/skills/create-plan-symphony/SKILL.md").read_text(encoding="utf-8")

        for heading in (
            "## Vertical slice contract",
            "### Slice outcome",
            "### Behavior contract",
            "### Interface contract",
            "### Data contract",
            "### Non-goals",
            "### Acceptance criteria",
            "### Verification contract",
            "### Independent verifier instructions",
        ):
            self.assertIn(heading, text)

    def test_workflow_declares_greenfield_slicing_and_verifier_pass(self) -> None:
        text = (ROOT / "WORKFLOW.md").read_text(encoding="utf-8")

        for phrase in (
            "concrete implementation slice",
            "broad issue",
            "greenfield project",
            "missing Jira ticket",
            "create the contracted Jira slice tickets before implementation",
            "independent verifier pass",
            "plan-vs-implementation drift",
        ):
            self.assertIn(phrase, text)

    def test_agents_policy_requires_one_contract_first_slice_at_a_time(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        for phrase in (
            "## Contract-First Vertical Slicing",
            "All coding work must be delivered as contract-first vertical slices.",
            "A builder may implement only one bounded, testable behavior at a time.",
            "Do not proceed to implementation until the persisted plan contains the vertical slice contract.",
            "If Jira tickets do not exist for a greenfield project, create the required contracted Jira slices before coding.",
            "Implement only the selected contracted slice, not the entire initiative.",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
