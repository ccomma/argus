from __future__ import annotations

from pathlib import Path

from argus.assets import (
    AssetLearningLink,
    AssetReport,
    AssetScanProfile,
    AssetScanResult,
    AssetReporter,
    CandidateAssetLinker,
    CapabilityAsset,
    CapabilityAssetScanner,
    CapabilityInventory,
)
from argus.ledger import LearningLedger


class AssetApplication:
    def __init__(
        self,
        inventory: CapabilityInventory,
        reports_dir: str | Path,
        learning_ledger: LearningLedger,
    ) -> None:
        self.inventory = inventory
        self.reports_dir = Path(reports_dir)
        self.learning_ledger = learning_ledger

    def scan(self, profile: AssetScanProfile) -> tuple[AssetScanResult, AssetReport]:
        result = CapabilityAssetScanner().scan_profile(profile)
        self.inventory.write(result.assets)
        report = AssetReporter(self.reports_dir).write(result.assets, warnings=result.warnings)
        return result, report

    def list_assets(self) -> list[CapabilityAsset]:
        return self.inventory.list_assets()

    def write_report(self) -> AssetReport:
        return AssetReporter(self.reports_dir).write(self.inventory.list_assets())

    def link_learnings(self) -> tuple[list[AssetLearningLink], AssetReport]:
        assets = self.inventory.list_assets()
        links = CandidateAssetLinker().link(self.learning_ledger.list_items(), assets)
        report = AssetReporter(self.reports_dir).write(assets, links=links)
        return links, report
