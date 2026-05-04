from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Any


def _make_id(prefix: str, payload: dict[str, Any]) -> str:
    digest = sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return f"{prefix}-{digest}"


@dataclass(frozen=True)
class ModificationSnapshot:
    id: str
    subject_type: str
    subject_id: str
    captured_at: int
    content_json: str
    version_before: str = ""
    triggered_by: str = ""
    trigger_reason: str = ""

    @classmethod
    def capture(
        cls,
        *,
        subject_type: str,
        subject_id: str,
        content: dict[str, Any],
        version_before: str = "",
        triggered_by: str = "",
        trigger_reason: str = "",
    ) -> ModificationSnapshot:
        content_json = json.dumps(content, sort_keys=True, default=str)
        payload = {
            "subject_type": subject_type,
            "subject_id": subject_id,
            "version_before": version_before,
            "triggered_by": triggered_by,
            "trigger_reason": trigger_reason,
            "content_json": content_json,
            "captured_at": int(time.time()),
        }
        snap_id = _make_id("snap", payload)
        return cls(
            id=snap_id,
            subject_type=subject_type,
            subject_id=subject_id,
            captured_at=payload["captured_at"],
            content_json=content_json,
            version_before=version_before,
            triggered_by=triggered_by,
            trigger_reason=trigger_reason,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModificationSnapshot:
        return cls(**data)


@dataclass(frozen=True)
class AssetDiff:
    id: str
    subject_type: str
    subject_id: str
    version_before: str
    version_after: str
    unified_diff_lines: list[str] = field(default_factory=list)
    added_lines: int = 0
    removed_lines: int = 0
    changed_fields: list[str] = field(default_factory=list)
    created_at: int = 0

    @classmethod
    def create(
        cls,
        *,
        subject_type: str,
        subject_id: str,
        version_before: str,
        version_after: str,
        unified_diff_lines: list[str],
        added_lines: int,
        removed_lines: int,
        changed_fields: list[str],
    ) -> AssetDiff:
        payload = {
            "subject_type": subject_type,
            "subject_id": subject_id,
            "version_before": version_before,
            "version_after": version_after,
            "unified_diff_lines": unified_diff_lines,
            "changed_fields": changed_fields,
        }
        diff_id = _make_id("diff", payload)
        return cls(
            id=diff_id,
            subject_type=subject_type,
            subject_id=subject_id,
            version_before=version_before,
            version_after=version_after,
            unified_diff_lines=unified_diff_lines,
            added_lines=added_lines,
            removed_lines=removed_lines,
            changed_fields=changed_fields,
            created_at=int(time.time()),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssetDiff:
        return cls(**data)


@dataclass(frozen=True)
class ModificationAuditRecord:
    id: str
    timestamp: int
    triggered_by: str
    trigger_reason: str
    subject_type: str
    subject_id: str
    action: str
    snapshot_id: str
    diff_id: str = ""
    rollback_instructions: str = ""
    outcome: str = "applied"

    @classmethod
    def create(
        cls,
        *,
        triggered_by: str,
        trigger_reason: str,
        subject_type: str,
        subject_id: str,
        action: str,
        snapshot_id: str,
        diff_id: str = "",
        rollback_instructions: str = "",
        outcome: str = "applied",
    ) -> ModificationAuditRecord:
        payload = {
            "triggered_by": triggered_by,
            "trigger_reason": trigger_reason,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "action": action,
            "snapshot_id": snapshot_id,
            "diff_id": diff_id,
            "timestamp": int(time.time()),
        }
        audit_id = _make_id("audit", payload)
        return cls(
            id=audit_id,
            timestamp=payload["timestamp"],
            triggered_by=triggered_by,
            trigger_reason=trigger_reason,
            subject_type=subject_type,
            subject_id=subject_id,
            action=action,
            snapshot_id=snapshot_id,
            diff_id=diff_id,
            rollback_instructions=rollback_instructions,
            outcome=outcome,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModificationAuditRecord:
        return cls(**data)


@dataclass(frozen=True)
class ModificationResult:
    snapshot_id: str
    diff_id: str = ""
    audit_record_id: str = ""
    outcome: str = "applied"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModificationResult:
        return cls(**data)


@dataclass(frozen=True)
class ModificationReport:
    markdown_path: Path
    json_path: Path
