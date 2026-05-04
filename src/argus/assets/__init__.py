from __future__ import annotations

"""能力资产（Assets）子系统模块。

提供能力资产的扫描、清单管理、分析、学习链接和报告生成的全套能力。
资产是 Argus 系统中可被 AI 代理使用的能力单元，包括技能（skill）、
插件（plugin）、MCP 服务器、规则文件、脚本和记忆（memory）。
"""

from argus.assets.analysis import AssetAnalysis, AssetRiskCounts, analyze_assets, find_potential_conflicts, find_potential_duplicates
from argus.assets.inventory import CapabilityInventory
from argus.assets.linking import CandidateAssetLinker
from argus.assets.models import (
    ACTIVE,
    ARCHIVED,
    DEPRECATED,
    DISABLED,
    ISOLATED,
    AssetLearningLink,
    AssetReport,
    AssetScanProfile,
    AssetScanResult,
    CapabilityAsset,
    local_codex_asset_profile,
)
from argus.assets.reporting import AssetReporter
from argus.assets.scanning import CapabilityAssetScanner
from argus.assets.text import meaningful_tokens, normalize, tokens

__all__ = [
    "ACTIVE",
    "ARCHIVED",
    "AssetAnalysis",
    "AssetLearningLink",
    "AssetReport",
    "AssetReporter",
    "AssetRiskCounts",
    "AssetScanProfile",
    "AssetScanResult",
    "CandidateAssetLinker",
    "CapabilityAsset",
    "CapabilityAssetScanner",
    "CapabilityInventory",
    "DEPRECATED",
    "DISABLED",
    "ISOLATED",
    "analyze_assets",
    "find_potential_conflicts",
    "find_potential_duplicates",
    "local_codex_asset_profile",
    "meaningful_tokens",
    "normalize",
    "tokens",
]
