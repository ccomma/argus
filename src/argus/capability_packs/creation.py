from __future__ import annotations

"""能力包创建模块。

提供 CapabilityPackCreator 类和 build_manifest 函数，
用于根据资产清单创建能力包。支持"提议"（propose，不持久化）
和"创建"（create，持久化到存储）两种模式。
"""

from time import time
from typing import TYPE_CHECKING

from argus.assets import CapabilityAsset

from .models import (
    MANIFEST_SCHEMA_VERSION,
    RISK_POLICY_VERSION,
    CapabilityPackEntry,
    CapabilityPackManifest,
    CapabilityPackResult,
)
from .risk import aggregate_risk, highest_risk_entry_ids, infer_risk, reason_codes_for_asset
from .serialization import asset_snapshot_hash, content_hash

if TYPE_CHECKING:
    from .stores import CapabilityPackStore


class CapabilityPackCreator:
    """能力包创建器。

    负责根据指定的必要/可选资产 ID 从资产清单中选择资产，
    组装为能力包清单。支持版本递增和持久化。
    """

    def __init__(self, store: CapabilityPackStore | None = None) -> None:
        """初始化创建器。

        Args:
            store: 能力包存储，为 None 时只能提议不能创建（不持久化）
        """
        self.store = store

    def propose(
        self,
        *,
        pack_id: str,
        display_name: str,
        required_asset_ids: list[str],
        optional_asset_ids: list[str],
        assets: list[CapabilityAsset],
        created_by: str,
        description: str = "",
    ) -> CapabilityPackResult:
        """提议一个能力包（不持久化）。

        用于让用户预览能力包内容而不实际写入存储。
        版本号由存储的 next_version() 自动确定。
        """
        version = self.store.next_version(pack_id) if self.store else 1
        manifest = build_manifest(
            pack_id=pack_id,
            version=version,
            display_name=display_name,
            required_asset_ids=required_asset_ids,
            optional_asset_ids=optional_asset_ids,
            assets=assets,
            created_by=created_by,
            description=description,
        )
        return CapabilityPackResult(manifest=manifest, content_hash=content_hash(manifest), path=None)

    def create(
        self,
        *,
        pack_id: str,
        display_name: str,
        required_asset_ids: list[str],
        optional_asset_ids: list[str],
        assets: list[CapabilityAsset],
        created_by: str,
        description: str = "",
    ) -> CapabilityPackResult:
        """创建一个能力包并持久化到存储。

        流程：
        1. 检查必须指定 store，否则抛出异常
        2. 调用 propose() 生成清单
        3. 将清单写入存储
        4. 返回包含持久化路径的结果
        """
        if not self.store:
            raise ValueError("capability pack store is required to create manifests")
        result = self.propose(
            pack_id=pack_id,
            display_name=display_name,
            required_asset_ids=required_asset_ids,
            optional_asset_ids=optional_asset_ids,
            assets=assets,
            created_by=created_by,
            description=description,
        )
        path = self.store.write(result.manifest)
        return CapabilityPackResult(manifest=result.manifest, content_hash=result.content_hash, path=path)


def build_manifest(
    *,
    pack_id: str,
    version: int,
    display_name: str,
    required_asset_ids: list[str],
    optional_asset_ids: list[str],
    assets: list[CapabilityAsset],
    created_by: str,
    description: str,
) -> CapabilityPackManifest:
    """构建能力包清单。

    流程：
    1. 将资产列表转为 {id: asset} 的查找表，便于 O(1) 取值
    2. 先处理必要资产，再处理可选资产，为每个资产生成条目
    3. 对不存在的资产 ID 抛出明确错误（通过 require_asset）
    4. 计算所有条目的聚合风险
    5. 组装完整的 CapabilityPackManifest 对象

    supersedes_version 逻辑：仅当 version > 1 时设置为 version - 1，
    表示该版本取代上一版本。
    """
    by_id = {asset.id: asset for asset in assets}
    entries: list[CapabilityPackEntry] = []
    for asset_id in required_asset_ids:
        entries.append(entry_from_asset(pack_id, require_asset(by_id, asset_id), required=True))
    for asset_id in optional_asset_ids:
        entries.append(entry_from_asset(pack_id, require_asset(by_id, asset_id), required=False))
    risk = aggregate_risk(entries)
    return CapabilityPackManifest(
        manifest_schema_version=MANIFEST_SCHEMA_VERSION,
        pack_id=pack_id,
        version=version,
        display_name=display_name,
        entries=entries,
        aggregate_risk_tier_snapshot=risk.tier,
        aggregate_risk_reason_snapshot=risk.reason,
        aggregate_reason_codes_snapshot=risk.reason_codes,
        aggregate_contributing_entry_ids_snapshot=highest_risk_entry_ids(entries, risk.tier),
        risk_policy_version=RISK_POLICY_VERSION,
        created_at=int(time()),
        created_by=created_by,
        description=description,
        supersedes_version=version - 1 if version > 1 else None,
    )


def entry_from_asset(pack_id: str, asset: CapabilityAsset, *, required: bool) -> CapabilityPackEntry:
    """从单个资产创建能力包条目。

    快照化以下内容以便后续漂移检测：
    - 资产的基本信息（类型、名称、来源、版本、路径）
    - 权限列表
    - 资产的当前 SHA256 哈希（用于检测文件内容变更）
    - 风险推断结果（等级和原因代码）

    primary_purpose 由 purpose_for_asset() 推断。
    """
    primary_purpose = purpose_for_asset(asset)
    reason_codes = reason_codes_for_asset(asset)
    risk = infer_risk(reason_codes)
    return CapabilityPackEntry(
        entry_id=f"{pack_id}-{asset.id}-{primary_purpose}",
        asset_id=asset.id,
        required=required,
        primary_purpose=primary_purpose,
        secondary_purposes=[],
        selection_rationale=f"Selected {asset.name} for {primary_purpose}.",
        asset_type_snapshot=asset.type,
        asset_name_snapshot=asset.name,
        source_snapshot=asset.source,
        version_snapshot=asset.version,
        install_path_snapshot=asset.install_path,
        permissions_snapshot=asset.permissions,
        asset_snapshot_hash=asset_snapshot_hash(asset),
        inferred_reason_codes_snapshot=reason_codes,
        risk_tier_snapshot=risk.tier,
        risk_reason_snapshot=risk.reason,
    )


def purpose_for_asset(asset: CapabilityAsset) -> str:
    """根据资产类型推断其主要用途。

    映射规则：
    - rule → governance（规则文件用于治理）
    - memory → memory（记忆文件用于持久化上下文）
    - script → implementation（脚本用于实现）
    - mcp_server → browser_automation 或 implementation（根据名称判断）
    - 其他 → implementation（默认）
    """
    if asset.type == "rule":
        return "governance"
    if asset.type == "memory":
        return "memory"
    if asset.type == "script":
        return "implementation"
    if asset.type == "mcp_server":
        return "browser_automation" if "browser" in asset.name.lower() else "implementation"
    return "implementation"


def require_asset(assets: dict[str, CapabilityAsset], asset_id: str) -> CapabilityAsset:
    """从资产查找表中获取指定 ID 的资产，不存在时抛出明确的错误信息。"""
    try:
        return assets[asset_id]
    except KeyError as exc:
        raise ValueError(f"asset not found in inventory: {asset_id}") from exc
