import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from argus.lifecycle import (
    AssetState,
    LifecycleAction,
    LifecycleLedger,
    LifecycleRecord,
    StateMachine,
    state_machine_for,
)
from argus.registry import RegistryEntry, RegistryIndex
from argus.feedback import FeedbackLoop


class Phase12LifecycleTest(unittest.TestCase):
    def test_state_machine_default_transitions(self):
        sm = StateMachine(AssetState.DRAFT)
        self.assertTrue(sm.can(LifecycleAction.ACTIVATE))
        self.assertTrue(sm.can(LifecycleAction.ARCHIVE))
        self.assertFalse(sm.can(LifecycleAction.DISABLE))

    def test_state_machine_apply(self):
        sm = StateMachine(AssetState.DRAFT)
        new_state = sm.apply(LifecycleAction.ACTIVATE)
        self.assertEqual(new_state, AssetState.ACTIVE)
        self.assertTrue(sm.can(LifecycleAction.DISABLE))

    def test_state_machine_invalid_transition(self):
        sm = StateMachine(AssetState.ACTIVE)
        with self.assertRaises(ValueError):
            sm.apply(LifecycleAction.CREATE)

    def test_state_machine_available_actions(self):
        sm = StateMachine(AssetState.ACTIVE)
        actions = sm.available_actions()
        self.assertIn(LifecycleAction.DISABLE, actions)
        self.assertIn(LifecycleAction.ISOLATE, actions)
        self.assertIn(LifecycleAction.DEPRECATE, actions)

    def test_state_machine_isolated_release(self):
        sm = StateMachine(AssetState.ISOLATED)
        self.assertTrue(sm.can(LifecycleAction.RELEASE))
        new_state = sm.apply(LifecycleAction.RELEASE)
        self.assertEqual(new_state, AssetState.ACTIVE)

    def test_deleted_no_transitions(self):
        sm = StateMachine(AssetState.DELETED)
        self.assertEqual(len(sm.available_actions()), 0)

    def test_state_machine_for_string(self):
        sm = state_machine_for("active")
        self.assertEqual(sm.current, AssetState.ACTIVE)
        sm2 = state_machine_for("unknown")
        self.assertEqual(sm2.current, AssetState.DRAFT)

    def test_lifecycle_record_create(self):
        record = LifecycleRecord.create(
            asset_id="a1",
            asset_type="skill",
            action=LifecycleAction.ACTIVATE,
            from_state=AssetState.DRAFT,
            to_state=AssetState.ACTIVE,
            triggered_by="test",
            reason="testing",
        )
        self.assertTrue(record.record_id)
        self.assertEqual(record.asset_id, "a1")
        data = record.to_dict()
        self.assertEqual(data["action"], "activate")

    def test_lifecycle_ledger_append_and_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ledger.jsonl"
            ledger = LifecycleLedger(path)
            r1 = LifecycleRecord.create("a1", "skill", LifecycleAction.ACTIVATE,
                                        AssetState.DRAFT, AssetState.ACTIVE, "test")
            r2 = LifecycleRecord.create("a1", "skill", LifecycleAction.DISABLE,
                                        AssetState.ACTIVE, AssetState.DISABLED, "test")
            ledger.append(r1)
            ledger.append(r2)
            all_records = ledger.list_all()
            self.assertEqual(len(all_records), 2)
            a1_records = ledger.for_asset("a1")
            self.assertEqual(len(a1_records), 2)
            no_records = ledger.for_asset("nonexistent")
            self.assertEqual(len(no_records), 0)


class Phase12RegistryTest(unittest.TestCase):
    def test_registry_entry(self):
        entry = RegistryEntry(
            entry_id="e1", name="Test Skill", entry_type="skill",
            source="github.com/trusted", quality_score=0.9,
            tags=["python", "testing"],
        )
        data = entry.to_dict()
        restored = RegistryEntry.from_dict(data)
        self.assertEqual(restored.name, "Test Skill")

    def test_registry_index_add_and_search(self):
        idx = RegistryIndex()
        idx.add(RegistryEntry("e1", "Python Tester", "skill", "local", quality_score=0.9, tags=["python"]))
        idx.add(RegistryEntry("e2", "JS Linter", "plugin", "local", quality_score=0.7, tags=["js"]))
        idx.add(RegistryEntry("e3", "Bad Skill", "skill", "evil.com", risk_score=0.9, quality_score=0.2))
        results = idx.search(name="python")
        self.assertEqual(len(results), 1)
        results = idx.search(entry_type="skill")
        self.assertEqual(len(results), 2)
        results = idx.search(max_risk=0.5)
        self.assertEqual(len(results), 2)

    def test_registry_index_remove(self):
        idx = RegistryIndex()
        idx.add(RegistryEntry("e1", "Test", "skill", "local"))
        self.assertTrue(idx.remove("e1", "local"))
        self.assertEqual(len(idx.entries), 0)
        self.assertFalse(idx.remove("e1"))

    def test_registry_index_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "index.json"
            idx = RegistryIndex()
            idx.add(RegistryEntry("e1", "Test", "skill", "local"))
            idx.save(path)
            loaded = RegistryIndex.load(path)
            self.assertEqual(len(loaded.entries), 1)


