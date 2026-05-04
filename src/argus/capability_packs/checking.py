from __future__ import annotations

from argus.assets import CapabilityAsset

from .models import CapabilityPackCheckReport, CapabilityPackEntry, CapabilityPackManifest
from .risk import aggregate_risk
from .serialization import asset_snapshot_hash, content_hash


class CapabilityPackChecker:
    def check(self, manifest: CapabilityPackManifest, assets: list[CapabilityAsset]) -> CapabilityPackCheckReport:
        current_assets = {asset.id: asset for asset in assets}
        missing_required: list[str] = []
        drifted_required: list[str] = []
        drifted_optional: list[str] = []
        current_entries: list[CapabilityPackEntry] = []
        for entry in manifest.entries:
            asset = current_assets.get(entry.asset_id)
            if asset is None:
                if entry.required:
                    missing_required.append(entry.entry_id)
                continue
            if asset_snapshot_hash(asset) != entry.asset_snapshot_hash:
                if entry.required:
                    drifted_required.append(entry.entry_id)
                else:
                    drifted_optional.append(entry.entry_id)
                    continue
            current_entries.append(entry)
        risk = aggregate_risk(current_entries)
        return CapabilityPackCheckReport(
            pack_id=manifest.pack_id,
            version=manifest.version,
            complete=not missing_required and not drifted_required,
            content_hash=content_hash(manifest),
            missing_required_entry_ids=missing_required,
            drifted_required_entry_ids=drifted_required,
            drifted_optional_entry_ids=drifted_optional,
            current_aggregate_risk_tier=risk.tier,
            current_aggregate_risk_reason=risk.reason,
        )
