from __future__ import annotations

"""资产报告生成模块。

提供 AssetReporter 类，将扫描结果和分析结果整理为可读的 Markdown 报告
和结构化的 JSON 报告。报告涵盖资产按类型分布、潜在重复和冲突、
高风险资产列表以及扫描警告。
"""

import json
from pathlib import Path

from argus.assets.analysis import analyze_assets
from argus.assets.models import AssetLearningLink, AssetReport, CapabilityAsset


class AssetReporter:
    """资产报告生成器。

    将资产扫描和分析的结果输出为标准化报告文件。
    """

    def __init__(self, reports_dir: str | Path) -> None:
        """初始化报告器。

        Args:
            reports_dir: 报告输出目录
        """
        self.reports_dir = Path(reports_dir)

    def write(
        self,
        assets: list[CapabilityAsset],
        *,
        warnings: list[str] | None = None,
        links: list[AssetLearningLink] | None = None,
    ) -> AssetReport:
        """生成资产扫描报告。

        流程：
        1. 创建报告目录
        2. 生成 asset-scan-report.md（人类可读的 Markdown 报告）
        3. 如果有学习-资产关联，额外生成 candidate-asset-links.json
        4. 返回 AssetReport 对象，包含生成的路径

        Args:
            assets: 能力资产列表
            warnings: 扫描过程中产生的警告
            links: 学习与资产的关联记录

        Returns:
            包含报告路径的 AssetReport 对象
        """
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.reports_dir / "asset-scan-report.md"
        link_report_path = self.reports_dir / "candidate-asset-links.json"
        report_path.write_text(_markdown_report(assets, warnings or [], links or []), encoding="utf-8")
        if links is not None:
            link_report_path.write_text(
                json.dumps([link.to_dict() for link in links], indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            return AssetReport(report_path=report_path, link_report_path=link_report_path)
        return AssetReport(report_path=report_path)


def _markdown_report(
    assets: list[CapabilityAsset],
    warnings: list[str],
    links: list[AssetLearningLink],
) -> str:
    """生成资产扫描 Markdown 报告的内容。

    包含以下章节：
    - 总览统计
    - 按类型分布的资产计数
    - 潜在重复资产（同名但 ID 不同）
    - 潜在冲突资产（同名且有代理或行为域重叠）
    - 高风险资产列表（按风险评分降序）
    - 扫描警告
    """
    analysis = analyze_assets(assets)
    lines = [
        "# Argus Capability Asset Report",
        "",
        f"- Assets: {len(assets)}",
        f"- Candidate Links: {len(links)}",
        f"- Risk: low={analysis.risk_counts.low}, medium={analysis.risk_counts.medium}, high={analysis.risk_counts.high}",
        "",
        "## Assets By Type",
        "",
    ]
    if not analysis.by_type:
        lines.append("No capability assets found.")
    for asset_type, count in sorted(analysis.by_type.items()):
        lines.append(f"- {asset_type}: {count}")
    if analysis.duplicates:
        lines.extend(["", "## Potential Duplicates", ""])
        for group in analysis.duplicates:
            lines.append(f"- {_asset_names(group)}")
    if analysis.conflicts:
        lines.extend(["", "## Potential Conflicts", ""])
        for group in analysis.conflicts:
            lines.append(f"- {_asset_names(group)}")
    if analysis.risky_assets:
        lines.extend(["", "## Risky Assets", ""])
        for asset in sorted(analysis.risky_assets, key=lambda item: (-item.risk_score, item.type, item.name)):
            permissions = ", ".join(asset.permissions) or "none"
            lines.append(f"- {asset.name} ({asset.type}): risk={asset.risk_score}, permissions={permissions}")
    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"


def _asset_names(group: list[CapabilityAsset]) -> str:
    """格式化一组资产的名称列表，附带类型标注。"""
    return ", ".join(f"{asset.name} ({asset.type})" for asset in group)
