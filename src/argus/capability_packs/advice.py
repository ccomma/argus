from __future__ import annotations

"""能力包建议模块。

提供 CapabilityPackAdvisor 类，用于检查当前资产清单是否满足
创建能力包所需的能力列表。输出缺失的能力建议和检测到的重复资产。
"""

from argus.assets import CapabilityAsset, find_potential_duplicates, normalize

from .models import CapabilityAdviceReport


class CapabilityPackAdvisor:
    """能力包建议器。

    在创建能力包之前，评估用户的资产清单是否覆盖了所需的能力项。
    例如，用户想创建一个"代码审查"能力包，但清单中缺少
    "code review" 技能，建议器会指出该缺失。
    """

    def advise(self, *, required_capabilities: list[str], assets: list[CapabilityAsset]) -> CapabilityAdviceReport:
        """评估资产是否满足所需能力。

        流程：
        1. 对每个资产提取搜索文本（名称 + 类型 + 来源 + 权限的归一化字符串）
        2. 对于每个所需能力，检查是否存在任一资产的搜索文本包含该能力关键词
        3. 收集未被满足的能力作为 missing_capabilities
        4. 同时检测资产列表中的潜在重复

        匹配策略：
        使用归一化后的子串包含匹配，而非精确匹配。例如
        required_capability "code review" 可以匹配资产 "code-review-skill"。
        """
        asset_terms = [_search_text(asset) for asset in assets]
        missing = [
            capability
            for capability in required_capabilities
            if not any(normalize(capability) in terms for terms in asset_terms)
        ]
        return CapabilityAdviceReport(
            missing_capabilities=missing,
            duplicate_asset_groups=find_potential_duplicates(assets),
        )


def _search_text(asset: CapabilityAsset) -> str:
    """构建资产的搜索文本。

    组合名称、类型、来源和权限列表，归一化后用于关键词匹配。
    包含权限列表可以匹配到如 "network" 等能力需求 ——
    如果用户要求 "network access" 能力，持有 network 权限的 MCP 服务器会被匹配。
    """
    return normalize(" ".join([asset.name, asset.type, asset.source, *asset.permissions]))
