"""维护引擎，对资产和能力包进行全面的健康检查。

检测六类问题：
  1. 重复资产（duplicates）—— 属于同一资产族的重复定义
  2. 冲突资产（conflicts）—— 同族中相互冲突的定义
  3. 废弃资产（deprecated_assets）—— 标记为 deprecated 的资产
  4. 归档资产（archived_assets）—— 标记为 archived 的资产
  5. 未使用的能力包（unused_capability_packs）—— 未绑定到任何合约的包
  6. 未使用的角色包（unused_role_packs）—— 无交接记录的角色
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from argus.assets import CapabilityInventory
from argus.assets.analysis import find_potential_conflicts, find_potential_duplicates
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.storage import ContractStorage


@dataclass(frozen=True)
class MaintenanceReport:
    """维护检查报告，列出六类问题清单和摘要统计。

    所有检测项均在一轮 run() 中完成，保证数据快照的一致性。
    """
    duplicates: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    deprecated_assets: list[str] = field(default_factory=list)
    archived_assets: list[str] = field(default_factory=list)
    unused_capability_packs: list[str] = field(default_factory=list)
    unused_role_packs: list[str] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "duplicates": self.duplicates,
            "conflicts": self.conflicts,
            "deprecated_assets": self.deprecated_assets,
            "archived_assets": self.archived_assets,
            "unused_capability_packs": self.unused_capability_packs,
            "unused_role_packs": self.unused_role_packs,
            "summary": self.summary,
        }


class MaintenanceEngine:
    """维护检查引擎，对资产和能力包进行综合健康扫描。

    需要注入四个数据源：资产清单、能力包存储、角色包存储和合约存储。
    """

    def __init__(
        self,
        inventory: CapabilityInventory,
        pack_store: CapabilityPackStore,
        role_store: RolePackStore,
        storage: ContractStorage,
    ) -> None:
        self.inventory = inventory
        self.pack_store = pack_store
        self.role_store = role_store
        self.storage = storage

    def run(self) -> MaintenanceReport:
        """执行全量健康检查，返回 MaintenanceReport。

        1. 检测资产重复和冲突（通过资产分析函数）
        2. 标记废弃/归档资产
        3. 找出未绑定到合约的能力包（通过遍历合约的 capability_pack_ref）
        4. 列出所有角色包（当前实现中全部视为未使用，标记供人工审查）
        5. 生成摘要统计
        """
        assets = self.inventory.list_assets()

        # 检测重复资产：同一资产族中名称/能力高度重合的定义
        duplicates = [
            {"asset_ids": [a.id for a in group], "names": [a.name for a in group]}
            for group in find_potential_duplicates(assets)
        ]

        # 检测冲突资产：同族中相互矛盾的定义
        conflicts = [
            {"asset_ids": [a.id for a in group], "names": [a.name for a in group]}
            for group in find_potential_conflicts(assets)
        ]

        # 标记已弃用和已归档的资产
        deprecated = sorted(a.id for a in assets if a.status == "deprecated")
        archived = sorted(a.id for a in assets if a.status == "archived")

        # 检测未绑定到任何合约的能力包
        all_packs = self.pack_store.list_latest()
        contracts = self.storage.list_contracts()
        bound_pack_ids = set()
        for c in contracts:
            if c.capability_pack_ref:
                # capability_pack_ref 格式为 "pack_id@version"，取 @ 前的 pack_id
                bound_pack_ids.add(c.capability_pack_ref.split("@")[0])
        unused_packs = sorted(p.pack_id for p in all_packs if p.pack_id not in bound_pack_ids)

        # 检测未使用的角色包（当前将所有角色标记为待审查）
        all_roles = self.role_store.list_latest()
        unused_roles = sorted(r.role_id for r in all_roles)

        summary = {
            "total_assets": len(assets),
            "duplicates": len(duplicates),
            "conflicts": len(conflicts),
            "deprecated": len(deprecated),
            "archived": len(archived),
            "unused_packs": len(unused_packs),
            "unused_roles": len(unused_roles),
        }
        return MaintenanceReport(
            duplicates=duplicates,
            conflicts=conflicts,
            deprecated_assets=deprecated,
            archived_assets=archived,
            unused_capability_packs=unused_packs,
            unused_role_packs=unused_roles,
            summary=summary,
        )
