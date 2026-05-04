import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from argus.application.modification import ModificationApplication
from argus.assets import CapabilityAsset, CapabilityInventory
from argus.controlled_modification import (
    AssetDiffer,
    AssetDiff,
    AuditLedger,
    ModificationAuditRecord,
    ModificationReporter,
    ModificationResult,
    ModificationSnapshot,
    RollbackManager,
    SnapshotManager,
)
from argus.contracts import WorkContractBuilder, ContractSession, QuestionStrategy
from argus.storage import ContractStorage


class Phase7ControlledModificationTest(unittest.TestCase):
    def test_snapshot_creates_deterministic_id(self):
        content = {"name": "test", "status": "active"}
        s1 = ModificationSnapshot.capture(
            subject_type="capability_asset",
            subject_id="asset-1",
            content=content,
            triggered_by="test",
            trigger_reason="testing",
        )
        s2 = ModificationSnapshot.capture(
            subject_type="capability_asset",
            subject_id="asset-1",
            content=content,
            triggered_by="test",
            trigger_reason="testing",
        )
        self.assertEqual(s1.id, s2.id)
        self.assertEqual(s1.subject_type, "capability_asset")
        self.assertEqual(s1.subject_id, "asset-1")

    def test_snapshot_manager_captures_and_loads_asset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SnapshotManager(Path(tmpdir) / "snapshots")
            asset = CapabilityAsset.create(name="test", type="skill", source="local", install_path="/tmp/test")
            snap = mgr.capture(
                subject_type="capability_asset",
                subject_id=asset.id,
                content=asset.to_dict(),
                triggered_by="test",
                trigger_reason="testing",
            )
            loaded = mgr.load(snap.id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.subject_id, asset.id)
            loaded_content = json.loads(loaded.content_json)
            self.assertEqual(loaded_content["name"], "test")

    def test_snapshot_manager_captures_and_loads_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SnapshotManager(Path(tmpdir) / "snapshots")
            session = ContractSession(intent="test intent", strategy=QuestionStrategy.standard())
            builder = WorkContractBuilder()
            contract = builder.build(session)
            snap = mgr.capture(
                subject_type="work_contract",
                subject_id=contract.id,
                content=contract.to_dict(),
                triggered_by="test",
                trigger_reason="testing",
            )
            loaded = mgr.load(snap.id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.subject_id, contract.id)

    def test_asset_diff_detects_status_change(self):
        a1 = CapabilityAsset.create(name="test", type="skill", source="local", install_path="/tmp/test")
        a2_data = a1.to_dict()
        a2_data["status"] = "deprecated"
        a2 = CapabilityAsset.from_dict(a2_data)

        differ = AssetDiffer()
        diff = differ.diff_capability_asset(a1, a2)
        self.assertIn("status", diff.changed_fields)
        self.assertGreater(len(diff.unified_diff_lines), 0)

    def test_asset_diff_detects_no_change(self):
        a1 = CapabilityAsset.create(name="test", type="skill", source="local", install_path="/tmp/test")
        a2 = CapabilityAsset.from_dict(a1.to_dict())

        differ = AssetDiffer()
        diff = differ.diff_capability_asset(a1, a2)
        self.assertEqual(diff.changed_fields, [])
        self.assertEqual(diff.added_lines, 0)
        self.assertEqual(diff.removed_lines, 0)

    def test_contract_diff_detects_field_update(self):
        session = ContractSession(intent="build a feature", strategy=QuestionStrategy.standard())
        builder = WorkContractBuilder()
        c1 = builder.build(session)

        c2_data = c1.to_dict()
        c2_data["goal"] = "updated goal description"
        c2 = type(c1).from_dict(c2_data)

        differ = AssetDiffer()
        diff = differ.diff_work_contract(c1, c2)
        self.assertIn("goal", diff.changed_fields)

    def test_audit_ledger_append_and_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = AuditLedger(Path(tmpdir) / "audit.jsonl")
            r1 = ModificationAuditRecord.create(
                triggered_by="test",
                trigger_reason="testing",
                subject_type="capability_asset",
                subject_id="asset-1",
                action="modify",
                snapshot_id="snap-1",
            )
            r2 = ModificationAuditRecord.create(
                triggered_by="test",
                trigger_reason="testing again",
                subject_type="capability_asset",
                subject_id="asset-2",
                action="modify",
                snapshot_id="snap-2",
            )
            ledger.append(r1)
            ledger.append(r2)
            records = ledger.list_records()
            self.assertEqual(len(records), 2)

    def test_audit_ledger_deduplicates_by_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = AuditLedger(Path(tmpdir) / "audit.jsonl")
            r1 = ModificationAuditRecord.create(
                triggered_by="test",
                trigger_reason="testing",
                subject_type="capability_asset",
                subject_id="asset-1",
                action="modify",
                snapshot_id="snap-1",
            )
            self.assertTrue(ledger.append(r1))
            self.assertFalse(ledger.append(r1))
            self.assertEqual(len(ledger.list_records()), 1)

    def test_apply_asset_modification_produces_snapshot_diff_and_audit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            asset = CapabilityAsset.create(name="test", type="skill", source="local", install_path="/tmp/test")
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            inventory.write([asset])

            app = _make_application(store)
            before = inventory.list_assets()
            self.assertEqual(before[0].status, "active")

            result = app.apply_asset_modification(
                asset_id=asset.id,
                triggered_by="governance_dedupe",
                trigger_reason="Duplicate capability asset found.",
                new_status="deprecated",
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.outcome, "applied")
            self.assertNotEqual(result.snapshot_id, "")
            self.assertNotEqual(result.diff_id, "")
            self.assertNotEqual(result.audit_record_id, "")

            # Inventory updated
            after = inventory.list_assets()
            self.assertEqual(after[0].status, "deprecated")

            # Snapshot file exists
            self.assertTrue((store / "modifications" / "snapshots" / f"{result.snapshot_id}.json").exists())

            # Audit record exists
            audit_records = app.list_audit_log()
            self.assertEqual(len(audit_records), 1)
            self.assertEqual(audit_records[0].id, result.audit_record_id)
            self.assertEqual(audit_records[0].action, "modify")

    def test_preview_asset_modification_does_not_modify_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            asset = CapabilityAsset.create(name="test", type="skill", source="local", install_path="/tmp/test")
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            inventory.write([asset])

            app = _make_application(store)
            diff = app.preview_asset_modification(
                asset_id=asset.id,
                triggered_by="governance_dedupe",
                trigger_reason="testing",
                new_status="deprecated",
            )

            self.assertIsNotNone(diff)
            self.assertIn("status", diff.changed_fields)

            # Inventory unchanged on disk
            current = inventory.list_assets()
            self.assertEqual(current[0].status, "active")

    def test_apply_contract_modification_produces_snapshot_diff_and_audit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            storage = ContractStorage(store)

            session = ContractSession(intent="build a feature", strategy=QuestionStrategy.standard())
            builder = WorkContractBuilder()
            contract = builder.build(session)
            storage.save_contract(contract)

            app = _make_application(store)
            mod_result = app.apply_contract_modification(
                contract_id=contract.id,
                triggered_by="governance_work_contract",
                trigger_reason="Contract goal needs clarification.",
                field_updates={"goal": "clarified goal text"},
            )

            self.assertIsNotNone(mod_result)
            self.assertEqual(mod_result.outcome, "applied")

            # Contract version incremented
            updated = storage.load_contract(contract.id)
            self.assertEqual(updated.version, contract.version + 1)
            self.assertEqual(updated.goal, "clarified goal text")
            self.assertTrue(len(updated.change_history) > 0)

            # Audit record
            records = app.list_audit_log()
            self.assertEqual(len(records), 1)

    def test_rollback_restores_previous_asset_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            asset = CapabilityAsset.create(name="test", type="skill", source="local", install_path="/tmp/test")
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            inventory.write([asset])

            app = _make_application(store)
            result = app.apply_asset_modification(
                asset_id=asset.id,
                triggered_by="test",
                trigger_reason="change status",
                new_status="deprecated",
            )
            after_apply = inventory.list_assets()
            self.assertEqual(after_apply[0].status, "deprecated")

            rollback_result = app.rollback(result.audit_record_id, "wrong status")

            self.assertEqual(rollback_result.outcome, "applied")

            after_rollback = inventory.list_assets()
            self.assertEqual(after_rollback[0].status, "active")

            # Two audit records: modify + rollback
            records = app.list_audit_log()
            self.assertEqual(len(records), 2)
            rollback_record = [r for r in records if r.action == "rollback"][0]
            self.assertIn("Reverted to snapshot", rollback_record.rollback_instructions)

    def test_rollback_fails_for_nonexistent_audit_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            app = _make_application(store)
            result = app.rollback("nonexistent-id", "test")
            self.assertEqual(result.outcome, "failed")
            self.assertTrue(len(result.warnings) > 0)

    def test_modification_reporter_writes_markdown_and_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir) / "reports"
            reporter = ModificationReporter(reports_dir)

            records = [
                ModificationAuditRecord.create(
                    triggered_by="test", trigger_reason="test",
                    subject_type="capability_asset", subject_id="asset-1",
                    action="modify", snapshot_id="snap-1",
                )
            ]
            snap = ModificationSnapshot.capture(
                subject_type="capability_asset", subject_id="asset-1",
                content={"name": "test"}, triggered_by="test", trigger_reason="test",
            )
            diff = AssetDiff.create(
                subject_type="capability_asset", subject_id="asset-1",
                version_before="1", version_after="2",
                unified_diff_lines=["-old", "+new"],
                added_lines=1, removed_lines=1, changed_fields=["status"],
            )

            report = reporter.write(audit_records=records, snapshots=[snap], diffs=[diff])

            self.assertTrue(report.markdown_path.exists())
            self.assertTrue(report.json_path.exists())
            markdown = report.markdown_path.read_text(encoding="utf-8")
            self.assertIn("Controlled Modification Report", markdown)
            self.assertIn("modify", markdown)

            json_data = json.loads(report.json_path.read_text(encoding="utf-8"))
            self.assertEqual(json_data["summary"]["total_audit_records"], 1)
            self.assertEqual(json_data["summary"]["total_diffs"], 1)

    def test_cli_modify_apply_and_rollback_commands(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            asset = CapabilityAsset.create(name="test-cli", type="skill", source="local", install_path="/tmp/test-cli")
            CapabilityInventory(store / "assets" / "inventory.json").write([asset])

            apply_out = subprocess.run(
                [
                    sys.executable, "-m", "argus.cli", "modify", "apply",
                    "--store", str(store),
                    "--asset-id", asset.id,
                    "--triggered-by", "test",
                    "--trigger-reason", "cli-test",
                    "--new-status", "archived",
                ],
                check=True, capture_output=True, text=True,
            )
            result = json.loads(apply_out.stdout)
            self.assertEqual(result["outcome"], "applied")
            self.assertIn("audit_record_id", result)

            rollback_out = subprocess.run(
                [
                    sys.executable, "-m", "argus.cli", "modify", "rollback",
                    "--store", str(store),
                    "--audit-id", result["audit_record_id"],
                    "--reason", "cli-rollback-test",
                ],
                check=True, capture_output=True, text=True,
            )
            rollback_result = json.loads(rollback_out.stdout)
            self.assertEqual(rollback_result["outcome"], "applied")


def _make_application(store_path: Path) -> ModificationApplication:
    from argus.controlled_modification import (
        AssetDiffer,
        AuditLedger,
        RollbackManager,
        SnapshotManager,
    )
    inventory = CapabilityInventory(store_path / "assets" / "inventory.json")
    contract_storage = ContractStorage(store_path)
    snapshot_mgr = SnapshotManager(store_path / "modifications" / "snapshots")
    differ = AssetDiffer()
    audit_ledger = AuditLedger(store_path / "modifications" / "audit.jsonl")
    rollback_mgr = RollbackManager(snapshot_mgr, inventory, contract_storage, audit_ledger)
    return ModificationApplication(
        inventory, contract_storage, snapshot_mgr, differ,
        rollback_mgr, audit_ledger, store_path / "modifications" / "reports",
    )


if __name__ == "__main__":
    unittest.main()
