from __future__ import annotations

from time import time
from typing import TYPE_CHECKING

from argus.assets import CapabilityAsset

from .models import (
    MANIFEST_SCHEMA_VERSION,
    RISK_POLICY_VERSION,
    CapabilityPackEntry,
    CapabilityPackManifest,
    CapabilityPackResult,
)
from .risk import aggregate_risk, highest_risk_entry_ids, infer_risk, reason_codes_for_asset
from .serialization import asset_snapshot_hash, content_hash

if TYPE_CHECKING:
    from .stores import CapabilityPackStore


class CapabilityPackCreator:
    def __init__(self, store: CapabilityPackStore | None = None) -> None:
        self.store = store

    def propose(
        self,
        *,
        pack_id: str,
        display_name: str,
        required_asset_ids: list[str],
        optional_asset_ids: list[str],
        assets: list[CapabilityAsset],
        created_by: str,
        description: str = "",
    ) -> CapabilityPackResult:
        version = self.store.next_version(pack_id) if self.store else 1
        manifest = build_manifest(
            pack_id=pack_id,
            version=version,
            display_name=display_name,
            required_asset_ids=required_asset_ids,
            optional_asset_ids=optional_asset_ids,
            assets=assets,
            created_by=created_by,
            description=description,
        )
        return CapabilityPackResult(manifest=manifest, content_hash=content_hash(manifest), path=None)

    def create(
        self,
        *,
        pack_id: str,
        display_name: str,
        required_asset_ids: list[str],
        optional_asset_ids: list[str],
        assets: list[CapabilityAsset],
        created_by: str,
        description: str = "",
    ) -> CapabilityPackResult:
        if not self.store:
            raise ValueError("capability pack store is required to create manifests")
        result = self.propose(
            pack_id=pack_id,
            display_name=display_name,
            required_asset_ids=required_asset_ids,
            optional_asset_ids=optional_asset_ids,
            assets=assets,
            created_by=created_by,
            description=description,
        )
        path = self.store.write(result.manifest)
        return CapabilityPackResult(manifest=result.manifest, content_hash=result.content_hash, path=path)


def build_manifest(
    *,
    pack_id: str,
    version: int,
    display_name: str,
    required_asset_ids: list[str],
    optional_asset_ids: list[str],
    assets: list[CapabilityAsset],
    created_by: str,
    description: str,
) -> CapabilityPackManifest:
    by_id = {asset.id: asset for asset in assets}
    entries: list[CapabilityPackEntry] = []
    for asset_id in required_asset_ids:
        entries.append(entry_from_asset(pack_id, require_asset(by_id, asset_id), required=True))
    for asset_id in optional_asset_ids:
        entries.append(entry_from_asset(pack_id, require_asset(by_id, asset_id), required=False))
    risk = aggregate_risk(entries)
    return CapabilityPackManifest(
        manifest_schema_version=MANIFEST_SCHEMA_VERSION,
        pack_id=pack_id,
        version=version,
        display_name=display_name,
        entries=entries,
        aggregate_risk_tier_snapshot=risk.tier,
        aggregate_risk_reason_snapshot=risk.reason,
        aggregate_reason_codes_snapshot=risk.reason_codes,
        aggregate_contributing_entry_ids_snapshot=highest_risk_entry_ids(entries, risk.tier),
        risk_policy_version=RISK_POLICY_VERSION,
        created_at=int(time()),
        created_by=created_by,
        description=description,
        supersedes_version=version - 1 if version > 1 else None,
    )


def entry_from_asset(pack_id: str, asset: CapabilityAsset, *, required: bool) -> CapabilityPackEntry:
    primary_purpose = purpose_for_asset(asset)
    reason_codes = reason_codes_for_asset(asset)
    risk = infer_risk(reason_codes)
    return CapabilityPackEntry(
        entry_id=f"{pack_id}-{asset.id}-{primary_purpose}",
        asset_id=asset.id,
        required=required,
        primary_purpose=primary_purpose,
        secondary_purposes=[],
        selection_rationale=f"Selected {asset.name} for {primary_purpose}.",
        asset_type_snapshot=asset.type,
        asset_name_snapshot=asset.name,
        source_snapshot=asset.source,
        version_snapshot=asset.version,
        install_path_snapshot=asset.install_path,
        permissions_snapshot=asset.permissions,
        asset_snapshot_hash=asset_snapshot_hash(asset),
        inferred_reason_codes_snapshot=reason_codes,
        risk_tier_snapshot=risk.tier,
        risk_reason_snapshot=risk.reason,
    )


def purpose_for_asset(asset: CapabilityAsset) -> str:
    if asset.type == "rule":
        return "governance"
    if asset.type == "memory":
        return "memory"
    if asset.type == "script":
        return "implementation"
    if asset.type == "mcp_server":
        return "browser_automation" if "browser" in asset.name.lower() else "implementation"
    return "implementation"


def require_asset(assets: dict[str, CapabilityAsset], asset_id: str) -> CapabilityAsset:
    try:
        return assets[asset_id]
    except KeyError as exc:
        raise ValueError(f"asset not found in inventory: {asset_id}") from exc
