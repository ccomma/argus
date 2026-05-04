from __future__ import annotations

"""学习项与资产关联模块。

提供 CandidateAssetLinker 类，通过文本 token 匹配自动建立
候选学习项与能力资产之间的关联。关联结果用于指导哪些资产
可以从特定学习经验中受益（如能力包改进、合约调整等）。
"""

from pathlib import Path

from argus.assets.models import AssetLearningLink, CapabilityAsset
from argus.assets.text import meaningful_tokens
from argus.ledger.learning import CandidateLearningItem


class CandidateAssetLinker:
    """候选学习项与资产的关联器。

    通过提取学习项和资产的有意义 token 集合，计算交集来建立关联。
    这种方法基于文本相似性，是一种轻量级但不完美的启发式匹配。
    """

    def link(self, learnings: list[CandidateLearningItem], assets: list[CapabilityAsset]) -> list[AssetLearningLink]:
        """建立学习项到资产的关联。

        流程：
        1. 对每个学习项，提取其有意义 token 集合（summary + type + scope + reverse_learning_target）
        2. 对每个资产，提取其匹配 token 集合（name + 路径 + 权限 + 元数据）
        3. 计算两个集合的交集
        4. 如果存在交集，创建关联记录，置信度基于交集大小
        5. 置信度公式：min(0.9, 0.45 + 0.1 * |交集|)

        例如，如果学习项提到 "question_strategy"，某个 skill 资产的
        metadata 中包含该词，则会被关联起来。

        Args:
            learnings: 候选学习项列表
            assets: 能力资产列表

        Returns:
            所有匹配到的学习-资产关联列表
        """
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
    """提取资产的有意义 token 用于匹配。

    组合来自多个来源的文本：资产名称、安装路径的 stem 和父目录名、
    权限列表以及所有元数据值。这样即使学习项中提到了路径名或权限名，
    也能成功匹配。
    """
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
