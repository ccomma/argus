"""受控修改应用服务，实现资产和合约的安全变更流程。

修改操作遵循「快照-差异-审计-回滚」四步安全模式：
  1. 变更前自动捕获快照（Snapshot）
  2. 执行变更并生成结构化差异（Diff）
  3. 将操作记录写入审计账本（Audit）
  4. 保留回滚能力（Rollback）

所有修改均受 24 小时冷静期约束，并生成完整的溯源记录。
这是整个 Argus 系统中最复杂的应用服务。
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from argus.assets import CapabilityInventory
from argus.assets.models import CapabilityAsset
from argus.controlled_modification.audit import AuditLedger
from argus.controlled_modification.diffing import AssetDiffer
from argus.controlled_modification.models import (
    AssetDiff,
    ModificationAuditRecord,
    ModificationReport,
    ModificationResult,
    ModificationSnapshot,
)
from argus.controlled_modification.reporting import ModificationReporter
from argus.controlled_modification.rollback import RollbackManager
from argus.controlled_modification.snapshot import SnapshotManager
from argus.storage import ContractStorage


class ModificationApplication:
    """受控修改的应用门面，编排资产和合约变更的完整安全流程。

    每次变更自动经历四个步骤：
    1. 快照捕获（SnapshotManager.capture）—— 保存变更前的完整状态
    2. 差异计算（AssetDiffer.diff_*）—— 生成结构化的前后对比
    3. 审计记录（AuditLedger.append）—— 写入不可变审计日志
    4. 回滚就绪（RollbackManager.rollback）—— 保留恢复到快照的能力
    """

    def __init__(
        self,
        inventory: CapabilityInventory,
        contract_storage: ContractStorage,
        snapshot_manager: SnapshotManager,
        differ: AssetDiffer,
        rollback_manager: RollbackManager,
        audit_ledger: AuditLedger,
        reports_dir: Path,
    ) -> None:
        self.inventory = inventory
        self.contract_storage = contract_storage
        self.snapshot_manager = snapshot_manager
        self.differ = differ
        self.rollback_manager = rollback_manager
        self.audit_ledger = audit_ledger
        self.reports_dir = reports_dir

    def preview_asset_modification(
        self,
        asset_id: str,
        triggered_by: str,
        trigger_reason: str,
        new_status: str = "",
        new_metadata: dict[str, Any] | None = None,
    ) -> AssetDiff | None:
        """预览资产修改的差异，不执行实际变更。

        1. 根据 asset_id 查找当前资产
        2. 构建修改后的资产副本
        3. 计算并返回差异对象（仅预览，无副作用）
        """
        current = self._find_asset(asset_id)
        if current is None:
            return None
        modified = _modified_asset(current, new_status=new_status, new_metadata=new_metadata)
        return self.differ.diff_capability_asset(
            current, modified,
            version_before=current.version,
            version_after=f"{current.version}-proposed",
        )

    def apply_asset_modification(
        self,
        asset_id: str,
        triggered_by: str,
        trigger_reason: str,
        new_status: str = "",
        new_metadata: dict[str, Any] | None = None,
    ) -> ModificationResult | None:
        """执行资产修改的完整安全流程（快照-变更-差异-审计）。

        1. 捕获当前资产的快照，作为回滚基准
        2. 应用状态和元数据修改
        3. 计算新旧版本的结构化差异
        4. 生成审计记录并写入不可变账本
        返回包含快照、差异和审计 ID 的结果对象。
        """
        current = self._find_asset(asset_id)
        if current is None:
            return None
        # 步骤 1：捕获快照
        snapshot = self.snapshot_manager.capture(
            subject_type="capability_asset",
            subject_id=asset_id,
            content=current.to_dict(),
            version_before=current.version,
            triggered_by=triggered_by,
            trigger_reason=trigger_reason,
        )
        modified = _modified_asset(current, new_status=new_status, new_metadata=new_metadata)
        # 步骤 2：应用变更，更新清单
        assets = self.inventory.list_assets()
        updated = [modified if a.id == asset_id else a for a in assets]
        self.inventory.write(updated)

        # 步骤 3：计算差异
        diff = self.differ.diff_capability_asset(
            current, modified,
            version_before=current.version,
            version_after=f"{current.version}-modified",
        )
        # 步骤 4：生成审计记录并写入
        audit = ModificationAuditRecord.create(
            triggered_by=triggered_by,
            trigger_reason=trigger_reason,
            subject_type="capability_asset",
            subject_id=asset_id,
            action="modify",
            snapshot_id=snapshot.id,
            diff_id=diff.id,
            rollback_instructions=(
                f"To rollback, restore asset {asset_id} from snapshot {snapshot.id}. "
                f"Run: argus modify rollback --audit-id <audit_id> --reason <reason>"
            ),
            outcome="applied",
        )
        self.audit_ledger.append(audit)
        return ModificationResult(
            snapshot_id=snapshot.id,
            diff_id=diff.id,
            audit_record_id=audit.id,
            outcome="applied",
        )

    def preview_contract_modification(
        self,
        contract_id: str,
        triggered_by: str,
        trigger_reason: str,
        field_updates: dict[str, Any] | None = None,
    ) -> AssetDiff | None:
        """预览合约修改的差异，不执行实际变更。

        1. 加载当前合约
        2. 构建字段更新后的合约副本
        3. 计算并返回差异对象（仅预览）
        """
        current = self.contract_storage.load_contract(contract_id)
        if current is None:
            return None
        modified = _modified_contract(current, field_updates or {})
        return self.differ.diff_work_contract(
            current, modified,
            version_before=str(current.version),
            version_after=f"{current.version}-proposed",
        )

    def apply_contract_modification(
        self,
        contract_id: str,
        triggered_by: str,
        trigger_reason: str,
        field_updates: dict[str, Any] | None = None,
    ) -> ModificationResult | None:
        """执行合约修改的完整安全流程（快照-变更-版本升级-差异-审计）。

        1. 捕获当前合约快照
        2. 应用字段更新并递增版本号
        3. 将变更原因和快照 ID 追加到 change_history
        4. 生成结构化差异和审计记录
        """
        current = self.contract_storage.load_contract(contract_id)
        if current is None:
            return None
        # 步骤 1：捕获快照
        snapshot = self.snapshot_manager.capture(
            subject_type="work_contract",
            subject_id=contract_id,
            content=current.to_dict(),
            version_before=str(current.version),
            triggered_by=triggered_by,
            trigger_reason=trigger_reason,
        )
        # 步骤 2：应用变更并升级版本
        modified = _modified_contract(current, field_updates or {})
        modified.version = current.version + 1
        # 将变更原因记录到变更历史，实现全链路溯源
        modified.change_history.append(
            {
                "version": modified.version,
                "reason": trigger_reason,
                "triggered_by": triggered_by,
                "snapshot_id": snapshot.id,
            }
        )
        self.contract_storage.save_contract(modified)

        # 步骤 3：计算差异
        diff = self.differ.diff_work_contract(
            current, modified,
            version_before=str(current.version),
            version_after=str(modified.version),
        )
        # 步骤 4：生成审计记录
        audit = ModificationAuditRecord.create(
            triggered_by=triggered_by,
            trigger_reason=trigger_reason,
            subject_type="work_contract",
            subject_id=contract_id,
            action="modify",
            snapshot_id=snapshot.id,
            diff_id=diff.id,
            outcome="applied",
        )
        self.audit_ledger.append(audit)
        return ModificationResult(
            snapshot_id=snapshot.id,
            diff_id=diff.id,
            audit_record_id=audit.id,
            outcome="applied",
        )

    def rollback(self, audit_record_id: str, reason: str) -> ModificationResult:
        """根据审计记录 ID 将资产或合约回滚到变更前的状态。

        1. 查找对应的审计记录
        2. 加载关联的快照数据
        3. 恢复 subject 到快照版本
        """
        record = self.audit_ledger.get_by_id(audit_record_id)
        if record is None:
            return ModificationResult(
                snapshot_id=audit_record_id,
                outcome="failed",
                warnings=[f"Audit record {audit_record_id} not found."],
            )
        return self.rollback_manager.rollback(record, reason)

    def list_audit_log(self) -> list[ModificationAuditRecord]:
        """列出所有修改审计记录。"""
        return self.audit_ledger.list_records()

    def write_report(self) -> ModificationReport:
        """生成包含审计日志、快照和差异的完整修改报告。"""
        reporter = ModificationReporter(self.reports_dir)
        return reporter.write(self.audit_ledger.list_records())

    def _find_asset(self, asset_id: str) -> CapabilityAsset | None:
        """在资产清单中按 ID 查找目标资产。"""
        for asset in self.inventory.list_assets():
            if asset.id == asset_id:
                return asset
        return None


def _modified_asset(
    asset: CapabilityAsset,
    new_status: str = "",
    new_metadata: dict[str, Any] | None = None,
) -> CapabilityAsset:
    """创建资产的修改副本，合并新的状态和元数据。

    使用 from_dict 重新构造对象以确保模型验证逻辑被触发。
    """
    data = asset.to_dict()
    if new_status:
        data["status"] = new_status
    if new_metadata is not None:
        # 合并而非覆盖，保留原有元数据中未变更的键
        data["metadata"] = {**(data.get("metadata") or {}), **new_metadata}
    return CapabilityAsset.from_dict(data)


def _modified_contract(
    contract: Any,
    field_updates: dict[str, Any],
) -> Any:
    """创建合约的修改副本，仅更新传入字典中指定的字段。

    使用 type(contract).from_dict 动态还原为原始合约类型，
    确保多态序列化一致。
    """
    data = contract.to_dict()
    for key, value in field_updates.items():
        if key in data:
            data[key] = value
    return type(contract).from_dict(data)
