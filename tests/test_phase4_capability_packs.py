import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from argus.assets import CapabilityAsset, CapabilityInventory
from argus.capability_packs import (
    CapabilityPackCreator,
    CapabilityPackStore,
    CapabilityPackChecker,
    CapabilityPackAdvisor,
    CapabilityPackBindingStore,
    RolePackStore,
    infer_risk,
)
from argus.contracts import ContractSession, QuestionStrategy, WorkContractBuilder
from argus.storage import ContractStorage


class Phase4CapabilityPacksTest(unittest.TestCase):
    def test_risk_inference_uses_deterministic_policy_table(self):
        risk = infer_risk(["network_access", "reads_files"])

        self.assertEqual(risk.tier, "high")
        self.assertEqual(risk.policy_version, "risk-policy-v1")
        self.assertEqual(risk.reason_codes, ["network_access"])

    def test_pack_creation_persists_versioned_manifest_with_stable_hash_and_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            assets = [
                CapabilityAsset.create(
                    name="research",
                    type="skill",
                    source="local_skill",
                    install_path="/tmp/skills/research",
                    permissions=["read"],
                ),
                CapabilityAsset.create(
                    name="browser",
                    type="mcp_server",
                    source="codex_mcp",
                    install_path="/tmp/config.toml",
                    permissions=["network", "process"],
                ),
            ]
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            inventory.write(assets)

            pack_store = CapabilityPackStore(store / "capability-packs")
            result = CapabilityPackCreator(pack_store).create(
                pack_id="product-research",
                display_name="Product Research",
                required_asset_ids=[assets[0].id],
                optional_asset_ids=[assets[1].id],
                assets=inventory.list_assets(),
                created_by="test",
            )
            loaded, loaded_hash = pack_store.load("product-research", 1)

        self.assertEqual(result.content_hash, loaded_hash)
        self.assertEqual(loaded.pack_id, "product-research")
        self.assertEqual(loaded.version, 1)
        self.assertEqual(loaded.aggregate_risk_tier_snapshot, "high")
        self.assertEqual([entry.entry_id for entry in loaded.entries], [entry.entry_id for entry in result.manifest.entries])
        self.assertEqual(loaded.entries[0].entry_id, f"product-research-{assets[0].id}-implementation")
        self.assertTrue(loaded.entries[0].required)
        self.assertFalse(loaded.entries[1].required)

    def test_pack_check_reports_missing_required_assets_without_mutating_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            asset = CapabilityAsset.create(
                name="research",
                type="skill",
                source="local_skill",
                install_path="/tmp/skills/research",
            )
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            inventory.write([asset])
            pack_store = CapabilityPackStore(store / "capability-packs")
            create_result = CapabilityPackCreator(pack_store).create(
                pack_id="research-pack",
                display_name="Research Pack",
                required_asset_ids=[asset.id],
                optional_asset_ids=[],
                assets=inventory.list_assets(),
                created_by="test",
            )
            manifest_path = pack_store.manifest_path("research-pack", 1)
            before = manifest_path.read_text(encoding="utf-8")
            inventory.write([])

            report = CapabilityPackChecker().check(create_result.manifest, inventory.list_assets())
            after = manifest_path.read_text(encoding="utf-8")

        self.assertFalse(report.complete)
        self.assertEqual(report.missing_required_entry_ids, [create_result.manifest.entries[0].entry_id])
        self.assertEqual(before, after)

    def test_packs_cli_create_inspect_and_check(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            asset = CapabilityAsset.create(
                name="research",
                type="skill",
                source="local_skill",
                install_path="/tmp/skills/research",
                permissions=["read"],
            )
            CapabilityInventory(store / "assets" / "inventory.json").write([asset])

            create = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "packs",
                    "create",
                    "--store",
                    str(store),
                    "--pack-id",
                    "research-pack",
                    "--display-name",
                    "Research Pack",
                    "--required-asset",
                    asset.id,
                    "--created-by",
                    "cli-test",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            inspect = subprocess.run(
                [sys.executable, "-m", "argus.cli", "packs", "inspect", "research-pack", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )
            check = subprocess.run(
                [sys.executable, "-m", "argus.cli", "packs", "check", "research-pack", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(json.loads(create.stdout)["version"], 1)
        self.assertEqual(json.loads(inspect.stdout)["manifest"]["pack_id"], "research-pack")
        self.assertTrue(json.loads(check.stdout)["complete"])

    def test_work_contract_can_bind_concrete_pack_version_and_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            asset = CapabilityAsset.create(
                name="product-strategy",
                type="skill",
                source="local_skill",
                install_path="/tmp/skills/product-strategy",
            )
            CapabilityInventory(store / "assets" / "inventory.json").write([asset])
            pack_store = CapabilityPackStore(store / "capability-packs")
            pack = CapabilityPackCreator(pack_store).create(
                pack_id="product-strategy-pack",
                display_name="Product Strategy Pack",
                required_asset_ids=[asset.id],
                optional_asset_ids=[],
                assets=[asset],
                created_by="test",
            )
            session = ContractSession.start("Clarify a fuzzy product idea", QuestionStrategy.quick())
            session.answer(goal="Define the product direction.", outputs="PRD.", acceptance_criteria="Pack is bound.")
            contract = WorkContractBuilder().build(session)
            storage = ContractStorage(store)
            storage.save_contract(contract)

            binding = CapabilityPackBindingStore(storage).bind(
                contract_id=contract.id,
                pack=pack.manifest,
                content_hash=pack.content_hash,
                rationale="Product strategy needs the product-strategy capability.",
            )
            loaded = storage.load_contract(contract.id)

        self.assertEqual(binding.contract_version, 1)
        self.assertEqual(binding.pack_id, "product-strategy-pack")
        self.assertEqual(binding.pack_version, 1)
        self.assertEqual(binding.content_hash, pack.content_hash)
        self.assertEqual(loaded.capability_pack_ref, f"product-strategy-pack@1#{pack.content_hash}")
        self.assertEqual(loaded.execution_evidence[-1]["event_type"], "capability_pack_bound")

    def test_role_pack_references_capability_pack_and_reuses_pack_check(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            asset = CapabilityAsset.create(
                name="product-manager",
                type="skill",
                source="local_skill",
                install_path="/tmp/skills/product-manager",
            )
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            inventory.write([asset])
            pack_store = CapabilityPackStore(store / "capability-packs")
            pack = CapabilityPackCreator(pack_store).create(
                pack_id="product-manager-pack",
                display_name="Product Manager Pack",
                required_asset_ids=[asset.id],
                optional_asset_ids=[],
                assets=inventory.list_assets(),
                created_by="test",
            )

            role_store = RolePackStore(store / "role-packs", pack_store)
            role_pack = role_store.create(
                role_id="product-manager",
                display_name="Product Manager",
                required_pack_ids=[pack.manifest.pack_id],
                optional_pack_ids=[],
                created_by="test",
            )
            report = role_store.check("product-manager", inventory.list_assets())

        self.assertEqual(role_pack.role_id, "product-manager")
        self.assertEqual(role_pack.required_pack_refs[0].pack_id, "product-manager-pack")
        self.assertEqual(role_pack.required_pack_refs[0].content_hash, pack.content_hash)
        self.assertTrue(report.complete)
        self.assertEqual(report.required_pack_ids, ["product-manager-pack"])

    def test_pack_advisor_reports_missing_capabilities_and_duplicates(self):
        assets = [
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
            ),
        ]

        report = CapabilityPackAdvisor().advise(
            required_capabilities=["research", "roadmap"],
            assets=assets,
        )

        self.assertEqual(report.missing_capabilities, ["roadmap"])
        self.assertEqual(len(report.duplicate_asset_groups), 1)
        self.assertIn("research", report.to_markdown())

    def test_cli_binds_contract_and_creates_role_pack(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            asset = CapabilityAsset.create(
                name="product-manager",
                type="skill",
                source="local_skill",
                install_path="/tmp/skills/product-manager",
            )
            CapabilityInventory(store / "assets" / "inventory.json").write([asset])
            draft = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "contract",
                    "draft",
                    "--store",
                    str(store),
                    "--intent",
                    "Shape a fuzzy product idea",
                    "--goal",
                    "Define direction.",
                    "--outputs",
                    "PRD.",
                    "--acceptance-criteria",
                    "Pack is bound.",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            contract_id = json.loads(draft.stdout)["id"]
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "packs",
                    "create",
                    "--store",
                    str(store),
                    "--pack-id",
                    "product-manager-pack",
                    "--display-name",
                    "Product Manager Pack",
                    "--required-asset",
                    asset.id,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            bind = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "contract",
                    "bind-pack",
                    contract_id,
                    "product-manager-pack",
                    "--store",
                    str(store),
                    "--rationale",
                    "The contract needs product management capability.",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            role = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "roles",
                    "create-pack",
                    "--store",
                    str(store),
                    "--role-id",
                    "product-manager",
                    "--display-name",
                    "Product Manager",
                    "--required-pack",
                    "product-manager-pack",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(json.loads(bind.stdout)["pack_id"], "product-manager-pack")
        self.assertEqual(json.loads(role.stdout)["role_id"], "product-manager")


if __name__ == "__main__":
    unittest.main()
