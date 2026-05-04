import json
import tempfile
import unittest
from pathlib import Path

from argus.handoff import HandoffManager, HandoffRecord


class Phase8HandoffTest(unittest.TestCase):
    def test_handoff_record_creates_deterministic_id(self):
        r1 = HandoffRecord.create(
            from_role_id="product-strategist",
            to_role_id="product-manager",
            contract_id="contract-1",
            handoff_reason="phase complete",
        )
        r2 = HandoffRecord.create(
            from_role_id="product-strategist",
            to_role_id="product-manager",
            contract_id="contract-1",
            handoff_reason="phase complete",
        )
        self.assertEqual(r1.id, r2.id)
        self.assertEqual(r1.from_role_id, "product-strategist")
        self.assertEqual(r1.to_role_id, "product-manager")
        self.assertEqual(r1.contract_id, "contract-1")

    def test_handoff_record_different_inputs_different_ids(self):
        r1 = HandoffRecord.create(from_role_id="a", to_role_id="b")
        r2 = HandoffRecord.create(from_role_id="b", to_role_id="c")
        self.assertNotEqual(r1.id, r2.id)

    def test_manager_creates_and_loads_handoff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HandoffManager(Path(tmpdir) / "handoffs")
            record = mgr.create(
                from_role_id="researcher",
                to_role_id="architect",
                contract_id="c1",
                context={"notes": "market research complete"},
                handoff_reason="role transition",
            )
            loaded = mgr.load(record.id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.from_role_id, "researcher")
            self.assertEqual(loaded.to_role_id, "architect")
            self.assertEqual(loaded.context["notes"], "market research complete")

    def test_manager_lists_by_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HandoffManager(Path(tmpdir) / "handoffs")
            mgr.create(from_role_id="a", to_role_id="b", contract_id="c1")
            mgr.create(from_role_id="b", to_role_id="c", contract_id="c1")
            mgr.create(from_role_id="x", to_role_id="y", contract_id="c2")
            by_c1 = mgr.list_by_contract("c1")
            self.assertEqual(len(by_c1), 2)
            by_c2 = mgr.list_by_contract("c2")
            self.assertEqual(len(by_c2), 1)

    def test_manager_lists_by_role(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HandoffManager(Path(tmpdir) / "handoffs")
            mgr.create(from_role_id="researcher", to_role_id="pm", contract_id="c1")
            mgr.create(from_role_id="pm", to_role_id="architect", contract_id="c1")
            mgr.create(from_role_id="architect", to_role_id="engineer", contract_id="c1")
            by_researcher = mgr.list_by_role("researcher")
            self.assertEqual(len(by_researcher), 1)
            by_pm = mgr.list_by_role("pm")
            self.assertEqual(len(by_pm), 2)  # from + to

    def test_manager_supports_multi_role_handoff_chain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HandoffManager(Path(tmpdir) / "handoffs")
            # Full chain: researcher -> pm -> architect -> engineer
            chain = [
                ("market-researcher", "product-manager", "market analysis complete"),
                ("product-manager", "software-architect", "PRD finalized"),
                ("software-architect", "implementation-engineer", "technical design ready"),
            ]
            for from_role, to_role, reason in chain:
                mgr.create(from_role_id=from_role, to_role_id=to_role, contract_id="c1", handoff_reason=reason)
            all_records = mgr.list_all()
            self.assertEqual(len(all_records), 3)
            all_role_ids = {r.from_role_id for r in all_records} | {r.to_role_id for r in all_records}
            self.assertIn("market-researcher", all_role_ids)
            self.assertIn("implementation-engineer", all_role_ids)


if __name__ == "__main__":
    unittest.main()
