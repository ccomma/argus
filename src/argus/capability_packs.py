from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from time import time
from typing import Any

from argus.asset_analysis import find_potential_duplicates
from argus.asset_models import CapabilityAsset
from argus.asset_text import normalize
from argus.storage import ContractStorage


MANIFEST_SCHEMA_VERSION = "capability-pack-v1"
RISK_POLICY_VERSION = "risk-policy-v1"

RISK_TIERS = ("low", "medium", "high", "critical")
RISK_REASON_BY_PERMISSION = {
    "read": "reads_files",
    "reads_files": "reads_files",
    "write": "writes_files",
    "writes_files": "writes_files",
    "network": "network_access",
    "network_access": "network_access",
    "process": "executes_commands",
    "executes_commands": "executes_commands",
    "secret": "uses_secrets",
    "uses_secrets": "uses_secrets",
    "external_service": "external_service",
}
RISK_TIER_BY_REASON = {
    "reads_files": "low",
    "writes_files": "medium",
    "network_access": "high",
    "executes_commands": "medium",
    "changes_agent_behavior": "high",
    "uses_secrets": "critical",
    "external_service": "high",
    "unknown": "medium",
}


@dataclass(frozen=True)
class RiskInference:
    tier: str
    reason_codes: list[str]
    reason: str
    policy_version: str = RISK_POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityPackEntry:
    entry_id: str
    asset_id: str
    required: bool
    primary_purpose: str
    selection_rationale: str
    asset_type_snapshot: str
    asset_name_snapshot: str
    source_snapshot: str
    version_snapshot: str
    install_path_snapshot: str
    permissions_snapshot: list[str]
    asset_snapshot_hash: str
    inferred_reason_codes_snapshot: list[str]
    risk_tier_snapshot: str
    risk_reason_snapshot: str
    secondary_purposes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityPackEntry:
        return cls(**data)


@dataclass(frozen=True)
class CapabilityPackManifest:
    manifest_schema_version: str
    pack_id: str
    version: int
    display_name: str
    entries: list[CapabilityPackEntry]
    aggregate_risk_tier_snapshot: str
    aggregate_risk_reason_snapshot: str
    aggregate_reason_codes_snapshot: list[str]
    aggregate_contributing_entry_ids_snapshot: list[str]
    risk_policy_version: str
    created_at: int
    created_by: str
    description: str = ""
    supersedes_version: int | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["entries"] = [entry.to_dict() for entry in self.entries]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityPackManifest:
        copied = dict(data)
        copied["entries"] = [CapabilityPackEntry.from_dict(item) for item in copied["entries"]]
        return cls(**copied)


@dataclass(frozen=True)
class CapabilityPackResult:
    manifest: CapabilityPackManifest
    content_hash: str
    path: Path | None = None


@dataclass(frozen=True)
class CapabilityPackCheckReport:
    pack_id: str
    version: int
    complete: bool
    content_hash: str
    missing_required_entry_ids: list[str]
    drifted_required_entry_ids: list[str]
    drifted_optional_entry_ids: list[str]
    current_aggregate_risk_tier: str
    current_aggregate_risk_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityPackBinding:
    contract_id: str
    contract_version: int
    pack_id: str
    pack_version: int
    content_hash: str
    rationale: str
    bound_at: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityPackBinding:
        return cls(**data)


@dataclass(frozen=True)
class CapabilityPackRef:
    pack_id: str
    version: int
    content_hash: str
    required: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityPackRef:
        return cls(**data)


@dataclass(frozen=True)
class RoleCapabilityPack:
    role_id: str
    version: int
    display_name: str
    required_pack_refs: list[CapabilityPackRef]
    optional_pack_refs: list[CapabilityPackRef]
    activation_policy: str
    risk_level: str
    rollback_ref: str
    created_at: int
    created_by: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["required_pack_refs"] = [pack_ref.to_dict() for pack_ref in self.required_pack_refs]
        data["optional_pack_refs"] = [pack_ref.to_dict() for pack_ref in self.optional_pack_refs]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoleCapabilityPack:
        copied = dict(data)
        copied["required_pack_refs"] = [CapabilityPackRef.from_dict(item) for item in copied["required_pack_refs"]]
        copied["optional_pack_refs"] = [CapabilityPackRef.from_dict(item) for item in copied["optional_pack_refs"]]
        return cls(**copied)


