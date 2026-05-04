from __future__ import annotations

"""能力包完整性检查模块。

提供 CapabilityPackChecker 类，验证能力包清单中的资产是否仍然有效。
核心概念是"漂移检测"（drift detection）——比较资产快照与当前
资产状态，发现缺失、修改或过时的资产条目。
"""

from argus.assets import CapabilityAsset

from .models import CapabilityPackCheckReport, CapabilityPackEntry, CapabilityPackManifest
from .risk import aggregate_risk
from .serialization import asset_snapshot_hash, content_hash


class CapabilityPackChecker:
    """能力包完整性检查器。

    接收一个能力包清单和当前的资产列表，逐条验证每个资产条目
    （CapabilityPackEntry）是否仍然有效。
    """

    def check(self, manifest: CapabilityPackManifest, assets: list[CapabilityAsset]) -> CapabilityPackCheckReport:
        """检查能力包的完整性。

        流程：
        1. 将当前资产列表转为 {id: asset} 查找表
        2. 逐条检查清单中的每个资产条目：
           a. 如果资产 ID 在当前列表中不存在 → 必要资产记为 missing，可选资产跳过
           b. 如果资产的快照哈希与当前哈希不一致 → 必要资产记为 drifted，可选资产跳过
           c. 如果以上检查通过 → 加入 current_entries（用于风险重算）
        3. 基于当前有效的条目重新计算聚合风险
        4. complete 为 True 当且仅当不存在缺失或漂移的必要资产

        漂移检测的关键在于 asset_snapshot_hash：该哈希基于资产的完整字典
        计算（包括 permissions、risk_score 等），任何属性的变化都会导致哈希不同。
        """
        current_assets = {asset.id: asset for asset in assets}
        missing_required: list[str] = []
        drifted_required: list[str] = []
        drifted_optional: list[str] = []
        current_entries: list[CapabilityPackEntry] = []
        for entry in manifest.entries:
            asset = current_assets.get(entry.asset_id)
            if asset is None:
                if entry.required:
                    missing_required.append(entry.entry_id)
                continue
            if asset_snapshot_hash(asset) != entry.asset_snapshot_hash:
                if entry.required:
                    drifted_required.append(entry.entry_id)
                else:
                    drifted_optional.append(entry.entry_id)
                    continue
            current_entries.append(entry)
        risk = aggregate_risk(current_entries)
        return CapabilityPackCheckReport(
            pack_id=manifest.pack_id,
            version=manifest.version,
            complete=not missing_required and not drifted_required,
            content_hash=content_hash(manifest),
            missing_required_entry_ids=missing_required,
            drifted_required_entry_ids=drifted_required,
            drifted_optional_entry_ids=drifted_optional,
            current_aggregate_risk_tier=risk.tier,
            current_aggregate_risk_reason=risk.reason,
        )
