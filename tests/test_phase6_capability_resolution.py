import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from argus.assets import CapabilityAsset, CapabilityInventory, analyze_assets
from argus.capability_packs import (
    CapabilityPackCreator,
    CapabilityPackStore,
    CapabilityPackChecker,
    CapabilityPackAdvisor,
)
from argus.capability_resolution import (
    CapabilityResolution,
    CapabilityResolver,
    Decision,
    ResolutionReporter,
    DECISION_RISK,
)
from argus.contracts import ContractSession, QuestionStrategy, WorkContractBuilder
from argus.governance import GovernanceFinding
from argus.ledger import CandidateLearningItem, LearningLedger
from argus.storage import ContractStorage


class Phase6CapabilityResolutionTest(unittest.TestCase):
    def test_decision_enum_and_risk_mapping(self):
        self.assertEqual(Decision.REUSE, "reuse")
        self.assertEqual(Decision.INSTALL_SUGGESTED, "install_suggested")
        self.assertEqual(DECISION_RISK[Decision.REUSE], "low")
        self.assertEqual(DECISION_RISK[Decision.CREATE_LOCAL], "medium")
        self.assertEqual(DECISION_RISK[Decision.INSTALL_SUGGESTED], "high")

    def test_gap_with_exact_local_match_yields_reuse_decision(self):
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

            resolver = CapabilityResolver(inventory)
            resolutions = resolver.resolve(
                gaps=[
                    {
                        "gap_id": "gap-1",
                        "gap_description": "Need a research capability to explore topics.",
                        "source": "test",
                    }
                ]
            )

        self.assertEqual(len(resolutions), 1)
        self.assertEqual(resolutions[0].decision, Decision.REUSE)
        self.assertEqual(resolutions[0].risk_level, "low")
        self.assertEqual(resolutions[0].matched_local_asset_ids, [asset.id])
        self.assertGreaterEqual(resolutions[0].confidence, 0.8)

    def test_gap_with_partial_match_yields_configure_decision(self):
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

            resolver = CapabilityResolver(inventory)
            resolutions = resolver.resolve(
                gaps=[
                    {
                        "gap_id": "gap-1",
                        "gap_description": "Need product skills for workflow planning.",
                        "source": "test",
                    }
                ]
            )

        self.assertEqual(len(resolutions), 1)
        self.assertEqual(resolutions[0].decision, Decision.CONFIGURE)
        self.assertEqual(resolutions[0].risk_level, "low")
        self.assertIn(asset.id, resolutions[0].matched_local_asset_ids)

    def test_gap_with_no_local_match_yields_install_suggested(self):
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

            resolver = CapabilityResolver(inventory)
            resolutions = resolver.resolve(
                gaps=[
                    {
                        "gap_id": "gap-1",
                        "gap_description": "Need browser automation for web scraping.",
                        "source": "test",
                    }
                ]
            )

        self.assertEqual(len(resolutions), 1)
        self.assertEqual(resolutions[0].decision, Decision.INSTALL_SUGGESTED)
        self.assertEqual(resolutions[0].risk_level, "high")
        self.assertEqual(resolutions[0].matched_local_asset_ids, [])

    def test_gap_with_similar_local_capability_yields_create_local(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            asset = CapabilityAsset.create(
                name="browser-automation",
                type="mcp_server",
                source="codex_mcp",
                install_path="/tmp/config.toml",
            )
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            inventory.write([asset])

            resolver = CapabilityResolver(inventory)
            resolutions = resolver.resolve(
                gaps=[
                    {
                        "gap_id": "gap-1",
                        "gap_description": "Need browser-based screenshot capture for design review.",
                        "source": "test",
                    }
                ]
            )

        self.assertEqual(len(resolutions), 1)
        self.assertEqual(resolutions[0].decision, Decision.CREATE_LOCAL)
        self.assertIn(asset.id, resolutions[0].matched_local_asset_ids)

    def test_resolve_from_learnings_extracts_capability_gaps(self):
        learning = CandidateLearningItem.create(
            summary="A browser automation tool is needed for web research tasks.",
            type="capability_gap",
            evidence_refs=["event-1"],
            reverse_learning_target="capability_pack",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            asset = CapabilityAsset.create(
                name="browser",
                type="mcp_server",
                source="codex_mcp",
                install_path="/tmp/config.toml",
                permissions=["network", "process"],
            )
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            inventory.write([asset])

            resolver = CapabilityResolver(inventory)
            resolutions = resolver.resolve_from_learnings([learning])

        self.assertGreaterEqual(len(resolutions), 1)
        self.assertIn(resolutions[0].decision, {Decision.REUSE, Decision.CONFIGURE})

    def test_resolve_from_advice_creates_resolutions_per_missing_capability(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            inventory.write([])

            resolver = CapabilityResolver(inventory)
            resolutions = resolver.resolve_from_advice(["roadmap", "browser-automation"])

        self.assertEqual(len(resolutions), 2)
        self.assertTrue(all(r.decision == Decision.INSTALL_SUGGESTED for r in resolutions))

    def test_resolve_from_findings_handles_dedupe_and_risk_categories(self):
        findings = [
            GovernanceFinding(
                category="dedupe",
                severity="low",
                subject_id="asset-1,asset-2",
                summary="Potential duplicate capability assets.",
                recommended_action="Review duplicate assets before any merge or archive action.",
            ),
            GovernanceFinding(
                category="risk",
                severity="high",
                subject_id="asset-3",
                summary="Capability asset has elevated risk score 0.8.",
                recommended_action="Require human review before expanding use of this asset.",
            ),
            GovernanceFinding(
                category="work_contract",
                severity="medium",
                subject_id="contract-1",
                summary="Missing required fields.",
                recommended_action="Ask missing question strategy fields before execution.",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            inventory = CapabilityInventory(store / "assets" / "inventory.json")
            inventory.write([])
            resolver = CapabilityResolver(inventory)
            resolutions = resolver.resolve_from_findings(findings)

        self.assertGreaterEqual(len(resolutions), 2)

    def test_resolution_is_deterministic_for_same_inputs(self):
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
            resolver = CapabilityResolver(inventory)

            first = resolver.resolve(
                gaps=[{"gap_id": "gap-1", "gap_description": "Need research capability.", "source": "test"}]
            )
            second = resolver.resolve(
                gaps=[{"gap_id": "gap-1", "gap_description": "Need research capability.", "source": "test"}]
            )

        self.assertEqual(first[0].decision, second[0].decision)
        self.assertEqual(first[0].matched_local_asset_ids, second[0].matched_local_asset_ids)

    def test_resolution_reporter_writes_markdown_and_json(self):
        resolutions = [
            CapabilityResolution(
                gap_id="gap-1",
                gap_description="Need research capability.",
                decision=Decision.REUSE,
                risk_level="low",
                matched_local_asset_ids=["asset-abc"],
                external_options=[],
                confidence=0.9,
                evidence=["Exact local match: research (skill)"],
                recommended_action="Reuse existing local capability: research (skill)",
                source="test",
            ),
            CapabilityResolution(
                gap_id="gap-2",
                gap_description="Need browser automation for web scraping.",
                decision=Decision.INSTALL_SUGGESTED,
                risk_level="high",
                matched_local_asset_ids=[],
                external_options=[{"type": "mcp_server", "name": "browser"}],
                confidence=0.3,
                evidence=["No local capability matches keywords: browser, automation, scraping"],
                recommended_action="Consider installing or creating a capability for: browser automation",
                source="test",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = ResolutionReporter(Path(tmpdir) / "reports")
            report = reporter.write(resolutions)

            self.assertTrue(report.markdown_path.exists())
            self.assertTrue(report.json_path.exists())
            markdown = report.markdown_path.read_text(encoding="utf-8")
            json_data = json.loads(report.json_path.read_text(encoding="utf-8"))

        self.assertIn("Capability Resolution Report", markdown)
        self.assertIn("[reuse]", markdown)
        self.assertIn("[install_suggested]", markdown)
        self.assertEqual(json_data["summary"]["total_gaps"], 2)
        self.assertEqual(json_data["summary"]["by_decision"], {"reuse": 1, "install_suggested": 1})

    def test_resolver_deduplicates_gaps_with_same_id(self):
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

            resolver = CapabilityResolver(inventory)
            resolutions = resolver.resolve(
                gaps=[
                    {"gap_id": "same-id", "gap_description": "Need research capability.", "source": "test"},
                    {"gap_id": "same-id", "gap_description": "Need research capability.", "source": "test"},
                ]
            )

        self.assertEqual(len(resolutions), 1)

    def test_cli_resolve_run_and_report_commands(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            asset = CapabilityAsset.create(
                name="research",
                type="skill",
                source="local_skill",
                install_path="/tmp/skills/research",
            )
            CapabilityInventory(store / "assets" / "inventory.json").write([asset])

            run = subprocess.run(
                [sys.executable, "-m", "argus.cli", "resolve", "run", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )
            report = subprocess.run(
                [sys.executable, "-m", "argus.cli", "resolve", "report", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )

            resolutions = json.loads(run.stdout)
            report_payload = json.loads(report.stdout)

        self.assertIsInstance(resolutions, list)
        self.assertIn("markdown_path", report_payload)
        self.assertIn("json_path", report_payload)


if __name__ == "__main__":
    unittest.main()