@dataclass(frozen=True)
class RolePackCheckReport:
    role_id: str
    version: int
    complete: bool
    required_pack_ids: list[str]
    optional_pack_ids: list[str]
    failed_pack_ids: list[str]
    pack_reports: list[CapabilityPackCheckReport]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["pack_reports"] = [report.to_dict() for report in self.pack_reports]
        return data


@dataclass(frozen=True)
class CapabilityAdviceReport:
    missing_capabilities: list[str]
    duplicate_asset_groups: list[list[CapabilityAsset]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "missing_capabilities": self.missing_capabilities,
            "duplicate_asset_groups": [
                [asset.to_dict() for asset in group]
                for group in self.duplicate_asset_groups
            ],
        }

    def to_markdown(self) -> str:
        lines = ["# Capability Pack Advice", "", "## Missing Capabilities", ""]
        if not self.missing_capabilities:
            lines.append("No missing capabilities found.")
        for capability in self.missing_capabilities:
            lines.append(f"- {capability}")
        lines.extend(["", "## Duplicate Capabilities", ""])
        if not self.duplicate_asset_groups:
            lines.append("No duplicate capability assets found.")
        for group in self.duplicate_asset_groups:
            lines.append("- " + ", ".join(f"{asset.name} ({asset.type})" for asset in group))
        return "\n".join(lines) + "\n"


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
        manifest = _build_manifest(
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


class CapabilityPackStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def write(self, manifest: CapabilityPackManifest) -> Path:
        path = self.manifest_path(manifest.pack_id, manifest.version)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_canonical_json(manifest.to_dict()) + "\n", encoding="utf-8")
        return path

    def load(self, pack_id: str, version: int | None = None) -> tuple[CapabilityPackManifest, str]:
        resolved_version = version if version is not None else self.latest_version(pack_id)
        path = self.manifest_path(pack_id, resolved_version)
        manifest = CapabilityPackManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))
        return manifest, content_hash(manifest)

    def list_latest(self) -> list[CapabilityPackManifest]:
        if not self.root.exists():
            return []
        manifests: list[CapabilityPackManifest] = []
        for pack_dir in sorted(path for path in self.root.iterdir() if path.is_dir()):
            manifest, _ = self.load(pack_dir.name)
            manifests.append(manifest)
        return manifests

    def manifest_path(self, pack_id: str, version: int) -> Path:
        return self.root / pack_id / f"{version}.json"

    def latest_version(self, pack_id: str) -> int:
        pack_dir = self.root / pack_id
        versions = sorted(int(path.stem) for path in pack_dir.glob("*.json") if path.stem.isdigit())
        if not versions:
            raise FileNotFoundError(f"capability pack not found: {pack_id}")
        return versions[-1]

    def next_version(self, pack_id: str) -> int:
        try:
            return self.latest_version(pack_id) + 1
        except FileNotFoundError:
            return 1


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


class CapabilityPackBindingStore:
    def __init__(self, storage: ContractStorage) -> None:
        self.storage = storage

    def bind(
        self,
        *,
        contract_id: str,
        pack: CapabilityPackManifest,
        content_hash: str,
        rationale: str,
    ) -> CapabilityPackBinding:
        contract = self.storage.load_contract(contract_id)
        binding = CapabilityPackBinding(
            contract_id=contract.id,
            contract_version=contract.version,
            pack_id=pack.pack_id,
            pack_version=pack.version,
            content_hash=content_hash,
            rationale=rationale,
            bound_at=int(time()),
        )
        event = {
            "event_type": "capability_pack_bound",
            "contract_id": contract.id,
            "contract_version": contract.version,
            "pack_id": pack.pack_id,
            "pack_version": pack.version,
            "content_hash": content_hash,
            "rationale": rationale,
        }
        contract.capability_pack_ref = f"{pack.pack_id}@{pack.version}#{content_hash}"
        contract.execution_evidence.append(event)
        self.storage.save_contract(contract)
        self.storage.append_evidence(contract.id, event)
        self.storage.save_contract_artifact(contract.id, "capability_pack_binding.json", binding.to_dict())
        return binding


