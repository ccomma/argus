from __future__ import annotations

"""资产分析模块。

提供资产清单的分析能力，包括：
- 按类型统计资产分布
- 检测潜在的重复资产
- 检测潜在的冲突资产（多个同名资产共享相同的代理或行为域）
- 识别高风险资产并统计风险分布
"""

from dataclasses import dataclass

from argus.assets.models import CapabilityAsset
from argus.assets.text import normalize


@dataclass(frozen=True)
class AssetRiskCounts:
    """资产风险计数的三分层统计。

    将资产按风险评分分为三档：
    - low: risk < 0.4
    - medium: 0.4 <= risk < 0.7
    - high: risk >= 0.7
    """

    low: int
    medium: int
    high: int


@dataclass(frozen=True)
class AssetAnalysis:
    """资产分析的完整结果。

    包含按类型统计、重复检测、冲突检测、高风险资产列表和风险计数。
    """

    by_type: dict[str, int]
    duplicates: list[list[CapabilityAsset]]
    conflicts: list[list[CapabilityAsset]]
    risky_assets: list[CapabilityAsset]
    risk_counts: AssetRiskCounts


def analyze_assets(assets: list[CapabilityAsset]) -> AssetAnalysis:
    """对资产列表进行全面分析。

    流程：
    1. 按类型统计资产数量
    2. 按风险评分分层统计（高/中/低）
    3. 检测潜在重复（同名资产）
    4. 检测潜在冲突（共享代理的冲突资产）
    5. 筛选风险评分 >= 0.5 的高风险资产

    返回结构化的 AssetAnalysis 结果。
    """
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
    """检测潜在重复资产。

    流程：
    1. 对资产名称做归一化处理（去除后缀、统一大小写）
    2. 将同名资产归为一组
    3. 返回包含多于 1 项的组

    例如 "git-skill" 和 "git_skill" 会被识别为潜在重复。
    """
    groups: dict[str, list[CapabilityAsset]] = {}
    for asset in assets:
        key = _normalized_asset_name(asset.name)
        groups.setdefault(key, []).append(asset)
    return [group for _, group in sorted(groups.items()) if len(group) > 1]


def find_potential_conflicts(assets: list[CapabilityAsset]) -> list[list[CapabilityAsset]]:
    """检测潜在冲突资产。

    两个资产如果满足以下条件则视为冲突：
    1. 名称相同（归一化后）
    2. 属于会影响代理行为的类型（skill/rule/memory/plugin）
    3. 共享相同的代理或有重叠的类型（行为域冲突）

    例如，两个同名的 rule 文件同时绑定到 codex 代理，可能导致
    行为规则的冲突或未定义行为。
    """
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
    """检查一组资产是否共享代理或行为域。

    条件一：任意两个资产共享至少一个代理 → 冲突
    条件二：组内存在多种不同资产类型 → 行为域重叠 → 冲突

    只有当资产不共享代理且类型相同时，才可能不冲突。
    """
    agent_sets = [set(asset.agents) for asset in group if asset.agents]
    for index, agents in enumerate(agent_sets):
        if any(agents & other for other in agent_sets[index + 1 :]):
            return True
    return len({asset.type for asset in group}) > 1


def _normalized_asset_name(name: str) -> str:
    """归一化资产名称以便比较。

    去除常见后缀（skill/plugin/script/server），
    然后做空格归一化处理。这样可以识别
    "Git Skill" 和 "git-skill" 是同一个资产。
    """
    normalized = normalize(name)
    for suffix in (" skill", " plugin", " script", " server"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
    return " ".join(normalized.split())
