from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from argus.assets import CapabilityAsset


MANIFEST_SCHEMA_VERSION = "capability-pack-v1"
RISK_POLICY_VERSION = "risk-policy-v1"


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
