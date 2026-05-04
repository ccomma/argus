from __future__ import annotations

import json
from pathlib import Path

from argus.assets.analysis import analyze_assets
from argus.assets.models import AssetLearningLink, AssetReport, CapabilityAsset


class AssetReporter:
    def __init__(self, reports_dir: str | Path) -> None:
        self.reports_dir = Path(reports_dir)

    def write(
        self,
        assets: list[CapabilityAsset],
        *,
        warnings: list[str] | None = None,
        links: list[AssetLearningLink] | None = None,
    ) -> AssetReport:
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
    return ", ".join(f"{asset.name} ({asset.type})" for asset in group)
