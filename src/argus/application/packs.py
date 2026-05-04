"""能力包和角色包的应用服务，编排创建、检查、绑定和咨询流程。

能力包（CapabilityPack）将多个能力资产组合为一个可分配的单元；
角色包（RolePack）将多个能力包组合为角色定义。此模块提供两套应用门面。
"""

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
    """能力包的应用门面，提供创建、检查、合约绑定和咨询功能。"""

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
        """对提议的能力包组合进行验证（不实际创建），返回可行性结果。"""
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
        """创建并持久化一个新的能力包。

        1. 验证所有引用的资产在清单中存在且可用
        2. 将必选和可选资产打包为能力包清单（manifest）
        3. 持久化到包存储中
        """
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
        """查看指定能力包的清单内容及其内容哈希。"""
        return self.store.load(pack_id, version)

    def check(self, pack_id: str, version: int | None = None) -> CapabilityPackCheckReport:
        """对能力包进行完整性检查，验证引用的资产是否均存在且状态正常。"""
        manifest, _ = self.store.load(pack_id, version)
        return CapabilityPackChecker().check(manifest, self.inventory.list_assets())

    def bind_contract(self, contract_id: str, pack_id: str, rationale: str, version: int | None = None) -> CapabilityPackBinding:
        """将能力包绑定到工作合约，建立「合约-能力」的溯源关系。"""
        manifest, hash_value = self.store.load(pack_id, version)
        return CapabilityPackBindingStore(self.contract_storage).bind(
            contract_id=contract_id,
            pack=manifest,
            content_hash=hash_value,
            rationale=rationale,
        )

    def advise(self, required_capabilities: list[str]) -> CapabilityAdviceReport:
        """根据需求能力列表，从现有资产中推荐合适的能力包组合。"""
        return CapabilityPackAdvisor().advise(
            required_capabilities=required_capabilities,
            assets=self.inventory.list_assets(),
        )


class RolePackApplication:
    """角色包的应用门面，将多个能力包组合为角色定义并验证其完整性。"""

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
        """创建并持久化一个角色能力包，组合必选和可选的能力包。

        1. 验证引用的能力包 ID 是否存在
        2. 组装为角色能力包（RoleCapabilityPack）
        3. 持久化到角色包存储中
        """
        return self.role_store.create(
            role_id=role_id,
            display_name=display_name,
            required_pack_ids=required_pack_ids,
            optional_pack_ids=optional_pack_ids,
            created_by=created_by,
        )

    def inspect(self, role_id: str, version: int | None = None) -> RoleCapabilityPack:
        """查看指定角色包的定义内容。"""
        return self.role_store.load(role_id, version)

    def check(self, role_id: str, version: int | None = None) -> RolePackCheckReport:
        """对角色包进行完整性检查，验证其引用的能力包和资产是否均有效。"""
        return self.role_store.check(role_id, self.inventory.list_assets(), version)
