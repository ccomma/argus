import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class Phase1CliTest(unittest.TestCase):
    def test_contract_draft_command_writes_local_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "contract",
                    "draft",
                    "--intent",
                    "Build the Argus Phase 1 MVP.",
                    "--mode",
                    "quick",
                    "--goal",
                    "Create a CLI work contract MVP.",
                    "--outputs",
                    "Work contract JSON.",
                    "--acceptance-criteria",
                    "The CLI writes a local contract file.",
                    "--store",
                    str(store),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            contract = json.loads(result.stdout)
            contract_path = store / "contracts" / contract["id"] / "contract.json"

            self.assertEqual(contract["status"], "ready")
            self.assertTrue(contract_path.exists())

    def test_contract_evaluate_command_writes_evaluation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            draft = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "contract",
                    "draft",
                    "--intent",
                    "Create a PRD for Phase 1.",
                    "--goal",
                    "Define the Work Contract MVP.",
                    "--outputs",
                    "PRD.",
                    "--acceptance-criteria",
                    "The PRD contains acceptance criteria.",
                    "--store",
                    str(store),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            contract = json.loads(draft.stdout)
            deliverable = Path(tmpdir) / "prd.md"
            deliverable.write_text("# PRD\n\n## Background\nx\n\n## Goals\nx\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "contract",
                    "evaluate",
                    contract["id"],
                    str(deliverable),
                    "--type",
                    "prd",
                    "--store",
                    str(store),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            evaluation = json.loads(result.stdout)
            evaluations_dir = store / "contracts" / contract["id"] / "evaluations"

            self.assertEqual(evaluation["status"], "partial")
            self.assertIn("Acceptance Criteria", evaluation["missing_items"])
            self.assertTrue(any(evaluations_dir.iterdir()))

    def test_contract_show_and_score_commands_read_saved_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            draft = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "contract",
                    "draft",
                    "--intent",
                    "Plan Phase 1 next steps.",
                    "--mode",
                    "quick",
                    "--goal",
                    "Plan the next implementation slice.",
                    "--outputs",
                    "Implementation plan.",
                    "--acceptance-criteria",
                    "The plan identifies testable commands.",
                    "--store",
                    str(store),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            contract = json.loads(draft.stdout)

            shown = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "contract",
                    "show",
                    contract["id"],
                    "--store",
                    str(store),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            scored = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "contract",
                    "score",
                    contract["id"],
                    "--store",
                    str(store),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual(json.loads(shown.stdout)["id"], contract["id"])
            self.assertEqual(json.loads(scored.stdout)["overall_score"], 1.0)

    def test_contract_render_command_outputs_evaluable_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            draft = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "contract",
                    "draft",
                    "--intent",
                    "Create a roadmap for Argus Phase 1.",
                    "--mode",
                    "quick",
                    "--goal",
                    "Describe the next Phase 1 implementation milestones.",
                    "--outputs",
                    "Roadmap.",
                    "--acceptance-criteria",
                    "The roadmap has phases and exit conditions.",
                    "--store",
                    str(store),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            contract = json.loads(draft.stdout)

            rendered = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "contract",
                    "render",
                    contract["id"],
                    "--type",
                    "roadmap",
                    "--store",
                    str(store),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            rendered_path = Path(tmpdir) / "roadmap.md"
            rendered_path.write_text(rendered.stdout, encoding="utf-8")
            evaluated = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "contract",
                    "evaluate",
                    contract["id"],
                    str(rendered_path),
                    "--type",
                    "roadmap",
                    "--store",
                    str(store),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            deliverable_path = store / "contracts" / contract["id"] / "deliverables" / "roadmap.md"
            evidence_path = store / "contracts" / contract["id"] / "evidence.jsonl"

            self.assertIn("## Phases", rendered.stdout)
            self.assertEqual(json.loads(evaluated.stdout)["status"], "pass")
            self.assertTrue(deliverable_path.exists())
            self.assertIn("deliverable_rendered", evidence_path.read_text(encoding="utf-8"))
            self.assertIn("deliverable_evaluated", evidence_path.read_text(encoding="utf-8"))

    def test_contract_start_interactively_asks_questions_and_saves_ready_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "contract",
                    "start",
                    "--intent",
                    "Prepare the final Phase 1 acceptance pass.",
                    "--mode",
                    "quick",
                    "--store",
                    str(store),
                ],
                input="\n".join(
                    [
                        "Complete the Phase 1 MVP acceptance pass.",
                        "Acceptance report and runnable CLI.",
                        "All Phase 1 tests and CLI smoke checks pass.",
                    ]
                )
                + "\n",
                check=True,
                capture_output=True,
                text=True,
            )

            contract = json.loads(result.stdout)
            contract_path = store / "contracts" / contract["id"] / "contract.json"

            self.assertEqual(contract["status"], "ready")
            self.assertEqual(contract["goal"], "Complete the Phase 1 MVP acceptance pass.")
            self.assertTrue(contract_path.exists())


if __name__ == "__main__":
    unittest.main()
