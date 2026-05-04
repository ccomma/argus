"""受控修改的领域模型：快照、差异、审计记录、修改结果和报告路径。

所有模型均使用 frozen dataclass 保证不可变性，
ID 通过对 payload 的 SHA1 哈希生成，确保内容寻址。
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Any


def _make_id(prefix: str, payload: dict[str, Any]) -> str:
    """基于 payload 内容生成内容寻址 ID（SHA1 前 16 位）。"""
    digest = sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return f"{prefix}-{digest}"


@dataclass(frozen=True)
class ModificationSnapshot:
    """修改前捕获的状态快照，作为回滚的基准点。

    内容以 JSON 字符串存储（content_json），配合序列化的字典
    嵌入 ID 生成中，确保相同内容产生相同 ID。
    """
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
        """创建变更前的状态快照。

        1. 将内容字典序列化为稳定 JSON
        2. 基于关键属性生成内容寻址 ID
        3. 记录当前时间戳作为 capture_at
        """
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
    """资产或合约变更的结构化差异记录。

    包含 unified diff 行、增删行数统计和变更字段列表。
    """
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
        """基于 diff 数据创建差异对象，ID 由关键字段内容寻址生成。"""
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
    """不可变审计日志记录，串联快照、差异和回滚指令。

    每个修改操作（modify/rollback）均生成一条审计记录，
    rollback_instructions 字段包含人工回滚所需的 CLI 命令。
    """
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
        """创建审计记录，ID 基于操作属性内容寻址生成。"""
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
    """修改操作的结果值对象，关联快照、差异和审计记录 ID。"""
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
    """修改报告的路径引用，包含 Markdown 和 JSON 双格式路径。"""
    markdown_path: Path
    json_path: Path
