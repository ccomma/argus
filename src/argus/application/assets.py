"""资产应用服务，管理能力资产的扫描、盘点与学习链接。

实现能力资产的发现（扫描）、清单维护、报告生成，
以及将候选学习项与已有资产进行关联匹配。
"""

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
    """资产子系统的应用门面，编排资产扫描、盘点、报告和学习链接。"""

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
        """根据扫描配置发现能力资产并写入清单。

        1. 使用 CapabilityAssetScanner 扫描指定的 profile
        2. 将扫描结果写入能力清单（CapabilityInventory）
        3. 生成资产报告（含警告信息）
        """
        result = CapabilityAssetScanner().scan_profile(profile)
        self.inventory.write(result.assets)
        report = AssetReporter(self.reports_dir).write(result.assets, warnings=result.warnings)
        return result, report

    def list_assets(self) -> list[CapabilityAsset]:
        """列出当前清单中的所有能力资产。"""
        return self.inventory.list_assets()

    def write_report(self) -> AssetReport:
        """为当前清单中的全部资产生成报告。"""
        return AssetReporter(self.reports_dir).write(self.inventory.list_assets())

    def link_learnings(self) -> tuple[list[AssetLearningLink], AssetReport]:
        """将候选项学习项与已有资产进行关联匹配。

        1. 获取全部资产和候选学习项
        2. 使用 CandidateAssetLinker 进行自动关联
        3. 生成带链接信息的资产报告
        """
        assets = self.inventory.list_assets()
        links = CandidateAssetLinker().link(self.learning_ledger.list_items(), assets)
        report = AssetReporter(self.reports_dir).write(assets, links=links)
        return links, report
