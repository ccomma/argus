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
        snapshot = self.snapshot_manager.load(audit_record.snapshot_id)
        if snapshot is None:
            return ModificationResult(
                snapshot_id=audit_record.snapshot_id,
                outcome="failed",
                warnings=[f"Snapshot {audit_record.snapshot_id} not found."],
            )

        content = json.loads(snapshot.content_json)
        target = snapshot.subject_id

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

        elif snapshot.subject_type == "work_contract":
            original_contract = WorkContract.from_dict(content)
            self.contract_storage.save_contract(original_contract)

        else:
            return ModificationResult(
                snapshot_id=audit_record.snapshot_id,
                outcome="failed",
                warnings=[f"Unknown subject_type: {snapshot.subject_type}"],
            )

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
