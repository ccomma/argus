from __future__ import annotations

from pathlib import Path

from argus.asset_models import AssetLearningLink, CapabilityAsset
from argus.asset_text import meaningful_tokens
from argus.learning import CandidateLearningItem


class CandidateAssetLinker:
    def link(self, learnings: list[CandidateLearningItem], assets: list[CapabilityAsset]) -> list[AssetLearningLink]:
        links: list[AssetLearningLink] = []
        for learning in learnings:
            learning_tokens = meaningful_tokens(
                " ".join([learning.summary, learning.type, learning.scope, learning.reverse_learning_target])
            )
            for asset in assets:
                asset_tokens = _asset_match_tokens(asset)
                matched = learning_tokens & asset_tokens
                if not matched:
                    continue
                links.append(
                    AssetLearningLink(
                        learning_id=learning.id,
                        asset_id=asset.id,
                        reason=f"matched tokens: {', '.join(sorted(matched))}",
                        confidence=min(0.9, 0.45 + 0.1 * len(matched)),
                    )
                )
        return links


def _asset_match_tokens(asset: CapabilityAsset) -> set[str]:
    metadata_text = " ".join(str(value) for value in asset.metadata.values())
    return meaningful_tokens(
        " ".join(
            [
                asset.name,
                Path(asset.install_path).stem,
                Path(asset.install_path).parent.name,
                " ".join(asset.permissions),
                metadata_text,
            ]
        )
    )
