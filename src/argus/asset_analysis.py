from __future__ import annotations

from dataclasses import dataclass

from argus.asset_models import CapabilityAsset
from argus.asset_text import normalize


@dataclass(frozen=True)
class AssetRiskCounts:
    low: int
    medium: int
    high: int


@dataclass(frozen=True)
class AssetAnalysis:
    by_type: dict[str, int]
    duplicates: list[list[CapabilityAsset]]
    conflicts: list[list[CapabilityAsset]]
    risky_assets: list[CapabilityAsset]
    risk_counts: AssetRiskCounts


def analyze_assets(assets: list[CapabilityAsset]) -> AssetAnalysis:
    by_type: dict[str, int] = {}
    risk_counts = {"low": 0, "medium": 0, "high": 0}
    for asset in assets:
        by_type[asset.type] = by_type.get(asset.type, 0) + 1
        if asset.risk_score >= 0.7:
            risk_counts["high"] += 1
        elif asset.risk_score >= 0.4:
            risk_counts["medium"] += 1
        else:
            risk_counts["low"] += 1
    return AssetAnalysis(
        by_type=by_type,
        duplicates=find_potential_duplicates(assets),
        conflicts=find_potential_conflicts(assets),
        risky_assets=[asset for asset in assets if asset.risk_score >= 0.5],
        risk_counts=AssetRiskCounts(**risk_counts),
    )


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
