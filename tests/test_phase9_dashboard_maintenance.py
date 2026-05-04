import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from argus.analytics import DashboardReporter, ROICalculator
from argus.assets import CapabilityAsset, CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.capability_packs.creation import CapabilityPackCreator
from argus.contracts import ContractSession, QuestionStrategy, WorkContractBuilder
from argus.handoff import HandoffManager
from argus.ledger import EventLedger, LearningLedger
from argus.maintenance import MaintenanceEngine, MaintenanceReporter
from argus.storage import ContractStorage


class Phase9DashboardTest(unittest.TestCase):
    def _make_calculator(self, tmpdir: str):
        store = Path(tmpdir) / ".argus"
        storage = ContractStorage(store)
        event_ledger = EventLedger(store / "ledger" / "events.jsonl")
        learning_ledger = LearningLedger(store / "ledger" / "candidate_learnings.jsonl")
        inventory = CapabilityInventory(store / "assets" / "inventory.json")
        pack_store = CapabilityPackStore(store / "capability-packs")
        role_store = RolePackStore(store / "role-packs", pack_store)
        handoff_mgr = HandoffManager(store / "handoffs")
        return ROICalculator(storage, event_ledger, learning_ledger, inventory, pack_store, role_store, handoff_mgr), store

    def test_contract_roi_empty_system(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            calc, store = self._make_calculator(tmpdir)
            roi = calc.contract_roi()
            self.assertEqual(roi.total_contracts, 0)
            self.assertEqual(roi.avg_completeness, 0.0)

    def test_contract_roi_with_contracts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            calc, store = self._make_calculator(tmpdir)
            storage = ContractStorage(store)
            session = ContractSession(intent="test", strategy=QuestionStrategy.standard())
            contract = WorkContractBuilder().build(session)
            storage.save_contract(contract)
            roi = calc.contract_roi()
            self.assertEqual(roi.total_contracts, 1)
            self.assertIn("clarifying", roi.by_status)

    def test_learning_roi_empty_system(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            calc, store = self._make_calculator(tmpdir)
            roi = calc.learning_roi()
            self.assertEqual(roi.total_learnings, 0)

    def test_role_roi_with_handoffs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            calc, store = self._make_calculator(tmpdir)
            handoff_mgr = HandoffManager(store / "handoffs")
            handoff_mgr.create(from_role_id="a", to_role_id="b", contract_id="c1")
            handoff_mgr.create(from_role_id="b", to_role_id="c", contract_id="c1")
            roi = calc.role_roi()
            self.assertEqual(roi.total_handoffs, 2)

    def test_dashboard_reporter_writes_markdown_and_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            calc, store = self._make_calculator(tmpdir)
            reporter = DashboardReporter(Path(tmpdir) / "reports")
            report = reporter.write(calc)
            self.assertTrue(report.markdown_path.exists())
            self.assertTrue(report.json_path.exists())
            md = report.markdown_path.read_text(encoding="utf-8")
            self.assertIn("Argus Dashboard", md)
            json_data = json.loads(report.json_path.read_text(encoding="utf-8"))
            self.assertIn("contract_roi", json_data)


class Phase9MaintenanceTest(unittest.TestCase):
    def _make_engine(self, tmpdir: str):
        store = Path(tmpdir) / ".argus"
        storage = ContractStorage(store)
        inventory = CapabilityInventory(store / "assets" / "inventory.json")
        pack_store = CapabilityPackStore(store / "capability-packs")
        role_store = RolePackStore(store / "role-packs", pack_store)
        return MaintenanceEngine(inventory, pack_store, role_store, storage), store

    def test_maintenance_empty_system(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            engine, store = self._make_engine(tmpdir)
            report = engine.run()
            self.assertEqual(report.summary["total_assets"], 0)
            self.assertEqual(report.summary["duplicates"], 0)

    def test_maintenance_detects_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            engine, store = self._make_engine(tmpdir)
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            a1 = CapabilityAsset.create(name="my-skill", type="skill", source="local", install_path="/tmp/a")
            a2 = CapabilityAsset.create(name="my-skill", type="skill", source="local", install_path="/tmp/b")
            inventory.write([a1, a2])
            report = engine.run()
            self.assertGreaterEqual(report.summary["duplicates"], 1)

    def test_maintenance_detects_deprecated_assets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            engine, store = self._make_engine(tmpdir)
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            a1 = CapabilityAsset.create(name="old-skill", type="skill", source="local", install_path="/tmp/old1")
            a2 = CapabilityAsset.create(name="old-tool", type="plugin", source="local", install_path="/tmp/old2")
            a1_data = a1.to_dict()
            a1_data["status"] = "deprecated"
            a1d = CapabilityAsset.from_dict(a1_data)
            a2_data = a2.to_dict()
            a2_data["status"] = "deprecated"
            a2d = CapabilityAsset.from_dict(a2_data)
            inventory.write([a1d, a2d])
            report = engine.run()
            self.assertEqual(report.summary["deprecated"], 2)

    def test_maintenance_reporter_writes_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            engine, store = self._make_engine(tmpdir)
            reporter = MaintenanceReporter(Path(tmpdir) / "maintenance")
            paths = reporter.write(engine)
            self.assertTrue(paths.markdown_path.exists())
            self.assertTrue(paths.json_path.exists())
            md = paths.markdown_path.read_text(encoding="utf-8")
            self.assertIn("Maintenance Report", md)


class Phase9CLITest(unittest.TestCase):
    def test_dashboard_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "dashboard", "--store", str(store)],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertIn("markdown_path", data)
            self.assertIn("contract_roi", data)

    def test_maintenance_run_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "maintenance", "run", "--store", str(store)],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertIn("summary", data)
            self.assertEqual(data["summary"]["total_assets"], 0)

    def test_maintenance_report_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "maintenance", "report", "--store", str(store)],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertIn("markdown_path", data)


if __name__ == "__main__":
    unittest.main()
