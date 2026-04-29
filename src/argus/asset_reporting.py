from __future__ import annotations

import json
from pathlib import Path

from argus.asset_models import AssetLearningLink, AssetReport, CapabilityAsset
from argus.asset_text import normalize


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


def find_potential_duplicates(assets: list[CapabilityAsset]) -> list[list[CapabilityAsset]]:
    groups: dict[str, list[CapabilityAsset]] = {}
    for asset in assets:
        key = _normalized_asset_name(asset.name)
        groups.setdefault(key, []).append(asset)
    return [group for _, group in sorted(groups.items()) if len(group) > 1]


def find_potential_conflicts(assets: list[CapabilityAsset]) -> list[list[CapabilityAsset]]:
    groups: dict[str, list[CapabilityAsset]] = {}
    for asset in assets:
        if asset.type not in {"skill", "rule", "memory", "plugin"}:
            continue
        groups.setdefault(_normalized_asset_name(asset.name), []).append(asset)
    return [
        group
        for _, group in sorted(groups.items())
        if len(group) > 1 and _group_has_shared_agent_or_behavior_scope(group)
    ]


def _markdown_report(
    assets: list[CapabilityAsset],
    warnings: list[str],
    links: list[AssetLearningLink],
) -> str:
    by_type: dict[str, int] = {}
    duplicates = find_potential_duplicates(assets)
    conflicts = find_potential_conflicts(assets)
    risky_assets = [asset for asset in assets if asset.risk_score >= 0.5]
    risk_counts = {"low": 0, "medium": 0, "high": 0}
    for asset in assets:
        by_type[asset.type] = by_type.get(asset.type, 0) + 1
        if asset.risk_score >= 0.7:
            risk_counts["high"] += 1
        elif asset.risk_score >= 0.4:
            risk_counts["medium"] += 1
        else:
            risk_counts["low"] += 1
    lines = [
        "# Argus Capability Asset Report",
        "",
        f"- Assets: {len(assets)}",
        f"- Candidate Links: {len(links)}",
        f"- Risk: low={risk_counts['low']}, medium={risk_counts['medium']}, high={risk_counts['high']}",
        "",
        "## Assets By Type",
        "",
    ]
    if not by_type:
        lines.append("No capability assets found.")
    for asset_type, count in sorted(by_type.items()):
        lines.append(f"- {asset_type}: {count}")
    if duplicates:
        lines.extend(["", "## Potential Duplicates", ""])
        for group in duplicates:
            lines.append(f"- {_asset_names(group)}")
    if conflicts:
        lines.extend(["", "## Potential Conflicts", ""])
        for group in conflicts:
            lines.append(f"- {_asset_names(group)}")
    if risky_assets:
        lines.extend(["", "## Risky Assets", ""])
        for asset in sorted(risky_assets, key=lambda item: (-item.risk_score, item.type, item.name)):
            permissions = ", ".join(asset.permissions) or "none"
            lines.append(f"- {asset.name} ({asset.type}): risk={asset.risk_score}, permissions={permissions}")
    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"


def _asset_names(group: list[CapabilityAsset]) -> str:
    return ", ".join(f"{asset.name} ({asset.type})" for asset in group)


def _group_has_shared_agent_or_behavior_scope(group: list[CapabilityAsset]) -> bool:
    agent_sets = [set(asset.agents) for asset in group if asset.agents]
    for index, agents in enumerate(agent_sets):
        if any(agents & other for other in agent_sets[index + 1 :]):
            return True
    return len({asset.type for asset in group}) > 1


def _normalized_asset_name(name: str) -> str:
    normalized = normalize(name)
    for suffix in (" skill", " plugin", " script", " server"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
    return " ".join(normalized.split())
