import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from argus.assets import (
    AssetReporter,
    CandidateAssetLinker,
    CapabilityAsset,
    CapabilityAssetScanner,
    CapabilityInventory,
    local_codex_asset_profile,
)
from argus.learning import CandidateLearningItem, LearningLedger


FIXTURES = Path(__file__).parent / "fixtures" / "assets"


class Phase3AssetsTest(unittest.TestCase):
    def test_scanner_discovers_local_capability_assets(self):
        result = CapabilityAssetScanner().scan(
            skill_dirs=[FIXTURES / "skills"],
            plugin_dirs=[FIXTURES / "plugins"],
            mcp_configs=[FIXTURES / "mcp.json"],
            rule_files=[FIXTURES / "rules" / "AGENTS.md"],
            script_dirs=[FIXTURES / "scripts"],
            memory_dirs=[FIXTURES / "memory"],
        )

        by_type = {asset.type: asset for asset in result.assets}

        self.assertEqual(result.warnings, [])
        self.assertEqual(set(by_type), {"skill", "plugin", "mcp_server", "rule", "script", "memory"})
        self.assertEqual(by_type["plugin"].name, "demo-plugin")
        self.assertEqual(by_type["plugin"].version, "0.1.0")
        self.assertIn("network", by_type["plugin"].permissions)
        self.assertIn("process", by_type["mcp_server"].permissions)
        self.assertEqual(by_type["rule"].agents, ["codex"])

    def test_inventory_persists_assets_and_deduplicates_scan_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = CapabilityAssetScanner().scan(skill_dirs=[FIXTURES / "skills", FIXTURES / "skills"])
            inventory = CapabilityInventory(Path(tmpdir) / ".argus" / "assets" / "inventory.json")
            inventory.write(result.assets)
            loaded = inventory.list_assets()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].type, "skill")
        self.assertEqual(loaded[0].name, "research")

    def test_scanner_reads_toml_mcp_config_variants(self):
        result = CapabilityAssetScanner().scan(mcp_configs=[FIXTURES / "mcp.toml"])

        assets = {asset.name: asset for asset in result.assets}

        self.assertEqual(result.warnings, [])
        self.assertEqual(set(assets), {"context7", "remote-tools"})
        self.assertIn("process", assets["context7"].permissions)
        self.assertIn("network", assets["remote-tools"].permissions)

    def test_local_codex_profile_uses_home_relative_asset_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            (home / ".codex" / "skills" / "profile-skill").mkdir(parents=True)
            (home / ".codex" / "skills" / "profile-skill" / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
            (home / ".agents" / "skills").mkdir(parents=True)
            (home / ".codex" / "plugins" / "cache" / "demo" / ".codex-plugin").mkdir(parents=True)
            (home / ".codex" / "plugins" / "cache" / "demo" / ".codex-plugin" / "plugin.json").write_text(
                '{"name":"profile-plugin","version":"1.0.0"}\n',
                encoding="utf-8",
            )
            (home / ".codex" / "config.toml").write_text(
                '[mcp_servers.profile]\ncommand = "node"\nargs = ["server.js"]\n',
                encoding="utf-8",
            )
            (home / ".codex").mkdir(exist_ok=True)
            (home / ".codex" / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
            (home / ".codex" / "memories").mkdir(parents=True)
            (home / ".codex" / "memories" / "MEMORY.md").write_text("# Memory\n", encoding="utf-8")

            profile = local_codex_asset_profile(home)
            result = CapabilityAssetScanner().scan(**profile.to_scan_kwargs())

        by_name = {asset.name: asset.type for asset in result.assets}
        self.assertEqual(result.warnings, [])
        self.assertEqual(by_name["profile-skill"], "skill")
        self.assertEqual(by_name["profile-plugin"], "plugin")
        self.assertEqual(by_name["profile"], "mcp_server")
        self.assertEqual(by_name["AGENTS.md"], "rule")
        self.assertEqual(by_name["MEMORY.md"], "memory")

    def test_candidate_learning_links_to_matching_asset(self):
        result = CapabilityAssetScanner().scan(script_dirs=[FIXTURES / "scripts"])
        learning = CandidateLearningItem.create(
            summary="A repair script can document command recovery.",
            type="tool_pitfall",
            evidence_refs=["event-1"],
            reverse_learning_target="capability_pack",
        )

        links = CandidateAssetLinker().link([learning], result.assets)

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].learning_id, learning.id)
        self.assertEqual(links[0].asset_id, result.assets[0].id)

    def test_candidate_learning_does_not_link_on_generic_capability_words(self):
        result = CapabilityAssetScanner().scan(script_dirs=[FIXTURES / "scripts"])
        learning = CandidateLearningItem.create(
            summary="A capability pack may be needed for this tool.",
            type="capability_gap",
            evidence_refs=["event-1"],
            reverse_learning_target="capability_pack",
        )

        links = CandidateAssetLinker().link([learning], result.assets)

        self.assertEqual(links, [])

    def test_asset_report_flags_potential_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assets = [
                CapabilityAsset.create(
                    name="research",
                    type="skill",
                    source="local_skill",
                    install_path=Path(tmpdir) / "skills" / "research",
                    agents=["codex"],
                ),
                CapabilityAsset.create(
                    name="research plugin",
                    type="plugin",
                    source="codex_plugin",
                    install_path=Path(tmpdir) / "plugins" / "research",
                    agents=["codex"],
                    permissions=["network"],
                    risk_score=0.55,
                ),
            ]

            report = AssetReporter(Path(tmpdir) / ".argus" / "assets" / "reports").write(assets)
            markdown = report.report_path.read_text(encoding="utf-8")

        self.assertIn("Potential Duplicates", markdown)
        self.assertIn("Potential Conflicts", markdown)
        self.assertIn("Risky Assets", markdown)
        self.assertIn("research (skill)", markdown)
        self.assertIn("research plugin (plugin)", markdown)
        self.assertIn("permissions=network", markdown)

    def test_assets_cli_scan_list_report_and_link(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / ".argus"
            learning_ledger = LearningLedger(store / "ledger" / "candidate_learnings.jsonl")
            learning_ledger.append(
                CandidateLearningItem.create(
                    summary="A repair script can document command recovery.",
                    type="tool_pitfall",
                    evidence_refs=["event-1"],
                    reverse_learning_target="capability_pack",
                )
            )

            scan = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "assets",
                    "scan",
                    "--store",
                    str(store),
                    "--skill-dir",
                    str(FIXTURES / "skills"),
                    "--plugin-dir",
                    str(FIXTURES / "plugins"),
                    "--mcp-config",
                    str(FIXTURES / "mcp.json"),
                    "--rule-file",
                    str(FIXTURES / "rules" / "AGENTS.md"),
                    "--script-dir",
                    str(FIXTURES / "scripts"),
                    "--memory-dir",
                    str(FIXTURES / "memory"),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            listed = subprocess.run(
                [sys.executable, "-m", "argus.cli", "assets", "list", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )
            report = subprocess.run(
                [sys.executable, "-m", "argus.cli", "assets", "report", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )
            links = subprocess.run(
                [sys.executable, "-m", "argus.cli", "assets", "link-learnings", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )

            inventory = json.loads(listed.stdout)

        self.assertEqual(json.loads(scan.stdout)["assets"], 6)
        self.assertEqual(len(inventory), 6)
        self.assertIn("asset-scan-report.md", json.loads(report.stdout)["report_path"])
        self.assertEqual(json.loads(links.stdout)["links"], 1)

    def test_assets_cli_scan_supports_local_codex_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            store = Path(tmpdir) / ".argus"
            (home / ".codex" / "skills" / "cli-skill").mkdir(parents=True)
            (home / ".codex" / "skills" / "cli-skill" / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
            (home / ".codex" / "config.toml").write_text(
                '[mcp_servers.cli]\ncommand = "node"\n',
                encoding="utf-8",
            )

            scan = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "argus.cli",
                    "assets",
                    "scan",
                    "--store",
                    str(store),
                    "--profile",
                    "local-codex",
                    "--profile-home",
                    str(home),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            listed = subprocess.run(
                [sys.executable, "-m", "argus.cli", "assets", "list", "--store", str(store)],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(json.loads(scan.stdout)["profiles"], ["local-codex"])
        self.assertEqual(json.loads(scan.stdout)["assets"], 2)
        self.assertEqual({asset["type"] for asset in json.loads(listed.stdout)}, {"skill", "mcp_server"})


if __name__ == "__main__":
    unittest.main()
