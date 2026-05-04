import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from argus.assets import DEPRECATED, CapabilityAsset, CapabilityInventory
from argus.capability_packs import CapabilityPackCreator, CapabilityPackStore, RolePackStore
from argus.contracts import ContractSession, DeliverableContract, DeliverableEvaluator, QuestionStrategy, WorkContractBuilder
from argus.governance import GovernanceReporter
from argus.ledger import CandidateLearningItem, LearningLedger
from argus.storage import ContractStorage


class Phase5GovernanceTest(unittest.TestCase):
    def test_governance_report_contains_required_phase5_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            contract_storage = _write_incomplete_contract_with_failed_evaluation(store)
            learning_ledger = _write_duplicate_candidate_learnings(store)
            inventory = _write_governance_assets(store)
            pack_store = CapabilityPackStore(store / "capability-packs")
            RolePackStore(store / "role-packs", pack_store).create(
                role_id="product-manager",
                display_name="Product Manager",
                required_pack_ids=[
                    CapabilityPackCreator(pack_store).create(
                        pack_id="product-manager-pack",
                        display_name="Product Manager Pack",
                        required_asset_ids=[inventory.list_assets()[0].id],
                        optional_asset_ids=[],
                        assets=inventory.list_assets(),
                        created_by="test",
                    ).manifest.pack_id
                ],
                optional_pack_ids=[],
                created_by="test",
            )

            result = GovernanceReporter(store / "governance" / "reports").write(
                contract_storage=contract_storage,
                learning_ledger=learning_ledger,
                inventory=inventory,
                pack_store=pack_store,
                role_store=RolePackStore(store / "role-packs", pack_store),
            )
            report = json.loads(result.json_path.read_text(encoding="utf-8"))
            markdown_exists = result.markdown_path.exists()

        categories = {finding["category"] for finding in report["findings"]}
        recommendation_types = {item["type"] for item in report["pending_actions"]}
        self.assertIn("dedupe", categories)
        self.assertIn("stale", categories)
        self.assertIn("risk", categories)
        self.assertIn("work_contract", categories)
        self.assertIn("role", categories)
        self.assertIn("question_strategy_improvement", recommendation_types)
        self.assertIn("deliverable_contract_improvement", recommendation_types)
        self.assertTrue(report["low_risk_maintenance_log"])
        self.assertTrue(markdown_exists)

    def test_governance_report_is_read_only_for_assets_and_roles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            contract_storage = _write_incomplete_contract_with_failed_evaluation(store)
            learning_ledger = _write_duplicate_candidate_learnings(store)
            inventory = _write_governance_assets(store)
            pack_store = CapabilityPackStore(store / "capability-packs")
            role_store = RolePackStore(store / "role-packs", pack_store)
            before_inventory = (store / "assets" / "inventory.json").read_text(encoding="utf-8")

            GovernanceReporter(store / "governance" / "reports").write(
                contract_storage=contract_storage,
                learning_ledger=learning_ledger,
                inventory=inventory,
                pack_store=pack_store,
                role_store=role_store,
            )
            after_inventory = (store / "assets" / "inventory.json").read_text(encoding="utf-8")

        self.assertEqual(before_inventory, after_inventory)

    def test_governance_cli_writes_report_log_and_pending_actions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            _write_incomplete_contract_with_failed_evaluation(store)
            _write_duplicate_candidate_learnings(store)
            _write_governance_assets(store)

            result = subprocess.run(
                [sys.executable, "-m", "argus.cli", "governance", "report", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)

        self.assertIn("governance-report.md", payload["markdown_path"])
        self.assertIn("governance-report.json", payload["json_path"])
        self.assertIn("low-risk-maintenance-log.json", payload["low_risk_log_path"])
        self.assertIn("pending-actions.json", payload["pending_actions_path"])


def _write_incomplete_contract_with_failed_evaluation(store: Path) -> ContractStorage:
    storage = ContractStorage(store)
    session = ContractSession.start("Create a launch plan", QuestionStrategy.standard())
    session.answer(goal="Launch plan.", outputs="Plan.")
    contract = WorkContractBuilder().build(session)
    storage.save_contract(contract)
    evaluation = DeliverableEvaluator().evaluate(
        contract,
        DeliverableContract.prd(),
        "# PRD\n\n## Goals\nLaunch.",
    )
    storage.save_evaluation(contract.id, evaluation)
    return storage


def _write_duplicate_candidate_learnings(store: Path) -> LearningLedger:
    ledger = LearningLedger(store / "ledger" / "candidate_learnings.jsonl")
    item = CandidateLearningItem.create(
        summary="Ask for acceptance criteria before execution.",
        type="correction",
        evidence_refs=["event-1"],
        reverse_learning_target="question_strategy",
    )
    ledger.append(item)
    ledger.append(item)
    return ledger


def _write_governance_assets(store: Path) -> CapabilityInventory:
    inventory = CapabilityInventory(store / "assets" / "inventory.json")
    inventory.write(
        [
            CapabilityAsset.create(
                name="research",
                type="skill",
                source="local_skill",
                install_path="/tmp/skills/research",
            ),
            CapabilityAsset.create(
                name="research plugin",
                type="plugin",
                source="codex_plugin",
                install_path="/tmp/plugins/research",
                permissions=["network"],
                risk_score=0.75,
            ),
            CapabilityAsset.create(
                name="old-skill",
                type="skill",
                source="local_skill",
                install_path="/tmp/skills/old",
                status=DEPRECATED,
            ),
        ]
    )
    return inventory


if __name__ == "__main__":
    unittest.main()