class RolePackStore:
    def __init__(self, root: str | Path, pack_store: CapabilityPackStore) -> None:
        self.root = Path(root)
        self.pack_store = pack_store

    def create(
        self,
        *,
        role_id: str,
        display_name: str,
        required_pack_ids: list[str],
        optional_pack_ids: list[str],
        created_by: str,
        activation_policy: str = "manual",
    ) -> RoleCapabilityPack:
        version = self.next_version(role_id)
        required_refs = [self._pack_ref(pack_id, required=True) for pack_id in required_pack_ids]
        optional_refs = [self._pack_ref(pack_id, required=False) for pack_id in optional_pack_ids]
        risk = _highest_pack_risk(required_refs + optional_refs, self.pack_store)
        role_pack = RoleCapabilityPack(
            role_id=role_id,
            version=version,
            display_name=display_name,
            required_pack_refs=required_refs,
            optional_pack_refs=optional_refs,
            activation_policy=activation_policy,
            risk_level=risk,
            rollback_ref=f"{role_id}@{version - 1}" if version > 1 else "",
            created_at=int(time()),
            created_by=created_by,
        )
        path = self.manifest_path(role_id, version)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_canonical_json(role_pack.to_dict()) + "\n", encoding="utf-8")
        return role_pack

    def load(self, role_id: str, version: int | None = None) -> RoleCapabilityPack:
        resolved_version = version if version is not None else self.latest_version(role_id)
        return RoleCapabilityPack.from_dict(json.loads(self.manifest_path(role_id, resolved_version).read_text(encoding="utf-8")))

    def list_latest(self) -> list[RoleCapabilityPack]:
        if not self.root.exists():
            return []
        role_packs: list[RoleCapabilityPack] = []
        for role_dir in sorted(path for path in self.root.iterdir() if path.is_dir()):
            role_packs.append(self.load(role_dir.name))
        return role_packs

    def check(self, role_id: str, assets: list[CapabilityAsset], version: int | None = None) -> RolePackCheckReport:
        role_pack = self.load(role_id, version)
        reports: list[CapabilityPackCheckReport] = []
        failed: list[str] = []
        for pack_ref in [*role_pack.required_pack_refs, *role_pack.optional_pack_refs]:
            manifest, _ = self.pack_store.load(pack_ref.pack_id, pack_ref.version)
            report = CapabilityPackChecker().check(manifest, assets)
            reports.append(report)
            if pack_ref.required and not report.complete:
                failed.append(pack_ref.pack_id)
        return RolePackCheckReport(
            role_id=role_pack.role_id,
            version=role_pack.version,
            complete=not failed,
            required_pack_ids=[pack_ref.pack_id for pack_ref in role_pack.required_pack_refs],
            optional_pack_ids=[pack_ref.pack_id for pack_ref in role_pack.optional_pack_refs],
            failed_pack_ids=failed,
            pack_reports=reports,
        )

    def manifest_path(self, role_id: str, version: int) -> Path:
        return self.root / role_id / f"{version}.json"

    def latest_version(self, role_id: str) -> int:
        role_dir = self.root / role_id
        versions = sorted(int(path.stem) for path in role_dir.glob("*.json") if path.stem.isdigit())
        if not versions:
            raise FileNotFoundError(f"role capability pack not found: {role_id}")
        return versions[-1]

    def next_version(self, role_id: str) -> int:
        try:
            return self.latest_version(role_id) + 1
        except FileNotFoundError:
            return 1

    def _pack_ref(self, pack_id: str, *, required: bool) -> CapabilityPackRef:
        manifest, hash_value = self.pack_store.load(pack_id)
        return CapabilityPackRef(
            pack_id=manifest.pack_id,
            version=manifest.version,
            content_hash=hash_value,
            required=required,
        )


class CapabilityPackAdvisor:
    def advise(self, *, required_capabilities: list[str], assets: list[CapabilityAsset]) -> CapabilityAdviceReport:
        asset_terms = [_search_text(asset) for asset in assets]
        missing = [
            capability
            for capability in required_capabilities
            if not any(normalize(capability) in terms for terms in asset_terms)
        ]
        return CapabilityAdviceReport(
            missing_capabilities=missing,
            duplicate_asset_groups=find_potential_duplicates(assets),
        )


