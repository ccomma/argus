"""能力缺口解析引擎，将能力缺口信号匹配到本地资产或给出外部建议。

核心算法：对每个缺口描述提取关键词，与本地资产库进行三层匹配：
  1. 精确匹配（REUSE）：关键词高度重合，直接复用
  2. 部分匹配（CONFIGURE）：达到阈值 0.15，可配置现有资产满足
  3. 相似匹配（CREATE_LOCAL）：存在低分关联，可参照创建新资产
  4. 无匹配（INSTALL_SUGGESTED）：建议从外部安装或创建能力
"""

from __future__ import annotations

from argus.assets import CapabilityAsset, CapabilityInventory, analyze_assets, normalize
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.governance import GovernanceFinding
from argus.ledger import CandidateLearningItem

from .models import DECISION_RISK, CapabilityResolution, Decision


class CapabilityResolver:
    """能力缺口解析引擎，从多源信号中发现并解决能力差距。

    支持四种缺口来源：
    - 手动传入的缺口字典列表（resolve）
    - 反向学习目标指向能力包/合约的学习项（resolve_from_learnings）
    - 能力包咨询返回的缺失能力列表（resolve_from_advice）
    - 治理报告中的去重/风险/角色发现（resolve_from_findings）
    """

    def __init__(
        self,
        inventory: CapabilityInventory,
        pack_store: CapabilityPackStore | None = None,
        role_store: RolePackStore | None = None,
    ) -> None:
        self.inventory = inventory
        self.pack_store = pack_store
        self.role_store = role_store

    def resolve(
        self,
        *,
        gaps: list[dict],
        contract_id: str = "",
        role_id: str = "",
    ) -> list[CapabilityResolution]:
        """对缺口列表逐一解析，返回去重后的处置建议。

        1. 获取当前资产清单
        2. 对每个缺口执行关键词匹配算法
        3. 按 gap_id 去重返回
        """
        assets = self.inventory.list_assets()
        resolutions: list[CapabilityResolution] = []
        for gap in gaps:
            resolutions.append(
                _resolve_gap(
                    assets=assets,
                    gap_description=gap.get("gap_description", gap.get("summary", "")),
                    gap_id=gap.get("gap_id", ""),
                    contract_id=contract_id,
                    role_id=role_id,
                    source=gap.get("source", ""),
                )
            )
        return _deduplicate_resolutions(resolutions)

    def resolve_from_learnings(
        self,
        learnings: list[CandidateLearningItem],
        *,
        contract_id: str = "",
        role_id: str = "",
    ) -> list[CapabilityResolution]:
        """从候选学习项中提取反向学习目标为能力缺口并解析。

        仅处理 reverse_learning_target 为 capability_pack 或
        deliverable_contract 的学习项——这些方向暗示能力缺失。
        """
        gaps: list[dict] = []
        for item in learnings:
            if item.reverse_learning_target in {"capability_pack", "deliverable_contract"}:
                gaps.append(
                    {
                        "gap_id": item.id,
                        "gap_description": item.summary,
                        "source": "candidate_learning",
                        "confidence": item.confidence,
                    }
                )
        return self.resolve(gaps=gaps, contract_id=contract_id, role_id=role_id)

    def resolve_from_advice(
        self,
        missing_capabilities: list[str],
        *,
        contract_id: str = "",
        role_id: str = "",
    ) -> list[CapabilityResolution]:
        """从能力包咨询返回的缺失能力名称列表构建缺口并解析。"""
        gaps = [
            {
                "gap_id": f"advice-{normalize(name)[:20]}",
                "gap_description": f"Missing capability: {name}",
                "source": "pack_advice",
            }
            for name in missing_capabilities
        ]
        return self.resolve(gaps=gaps, contract_id=contract_id, role_id=role_id)

    def resolve_from_findings(
        self,
        findings: list[GovernanceFinding],
        *,
        contract_id: str = "",
        role_id: str = "",
    ) -> list[CapabilityResolution]:
        """从治理发现中提取去重/风险/角色类发现并构建缺口。

        仅处理 dedupe、risk、role 三类发现，
        其他类型的治理发现不直接对应能力缺口。
        """
        gaps: list[dict] = []
        for finding in findings:
            if finding.category in {"dedupe", "risk", "role"}:
                gaps.append(
                    {
                        "gap_id": finding.subject_id,
                        "gap_description": finding.recommended_action,
                        "source": f"governance_{finding.category}",
                    }
                )
        return self.resolve(gaps=gaps, contract_id=contract_id, role_id=role_id)


