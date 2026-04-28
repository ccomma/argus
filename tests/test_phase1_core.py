import tempfile
import unittest
from pathlib import Path

from argus.core import ArgusCore
from argus.storage import ContractStorage


class Phase1CoreTest(unittest.TestCase):
    def test_core_drafts_renders_and_evaluates_without_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            core = ArgusCore(ContractStorage(Path(tmpdir) / ".argus"))
            contract = core.draft_contract(
                intent="Create a Phase 1 closeout roadmap.",
                mode="quick",
                answers={
                    "goal": "Document the final Phase 1 state.",
                    "outputs": "Roadmap.",
                    "acceptance_criteria": "The roadmap passes evaluation.",
                },
            )

            rendered = core.render_deliverable(contract.id, "roadmap")
            evaluation = core.evaluate_deliverable(
                contract_id=contract.id,
                deliverable_type="roadmap",
                text=rendered,
            )

            self.assertEqual(contract.status, "ready")
            self.assertIn("## Phases", rendered)
            self.assertEqual(evaluation.status, "pass")


if __name__ == "__main__":
    unittest.main()
