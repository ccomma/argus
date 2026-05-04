"""回滚管理器，将资产或合约恢复到指定快照的状态。

回滚本身也会生成审计记录（action="rollback"），形成闭环溯源。
"""

from __future__ import annotations

import json

from argus.assets import CapabilityInventory
from argus.assets.models import CapabilityAsset
from argus.contracts.models import WorkContract
from argus.storage import ContractStorage

from .audit import AuditLedger
from .models import ModificationAuditRecord, ModificationResult
from .snapshot import SnapshotManager


class RollbackManager:
    """回滚管理器，根据审计记录中引用的快照恢复 subject 状态。

    回滚流程：
    1. 从审计记录加载对应的快照
    2. 根据 subject_type 选择恢复策略（资产 vs 合约）
    3. 恢复状态并写回对应的存储
    4. 生成一条 rollback 审计记录，形成完整的事后溯源
    """

    def __init__(
        self,
        snapshot_manager: SnapshotManager,
        inventory: CapabilityInventory,
        contract_storage: ContractStorage,
        audit_ledger: AuditLedger,
    ) -> None:
        self.snapshot_manager = snapshot_manager
        self.inventory = inventory
        self.contract_storage = contract_storage
        self.audit_ledger = audit_ledger

    def rollback(self, audit_record: ModificationAuditRecord, reason: str) -> ModificationResult:
        """执行回滚操作。

        1. 加载审计记录中引用的快照
        2. 从快照的 content_json 反序列化原始状态对象
        3. 根据 subject_type 分派到资产恢复或合约恢复逻辑
        4. 生成回滚审计记录并写入审计账本
        """
        snapshot = self.snapshot_manager.load(audit_record.snapshot_id)
        if snapshot is None:
            return ModificationResult(
                snapshot_id=audit_record.snapshot_id,
                outcome="failed",
                warnings=[f"Snapshot {audit_record.snapshot_id} not found."],
            )

        content = json.loads(snapshot.content_json)
        target = snapshot.subject_id

        # 资产回滚：用快照版本恢复清单中的指定资产
        if snapshot.subject_type == "capability_asset":
            original_asset = CapabilityAsset.from_dict(content)
            current = self.inventory.list_assets()
            updated = [original_asset if a.id == target else a for a in current]
            if not any(a.id == target for a in current):
                return ModificationResult(
                    snapshot_id=audit_record.snapshot_id,
                    outcome="failed",
                    warnings=[f"Asset {target} not found in inventory."],
                )
            self.inventory.write(updated)

        # 合约回滚：直接覆写合约存储中的当前版本
        elif snapshot.subject_type == "work_contract":
            original_contract = WorkContract.from_dict(content)
            self.contract_storage.save_contract(original_contract)

        else:
            return ModificationResult(
                snapshot_id=audit_record.snapshot_id,
                outcome="failed",
                warnings=[f"Unknown subject_type: {snapshot.subject_type}"],
            )

        # 回滚操作本身也是一种修改，必须产生审计记录
        rollback_audit = ModificationAuditRecord.create(
            triggered_by="rollback",
            trigger_reason=reason,
            subject_type=snapshot.subject_type,
            subject_id=target,
            action="rollback",
            snapshot_id=audit_record.snapshot_id,
            rollback_instructions=f"Reverted to snapshot {audit_record.snapshot_id}. "
            f"Previous action: {audit_record.action} triggered by {audit_record.triggered_by}.",
            outcome="applied",
        )
        self.audit_ledger.append(rollback_audit)
        return ModificationResult(
            snapshot_id=audit_record.snapshot_id,
            audit_record_id=rollback_audit.id,
            outcome="applied",
        )