def infer_risk(reason_codes: list[str]) -> RiskInference:
    known_codes = sorted(set(reason_codes or ["unknown"]))
    highest = "low"
    highest_codes: list[str] = []
    for code in known_codes:
        tier = RISK_TIER_BY_REASON.get(code, "medium")
        if _tier_rank(tier) > _tier_rank(highest):
            highest = tier
            highest_codes = [code]
        elif tier == highest:
            highest_codes.append(code)
    return RiskInference(tier=highest, reason_codes=highest_codes, reason=", ".join(highest_codes))


def aggregate_risk(entries: list[CapabilityPackEntry]) -> RiskInference:
    highest = "low"
    reason_codes: list[str] = []
    entry_ids: list[str] = []
    for entry in entries:
        tier = entry.risk_tier_snapshot
        if _tier_rank(tier) > _tier_rank(highest):
            highest = tier
            reason_codes = list(entry.inferred_reason_codes_snapshot)
            entry_ids = [entry.entry_id]
        elif tier == highest:
            reason_codes.extend(entry.inferred_reason_codes_snapshot)
            entry_ids.append(entry.entry_id)
    codes = sorted(set(reason_codes or ["reads_files"]))
    reason = ", ".join(codes)
    if entry_ids:
        reason = f"{reason}; entries={','.join(entry_ids)}"
    return RiskInference(tier=highest, reason_codes=codes, reason=reason)


def content_hash(manifest: CapabilityPackManifest) -> str:
    return sha256(_canonical_json(manifest.to_dict()).encode("utf-8")).hexdigest()


def asset_snapshot_hash(asset: CapabilityAsset) -> str:
    return sha256(_canonical_json(asset.to_dict()).encode("utf-8")).hexdigest()


def _build_manifest(
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
        entries.append(_entry_from_asset(pack_id, _require_asset(by_id, asset_id), required=True))
    for asset_id in optional_asset_ids:
        entries.append(_entry_from_asset(pack_id, _require_asset(by_id, asset_id), required=False))
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
        aggregate_contributing_entry_ids_snapshot=_highest_risk_entry_ids(entries, risk.tier),
        risk_policy_version=RISK_POLICY_VERSION,
        created_at=int(time()),
        created_by=created_by,
        description=description,
        supersedes_version=version - 1 if version > 1 else None,
    )


def _entry_from_asset(pack_id: str, asset: CapabilityAsset, *, required: bool) -> CapabilityPackEntry:
    primary_purpose = _purpose_for_asset(asset)
    reason_codes = _reason_codes_for_asset(asset)
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


def _purpose_for_asset(asset: CapabilityAsset) -> str:
    if asset.type == "rule":
        return "governance"
    if asset.type == "memory":
        return "memory"
    if asset.type == "script":
        return "implementation"
    if asset.type == "mcp_server":
        return "browser_automation" if "browser" in asset.name.lower() else "implementation"
    return "implementation"


def _reason_codes_for_asset(asset: CapabilityAsset) -> list[str]:
    codes = [RISK_REASON_BY_PERMISSION.get(permission, "unknown") for permission in asset.permissions]
    if not codes:
        codes = ["reads_files"]
    return sorted(set(codes))


def _require_asset(assets: dict[str, CapabilityAsset], asset_id: str) -> CapabilityAsset:
    try:
        return assets[asset_id]
    except KeyError as exc:
        raise ValueError(f"asset not found in inventory: {asset_id}") from exc


def _highest_risk_entry_ids(entries: list[CapabilityPackEntry], tier: str) -> list[str]:
    return [entry.entry_id for entry in entries if entry.risk_tier_snapshot == tier]


def _highest_pack_risk(pack_refs: list[CapabilityPackRef], pack_store: CapabilityPackStore) -> str:
    highest = "low"
    for pack_ref in pack_refs:
        manifest, _ = pack_store.load(pack_ref.pack_id, pack_ref.version)
        if _tier_rank(manifest.aggregate_risk_tier_snapshot) > _tier_rank(highest):
            highest = manifest.aggregate_risk_tier_snapshot
    return highest


def _search_text(asset: CapabilityAsset) -> str:
    return normalize(" ".join([asset.name, asset.type, asset.source, *asset.permissions]))


def _tier_rank(tier: str) -> int:
    return RISK_TIERS.index(tier) if tier in RISK_TIERS else RISK_TIERS.index("medium")


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))
