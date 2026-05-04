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
        current = self._find_asset(asset_id)
        if current is None:
            return None
        snapshot = self.snapshot_manager.capture(
            subject_type="capability_asset",
            subject_id=asset_id,
            content=current.to_dict(),
            version_before=current.version,
            triggered_by=triggered_by,
            trigger_reason=trigger_reason,
        )
        modified = _modified_asset(current, new_status=new_status, new_metadata=new_metadata)
        assets = self.inventory.list_assets()
        updated = [modified if a.id == asset_id else a for a in assets]
        self.inventory.write(updated)

        diff = self.differ.diff_capability_asset(
            current, modified,
            version_before=current.version,
            version_after=f"{current.version}-modified",
        )
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
        current = self.contract_storage.load_contract(contract_id)
        if current is None:
            return None
        snapshot = self.snapshot_manager.capture(
            subject_type="work_contract",
            subject_id=contract_id,
            content=current.to_dict(),
            version_before=str(current.version),
            triggered_by=triggered_by,
            trigger_reason=trigger_reason,
        )
        modified = _modified_contract(current, field_updates or {})
        modified.version = current.version + 1
        modified.change_history.append(
            {
                "version": modified.version,
                "reason": trigger_reason,
                "triggered_by": triggered_by,
                "snapshot_id": snapshot.id,
            }
        )
        self.contract_storage.save_contract(modified)

        diff = self.differ.diff_work_contract(
            current, modified,
            version_before=str(current.version),
            version_after=str(modified.version),
        )
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
        record = self.audit_ledger.get_by_id(audit_record_id)
        if record is None:
            return ModificationResult(
                snapshot_id=audit_record_id,
                outcome="failed",
                warnings=[f"Audit record {audit_record_id} not found."],
            )
        return self.rollback_manager.rollback(record, reason)

    def list_audit_log(self) -> list[ModificationAuditRecord]:
        return self.audit_ledger.list_records()

    def write_report(self) -> ModificationReport:
        reporter = ModificationReporter(self.reports_dir)
        return reporter.write(self.audit_ledger.list_records())

    def _find_asset(self, asset_id: str) -> CapabilityAsset | None:
        for asset in self.inventory.list_assets():
            if asset.id == asset_id:
                return asset
        return None


def _modified_asset(
    asset: CapabilityAsset,
    new_status: str = "",
    new_metadata: dict[str, Any] | None = None,
) -> CapabilityAsset:
    data = asset.to_dict()
    if new_status:
        data["status"] = new_status
    if new_metadata is not None:
        data["metadata"] = {**(data.get("metadata") or {}), **new_metadata}
    return CapabilityAsset.from_dict(data)


def _modified_contract(
    contract: Any,
    field_updates: dict[str, Any],
) -> Any:
    data = contract.to_dict()
    for key, value in field_updates.items():
        if key in data:
            data[key] = value
    return type(contract).from_dict(data)