def _resolve_gap(
    *,
    assets: list[CapabilityAsset],
    gap_description: str,
    gap_id: str,
    contract_id: str,
    role_id: str,
    source: str,
) -> CapabilityResolution:
    """单个缺口的解析核心，按四级策略链式匹配。

    匹配策略（由优到劣）：
    1. REUSE——精确匹配：关键词交集 >= 资产 tokens 的 50%
    2. CONFIGURE——部分匹配：关键词重叠分 >= 0.15 阈值
    3. CREATE_LOCAL——弱相似：关键词分在 (0, 0.15) 区间
    4. INSTALL_SUGGESTED——无匹配：建议外部安装（高风险）

    返回值中 confidence 反映匹配置信度，risk_level 由决策类型决定。
    """
    gap_norm = normalize(gap_description)
    keywords = _extract_keywords(gap_norm)

    # 第 1 级：精确匹配，可直接复用
    exact_matches = [asset for asset in assets if _is_exact_match(asset, keywords)]
    if exact_matches:
        return CapabilityResolution(
            gap_id=gap_id,
            gap_description=gap_description,
            decision=Decision.REUSE,
            risk_level="low",
            matched_local_asset_ids=[asset.id for asset in exact_matches],
            external_options=[],
            confidence=0.9,
            evidence=[f"Exact local match: {asset.name} ({asset.type})" for asset in exact_matches],
            recommended_action=f"Reuse existing local capability: {_asset_list(exact_matches)}",
            contract_id=contract_id,
            role_id=role_id,
            source=source,
        )

    # 第 2 级：部分匹配，可配置现有资产满足缺口
    scored = _scored_matches(assets, keywords)
    if scored:
        best = scored[:3]
        return CapabilityResolution(
            gap_id=gap_id,
            gap_description=gap_description,
            decision=Decision.CONFIGURE,
            risk_level="low",
            matched_local_asset_ids=[asset.id for asset, _ in best],
            external_options=[],
            confidence=round(best[0][1], 2) if best else 0.5,
            evidence=[f"Partial local match (score={s:.2f}): {asset.name} ({asset.type})" for asset, s in best],
            recommended_action=f"Configure existing local capability to cover gap: {_asset_list([a for a, _ in best])}",
            contract_id=contract_id,
            role_id=role_id,
            source=source,
        )

    # 第 3 级：存在弱相似资产，可参照创建新能力
    similar = _find_similar(assets, keywords)
    if similar:
        return CapabilityResolution(
            gap_id=gap_id,
            gap_description=gap_description,
            decision=Decision.CREATE_LOCAL,
            risk_level="medium",
            matched_local_asset_ids=[asset.id for asset in similar],
            external_options=[],
            confidence=0.55,
            evidence=[f"Similar local capability: {asset.name} ({asset.type})" for asset in similar],
            recommended_action=f"Create a new local capability modeled on: {_asset_list(similar)}",
            contract_id=contract_id,
            role_id=role_id,
            source=source,
        )

    # 第 4 级：无本地匹配，只能建议外部安装
    kw_list = sorted(keywords)
    return CapabilityResolution(
        gap_id=gap_id,
        gap_description=gap_description,
        decision=Decision.INSTALL_SUGGESTED,
        risk_level="high",
        matched_local_asset_ids=[],
        external_options=[{"type": "unknown", "name": kw} for kw in kw_list[:3]],
        confidence=0.3,
        evidence=[f"No local capability matches keywords: {', '.join(kw_list[:5])}"],
        recommended_action=f"Consider installing or creating a capability for: {gap_description}",
        contract_id=contract_id,
        role_id=role_id,
        source=source,
    )


def _is_exact_match(asset: CapabilityAsset, gap_keywords: set[str]) -> bool:
    """判断资产与缺口关键词是否精确匹配。

    条件：关键词至少覆盖资产 tokens 的 50% 且有交集。
    """
    asset_tokens = set(normalize(asset.name).split()) | {asset.type}
    return bool(asset_tokens & gap_keywords) and len(asset_tokens & gap_keywords) >= len(asset_tokens) * 0.5


# 部分匹配的最低分数阈值，低于此值视为无有效匹配
_CONFIGURE_THRESHOLD = 0.15


def _scored_matches(assets: list[CapabilityAsset], keywords: set[str]) -> list[tuple[CapabilityAsset, float]]:
    """计算所有资产与关键词的匹配分，返回 >= 阈值的按分降序排列。"""
    results = [(asset, _keyword_overlap(asset, keywords)) for asset in assets]
    scored = [(asset, score) for asset, score in results if score >= _CONFIGURE_THRESHOLD]
    return sorted(scored, key=lambda item: -item[1])


def _find_similar(assets: list[CapabilityAsset], keywords: set[str]) -> list[CapabilityAsset]:
    """寻找与关键词有弱相似性的资产（分数在 0 到阈值之间），最多返回 3 个。"""
    results: list[CapabilityAsset] = []
    for asset in assets:
        score = _keyword_overlap(asset, keywords)
        if 0.0 < score < _CONFIGURE_THRESHOLD:
            results.append(asset)
    return results[:3]


def _keyword_overlap(asset: CapabilityAsset, keywords: set[str]) -> float:
    """计算资产搜索文本与缺口关键词的重叠分，上限 0.75。"""
    text = _asset_search_text(asset)
    if not text or not keywords:
        return 0.0
    text_tokens = set(text.split())
    overlap = len(keywords & text_tokens)
    return min(0.75, overlap / len(keywords))


def _asset_search_text(asset: CapabilityAsset) -> str:
    """拼接资产的名称、类型、来源和权限作为搜索文本。"""
    return normalize(" ".join([asset.name, asset.type, asset.source, *asset.permissions]))


def _extract_keywords(text: str) -> set[str]:
    """从文本中提取关键词（长度 >= 3 的词）。"""
    return {word for word in text.split() if len(word) >= 3}


def _score_matches(scored: list[tuple[CapabilityAsset, float]]) -> list[tuple[CapabilityAsset, float]]:
    """按匹配分数降序排列。"""
    return sorted(scored, key=lambda item: -item[1])


def _asset_list(assets: list[CapabilityAsset]) -> str:
    """将资产列表格式化为可读字符串。"""
    return ", ".join(f"{asset.name} ({asset.type})" for asset in assets)


def _deduplicate_resolutions(resolutions: list[CapabilityResolution]) -> list[CapabilityResolution]:
    """按 gap_id 去重，保留首次出现的解析结果。"""
    seen = set()
    result: list[CapabilityResolution] = []
    for r in resolutions:
        if r.gap_id in seen:
            continue
        seen.add(r.gap_id)
        result.append(r)
    return result
