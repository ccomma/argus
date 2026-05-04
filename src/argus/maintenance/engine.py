"""Maintenance engine for capability health checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from argus.assets import CapabilityInventory
from argus.assets.analysis import find_potential_conflicts, find_potential_duplicates
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.storage import ContractStorage


@dataclass(frozen=True)
class MaintenanceReport:
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
        assets = self.inventory.list_assets()

        # Detect duplicates
        duplicates = [
            {"asset_ids": [a.id for a in group], "names": [a.name for a in group]}
            for group in find_potential_duplicates(assets)
        ]

        # Detect conflicts
        conflicts = [
            {"asset_ids": [a.id for a in group], "names": [a.name for a in group]}
            for group in find_potential_conflicts(assets)
        ]

        # Find deprecated/archived assets
        deprecated = sorted(a.id for a in assets if a.status == "deprecated")
        archived = sorted(a.id for a in assets if a.status == "archived")

        # Find unused packs (packs not bound to any contract)
        all_packs = self.pack_store.list_latest()
        contracts = self.storage.list_contracts()
        bound_pack_ids = set()
        for c in contracts:
            if c.capability_pack_ref:
                bound_pack_ids.add(c.capability_pack_ref.split("@")[0])
        unused_packs = sorted(p.pack_id for p in all_packs if p.pack_id not in bound_pack_ids)

        # Find unused role packs (roles with no handoffs)
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
