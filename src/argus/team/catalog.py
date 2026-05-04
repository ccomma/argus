"""团队能力编目 - 聚合团队共享的合约/角色/能力包/模板，支持持久化和统计。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from argus.assets import CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.storage import ContractStorage


@dataclass
class TeamCatalog:
    """团队能力编目：聚合团队共享的合约、角色、能力包、资产和模板引用，不实际存储数据。"""
    team_id: str
    contract_ids: list[str] = field(default_factory=list)
    role_ids: list[str] = field(default_factory=list)
    pack_ids: list[str] = field(default_factory=list)
    capability_ids: list[str] = field(default_factory=list)
    shared_templates: list[dict[str, Any]] = field(default_factory=list)

    def add_contract(self, contract_id: str) -> None:
        if contract_id not in self.contract_ids:
            self.contract_ids.append(contract_id)

    def add_role(self, role_id: str) -> None:
        if role_id not in self.role_ids:
            self.role_ids.append(role_id)

    def add_pack(self, pack_id: str) -> None:
        if pack_id not in self.pack_ids:
            self.pack_ids.append(pack_id)

    def add_template(self, name: str, content: dict[str, Any]) -> None:
        for t in self.shared_templates:
            if t["name"] == name:
                t["content"] = content
                return
        self.shared_templates.append({"name": name, "content": content})

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "contract_ids": self.contract_ids,
            "role_ids": self.role_ids,
            "pack_ids": self.pack_ids,
            "capability_ids": self.capability_ids,
            "shared_templates": self.shared_templates,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TeamCatalog:
        return cls(
            team_id=data["team_id"],
            contract_ids=data.get("contract_ids", []),
            role_ids=data.get("role_ids", []),
            pack_ids=data.get("pack_ids", []),
            capability_ids=data.get("capability_ids", []),
            shared_templates=data.get("shared_templates", []),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> TeamCatalog:
        if path.exists():
            return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
        return cls(team_id=path.stem)


class TeamCatalogManager:
    """编目管理器：管理多个团队编目的 JSON 文件存储、加载和统计计算。

    职责：
    1. save/load/list_all 管理编目文件
    2. compute_stats 汇总指定团队的合约/角色/包/资产/模板计数
    """

    def __init__(self, store_dir: Path) -> None:
        self.store_dir = Path(store_dir)

    def save(self, catalog: TeamCatalog) -> None:
        catalog.save(self.store_dir / f"{catalog.team_id}.json")

    def load(self, team_id: str) -> TeamCatalog:
        return TeamCatalog.load(self.store_dir / f"{team_id}.json")

    def list_all(self) -> list[TeamCatalog]:
        if not self.store_dir.exists():
            return []
        results = []
        for f in sorted(self.store_dir.glob("*.json")):
            results.append(TeamCatalog.from_dict(json.loads(f.read_text(encoding="utf-8"))))
        return results

    def compute_stats(
        self,
        team_id: str,
        storage: ContractStorage,
        inventory: CapabilityInventory,
        pack_store: CapabilityPackStore,
        role_store: RolePackStore,
    ) -> dict[str, Any]:
        """统计团队编目覆盖情况：计算各维度（合约/角色/包/资产/模板）的数量。

        1. 加载团队编目
        2. 过滤全局列表，仅保留编目中引用的条目
        3. 返回各维度计数
        """
        catalog = self.load(team_id)
        contracts = storage.list_contracts()
        team_contracts = [c.to_dict() for c in contracts if c.contract_id in catalog.contract_ids]
        roles = role_store.list_latest()
        team_roles = [r.to_dict() for r in roles if r.role_id in catalog.role_ids]
        packs = pack_store.list_latest()
        team_packs = [p.to_dict() for p in packs if p.pack_id in catalog.pack_ids]
        assets = inventory.list_assets()
        team_assets = [a.to_dict() for a in assets if a.id in catalog.capability_ids]
        return {
            "team_id": team_id,
            "contracts": len(team_contracts),
            "roles": len(team_roles),
            "packs": len(team_packs),
            "capabilities": len(team_assets),
            "templates": len(catalog.shared_templates),
        }
