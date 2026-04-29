import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class Phase2CliTest(unittest.TestCase):
    def test_ledger_and_learning_cli_flow(self):
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
                    "Create a ledger CLI fixture.",
                    "--mode",
                    "quick",
                    "--goal",
                    "Generate evidence for ledger ingestion.",
                    "--outputs",
                    "Roadmap.",
                    "--acceptance-criteria",
                    "Evidence is ingested.",
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
            roadmap = Path(tmpdir) / "roadmap.md"
            roadmap.write_text(rendered.stdout, encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "contract",
                    "evaluate",
                    contract["id"],
                    str(roadmap),
                    "--type",
                    "roadmap",
                    "--store",
                    str(store),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            ingest_contract = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "ledger",
                    "ingest-contract",
                    contract["id"],
                    "--store",
                    str(store),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            ingest_transcript = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "ledger",
                    "ingest-transcript",
                    str(Path(__file__).parent / "fixtures" / "codex_mixed_events.jsonl"),
                    "--store",
                    str(store),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            listed = subprocess.run(
                [sys.executable, "-m", "argus.cli", "ledger", "list", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )
            extracted = subprocess.run(
                [sys.executable, "-m", "argus.cli", "learning", "extract", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )
            extracted_again = subprocess.run(
                [sys.executable, "-m", "argus.cli", "learning", "extract", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )
            learning_list = subprocess.run(
                [sys.executable, "-m", "argus.cli", "learning", "list", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )
            report = subprocess.run(
                [sys.executable, "-m", "argus.cli", "learning", "report", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(json.loads(ingest_contract.stdout)["imported"], 2)
        self.assertEqual(json.loads(ingest_transcript.stdout)["imported"], 4)
        self.assertEqual(len(json.loads(listed.stdout)), 6)
        self.assertGreaterEqual(json.loads(extracted.stdout)["created"], 2)
        self.assertEqual(json.loads(extracted_again.stdout)["created"], 0)
        self.assertGreaterEqual(len(json.loads(learning_list.stdout)), 2)
        self.assertIn("learning-report.md", json.loads(report.stdout)["markdown_path"])

    def test_phase2_cli_reports_missing_contract_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "ledger",
                    "ingest-contract",
                    "missing-contract",
                    "--store",
                    str(Path(tmpdir) / ".argus"),
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_phase2_cli_reports_bad_transcript_jsonl_with_line_number(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad = Path(tmpdir) / "bad.jsonl"
            bad.write_text('{"event_type":"user_correction"}\n{bad json}\n', encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "ledger",
                    "ingest-transcript",
                    str(bad),
                    "--store",
                    str(Path(tmpdir) / ".argus"),
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("line 2", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
