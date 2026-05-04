from __future__ import annotations

from argus.assets import CapabilityAsset, CapabilityInventory, analyze_assets, normalize
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.governance import GovernanceFinding
from argus.ledger import CandidateLearningItem

from .models import DECISION_RISK, CapabilityResolution, Decision


class CapabilityResolver:
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
    gap_norm = normalize(gap_description)
    keywords = _extract_keywords(gap_norm)

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
    asset_tokens = set(normalize(asset.name).split()) | {asset.type}
    return bool(asset_tokens & gap_keywords) and len(asset_tokens & gap_keywords) >= len(asset_tokens) * 0.5


_CONFIGURE_THRESHOLD = 0.15


def _scored_matches(assets: list[CapabilityAsset], keywords: set[str]) -> list[tuple[CapabilityAsset, float]]:
    results = [(asset, _keyword_overlap(asset, keywords)) for asset in assets]
    scored = [(asset, score) for asset, score in results if score >= _CONFIGURE_THRESHOLD]
    return sorted(scored, key=lambda item: -item[1])


def _find_similar(assets: list[CapabilityAsset], keywords: set[str]) -> list[CapabilityAsset]:
    results: list[CapabilityAsset] = []
    for asset in assets:
        score = _keyword_overlap(asset, keywords)
        if 0.0 < score < _CONFIGURE_THRESHOLD:
            results.append(asset)
    return results[:3]


def _keyword_overlap(asset: CapabilityAsset, keywords: set[str]) -> float:
    text = _asset_search_text(asset)
    if not text or not keywords:
        return 0.0
    text_tokens = set(text.split())
    overlap = len(keywords & text_tokens)
    return min(0.75, overlap / len(keywords))


def _asset_search_text(asset: CapabilityAsset) -> str:
    return normalize(" ".join([asset.name, asset.type, asset.source, *asset.permissions]))


def _extract_keywords(text: str) -> set[str]:
    return {word for word in text.split() if len(word) >= 3}


def _score_matches(scored: list[tuple[CapabilityAsset, float]]) -> list[tuple[CapabilityAsset, float]]:
    return sorted(scored, key=lambda item: -item[1])


def _asset_list(assets: list[CapabilityAsset]) -> str:
    return ", ".join(f"{asset.name} ({asset.type})" for asset in assets)


def _deduplicate_resolutions(resolutions: list[CapabilityResolution]) -> list[CapabilityResolution]:
    seen = set()
    result: list[CapabilityResolution] = []
    for r in resolutions:
        if r.gap_id in seen:
            continue
        seen.add(r.gap_id)
        result.append(r)
    return result
