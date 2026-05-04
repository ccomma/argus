import tempfile
import unittest
from pathlib import Path

from argus.core import ArgusCore
from argus.ledger import (
    CandidateLearningItem,
    ContractEvidenceIngestor,
    EventLedger,
    EventRecord,
    LearningExtractor,
    LearningLedger,
    LearningReporter,
    TranscriptIngestor,
)
from argus.storage import ContractStorage


class Phase2LedgerTest(unittest.TestCase):
    def test_contract_evidence_ingestion_writes_deduplicated_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ContractStorage(Path(tmpdir) / ".argus")
            core = ArgusCore(storage)
            contract = core.draft_contract(
                intent="Create a Phase 2 ledger fixture.",
                mode="quick",
                answers={
                    "goal": "Generate contract evidence.",
                    "outputs": "Roadmap.",
                    "acceptance_criteria": "Evidence can be ingested.",
                },
            )
            rendered = core.render_deliverable(contract.id, "roadmap")
            core.evaluate_deliverable(contract_id=contract.id, deliverable_type="roadmap", text=rendered)

            ledger = EventLedger(Path(tmpdir) / ".argus" / "ledger" / "events.jsonl")
            ingestor = ContractEvidenceIngestor(storage, ledger)
            first_count = ingestor.ingest(contract.id)
            second_count = ingestor.ingest(contract.id)

            events = ledger.list_events()

        self.assertEqual(first_count, 2)
        self.assertEqual(second_count, 0)
        self.assertEqual([event.event_type for event in events], ["deliverable_rendered", "deliverable_evaluated"])
        self.assertTrue(all(event.source == "contract_evidence" for event in events))
        self.assertTrue(all(event.contract_id == contract.id for event in events))

    def test_transcript_ingestion_and_learning_extraction_create_candidates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            events_path = Path(tmpdir) / ".argus" / "ledger" / "events.jsonl"
            learnings_path = Path(tmpdir) / ".argus" / "ledger" / "candidate_learnings.jsonl"
            ledger = EventLedger(events_path)
            learning_ledger = LearningLedger(learnings_path)
            fixture = Path(__file__).parent / "fixtures" / "codex_mixed_events.jsonl"

            imported = TranscriptIngestor(ledger).ingest(fixture)
            candidates = LearningExtractor().extract(ledger.list_events())
            learning_ledger.append_many(candidates)
            loaded_candidates = learning_ledger.list_items()

        self.assertEqual(imported, 4)
        self.assertGreaterEqual(len(loaded_candidates), 2)
        self.assertIn("correction", {item.type for item in loaded_candidates})
        self.assertIn("tool_pitfall", {item.type for item in loaded_candidates})
        self.assertTrue(all(item.status == "pending" for item in loaded_candidates))
        self.assertTrue(all(item.evidence_refs for item in loaded_candidates))

    def test_learning_extractor_accepts_focused_rules(self):
        event = EventRecord.create(
            source="test",
            event_type="custom_signal",
            evidence={"summary": "Custom signal should become a candidate."},
        )
        extractor = LearningExtractor(
            rules=[
                lambda events: [
                    CandidateLearningItem.create(
                        summary=event.evidence["summary"],
                        type="custom",
                        evidence_refs=[event.id],
                        reverse_learning_target="capability_pack",
                    )
                    for event in events
                    if event.event_type == "custom_signal"
                ]
            ]
        )

        candidates = extractor.extract([event])

        self.assertEqual([candidate.type for candidate in candidates], ["custom"])
        self.assertEqual(candidates[0].evidence_refs, [event.id])

    def test_failed_contract_evaluation_becomes_deliverable_gap_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ContractStorage(Path(tmpdir) / ".argus")
            core = ArgusCore(storage)
            contract = core.draft_contract(
                intent="Create a PRD that intentionally misses sections.",
                mode="quick",
                answers={
                    "goal": "Create a PRD.",
                    "outputs": "PRD.",
                    "acceptance_criteria": "The PRD includes success and acceptance criteria.",
                },
            )
            core.evaluate_deliverable(
                contract_id=contract.id,
                deliverable_type="prd",
                text="# PRD\n\n## Background\nx\n",
            )
            ledger = EventLedger(Path(tmpdir) / ".argus" / "ledger" / "events.jsonl")
            ContractEvidenceIngestor(storage, ledger).ingest(contract.id)

            candidates = LearningExtractor().extract(ledger.list_events())

        self.assertIn("deliverable_gap", {item.type for item in candidates})
        gap = next(item for item in candidates if item.type == "deliverable_gap")
        self.assertEqual(gap.reverse_learning_target, "deliverable_contract")
        self.assertEqual(gap.confidence, 0.7)

    def test_learning_report_writes_markdown_and_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / ".argus"
            ledger = EventLedger(root / "ledger" / "events.jsonl")
            TranscriptIngestor(ledger).ingest(Path(__file__).parent / "fixtures" / "codex_mixed_events.jsonl")
            learning_ledger = LearningLedger(root / "ledger" / "candidate_learnings.jsonl")
            learning_ledger.append_many(LearningExtractor().extract(ledger.list_events()))

            reporter = LearningReporter(root / "ledger" / "reports")
            report = reporter.write(ledger.list_events(), learning_ledger.list_items())
            markdown_exists = report.markdown_path.exists()
            json_exists = report.json_path.exists()
            markdown_text = report.markdown_path.read_text(encoding="utf-8")

        self.assertTrue(markdown_exists)
        self.assertTrue(json_exists)
        self.assertIn("Candidate Learnings", markdown_text)


if __name__ == "__main__":
    unittest.main()
