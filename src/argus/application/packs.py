from __future__ import annotations

from argus.assets import CapabilityInventory
from argus.capability_packs import (
    CapabilityAdviceReport,
    CapabilityPackAdvisor,
    CapabilityPackBinding,
    CapabilityPackBindingStore,
    CapabilityPackCheckReport,
    CapabilityPackChecker,
    CapabilityPackCreator,
    CapabilityPackManifest,
    CapabilityPackResult,
    CapabilityPackStore,
    RoleCapabilityPack,
    RolePackCheckReport,
    RolePackStore,
)
from argus.storage import ContractStorage


class CapabilityPackApplication:
    def __init__(
        self,
        inventory: CapabilityInventory,
        store: CapabilityPackStore,
        contract_storage: ContractStorage,
    ) -> None:
        self.inventory = inventory
        self.store = store
        self.contract_storage = contract_storage

    def propose(
        self,
        *,
        pack_id: str,
        display_name: str,
        required_asset_ids: list[str],
        optional_asset_ids: list[str],
        created_by: str,
        description: str = "",
    ) -> CapabilityPackResult:
        return CapabilityPackCreator(self.store).propose(
            pack_id=pack_id,
            display_name=display_name,
            required_asset_ids=required_asset_ids,
            optional_asset_ids=optional_asset_ids,
            assets=self.inventory.list_assets(),
            created_by=created_by,
            description=description,
        )

    def create(
        self,
        *,
        pack_id: str,
        display_name: str,
        required_asset_ids: list[str],
        optional_asset_ids: list[str],
        created_by: str,
        description: str = "",
    ) -> CapabilityPackResult:
        return CapabilityPackCreator(self.store).create(
            pack_id=pack_id,
            display_name=display_name,
            required_asset_ids=required_asset_ids,
            optional_asset_ids=optional_asset_ids,
            assets=self.inventory.list_assets(),
            created_by=created_by,
            description=description,
        )

    def inspect(self, pack_id: str, version: int | None = None) -> tuple[CapabilityPackManifest, str]:
        return self.store.load(pack_id, version)

    def check(self, pack_id: str, version: int | None = None) -> CapabilityPackCheckReport:
        manifest, _ = self.store.load(pack_id, version)
        return CapabilityPackChecker().check(manifest, self.inventory.list_assets())

    def bind_contract(self, contract_id: str, pack_id: str, rationale: str, version: int | None = None) -> CapabilityPackBinding:
        manifest, hash_value = self.store.load(pack_id, version)
        return CapabilityPackBindingStore(self.contract_storage).bind(
            contract_id=contract_id,
            pack=manifest,
            content_hash=hash_value,
            rationale=rationale,
        )

    def advise(self, required_capabilities: list[str]) -> CapabilityAdviceReport:
        return CapabilityPackAdvisor().advise(
            required_capabilities=required_capabilities,
            assets=self.inventory.list_assets(),
        )


class RolePackApplication:
    def __init__(
        self,
        inventory: CapabilityInventory,
        role_store: RolePackStore,
    ) -> None:
        self.inventory = inventory
        self.role_store = role_store

    def create(
        self,
        *,
        role_id: str,
        display_name: str,
        required_pack_ids: list[str],
        optional_pack_ids: list[str],
        created_by: str,
    ) -> RoleCapabilityPack:
        return self.role_store.create(
            role_id=role_id,
            display_name=display_name,
            required_pack_ids=required_pack_ids,
            optional_pack_ids=optional_pack_ids,
            created_by=created_by,
        )

    def inspect(self, role_id: str, version: int | None = None) -> RoleCapabilityPack:
        return self.role_store.load(role_id, version)

    def check(self, role_id: str, version: int | None = None) -> RolePackCheckReport:
        return self.role_store.check(role_id, self.inventory.list_assets(), version)