class Phase12FeedbackTest(unittest.TestCase):
    def test_feedback_record_signal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = FeedbackLoop(Path(tmpdir))
            signal = loop.record(
                source_type="contract", source_id="c1",
                signal_type="success", target_type="role",
                target_id="r1", strength=0.8,
            )
            self.assertTrue(signal.signal_id)

    def test_feedback_list_and_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = FeedbackLoop(Path(tmpdir))
            loop.record("contract", "c1", "success", "role", "r1", 0.8)
            loop.record("contract", "c2", "failure", "role", "r1", -0.5)
            loop.record("learning", "l1", "success", "capability", "a1", 0.6)
            r1_signals = loop.list_signals(target_type="role", target_id="r1")
            self.assertEqual(len(r1_signals), 2)
            success_signals = loop.list_signals(signal_type="success")
            self.assertEqual(len(success_signals), 2)

    def test_feedback_aggregate_strength(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = FeedbackLoop(Path(tmpdir))
            loop.record("contract", "c1", "success", "role", "r1", 0.8)
            loop.record("contract", "c2", "success", "role", "r1", 0.6)
            avg = loop.aggregate_strength("role", "r1", "success")
            self.assertAlmostEqual(avg, 0.7)

    def test_feedback_recommendation_promote(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = FeedbackLoop(Path(tmpdir))
            loop.record("c1", "c1", "success", "role", "r1", 0.8)
            loop.record("c2", "c2", "success", "role", "r1", 0.7)
            loop.record("c3", "c3", "success", "role", "r1", 0.9)
            rec = loop.compute_recommendation("role", "r1")
            self.assertEqual(rec["recommendation"], "promote")

    def test_feedback_recommendation_observe_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = FeedbackLoop(Path(tmpdir))
            rec = loop.compute_recommendation("role", "r_new")
            self.assertEqual(rec["recommendation"], "observe")
            self.assertEqual(rec["total_signals"], 0)


class Phase12CLITest(unittest.TestCase):
    def test_lifecycle_show_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "lifecycle", "show",
                 "--store", str(store), "--asset-id", "a1", "--current-state", "draft"],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertIn("available_actions", data)

    def test_lifecycle_apply_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "lifecycle", "apply",
                 "--store", str(store), "--asset-id", "a1", "--asset-type", "skill",
                 "--action", "activate", "--from-state", "draft", "--reason", "test"],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertEqual(data["action"], "activate")
            self.assertEqual(data["to_state"], "active")

    def test_lifecycle_history_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            subprocess.run(
                [sys.executable, "-m", "argus.cli", "lifecycle", "apply",
                 "--store", str(store), "--asset-id", "a1", "--asset-type", "skill",
                 "--action", "activate", "--from-state", "draft"],
                check=True, capture_output=True, text=True,
            )
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "lifecycle", "history",
                 "--store", str(store), "--asset-id", "a1"],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertEqual(len(data), 1)

    def test_registry_add_and_search_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            subprocess.run(
                [sys.executable, "-m", "argus.cli", "registry", "add",
                 "--store", str(store), "--entry-id", "e1", "--name", "Test",
                 "--type", "skill", "--source", "local", "--quality-score", "0.9"],
                check=True, capture_output=True, text=True,
            )
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "registry", "search",
                 "--store", str(store), "--name", "Test"],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertGreaterEqual(len(data), 1)

    def test_registry_list_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            subprocess.run(
                [sys.executable, "-m", "argus.cli", "registry", "add",
                 "--store", str(store), "--entry-id", "e1", "--name", "E1",
                 "--type", "skill", "--source", "local"],
                check=True, capture_output=True, text=True,
            )
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "registry", "list", "--store", str(store)],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertEqual(len(data), 1)

    def test_feedback_record_and_list_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            subprocess.run(
                [sys.executable, "-m", "argus.cli", "feedback", "record",
                 "--store", str(store), "--source-type", "contract",
                 "--source-id", "c1", "--signal-type", "success",
                 "--target-type", "role", "--target-id", "r1", "--strength", "0.8"],
                check=True, capture_output=True, text=True,
            )
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "feedback", "list", "--store", str(store)],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertGreaterEqual(len(data), 1)

    def test_feedback_recommend_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            out = subprocess.run(
                [sys.executable, "-m", "argus.cli", "feedback", "recommend",
                 "--store", str(store), "--target-type", "role", "--target-id", "r1"],
                check=True, capture_output=True, text=True,
            )
            data = json.loads(out.stdout)
            self.assertIn("recommendation", data)


if __name__ == "__main__":
    unittest.main()
