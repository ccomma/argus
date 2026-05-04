"""版本锁定数据模型：定义资产锁定条目和版本锁管理器的结构。

版本锁定用于确保 AI Agent 在生产环境中使用确定性的能力版本，
防止因上游变更导致的不兼容或安全风险。LockEntry 为不可变数据类。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LockEntry:
    """单条版本锁定条目（不可变数据类）。

    记录一个能力资产的精确版本信息和锁定原因。
    每个条目唯一标识一个资产（asset_id），同一 asset_id 再次锁定时会原地更新。
    """
    asset_id: str
    asset_type: str
    source: str
    version: str
    locked_at: int = 0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "source": self.source,
            "version": self.version,
            "locked_at": self.locked_at,
            "reason": self.reason,
        }


@dataclass
class VersionLock:
    """版本锁管理器。

    职责：管理所有版本锁定条目，支持锁定/解锁/查询/持久化。
    核心语义：同一 asset_id 再次锁定时会原地替换旧条目（而非追加重复项）。
    """

    entries: list[LockEntry] = field(default_factory=list)
    lockfile_path: Path | None = None

    def lock(
        self,
        asset_id: str,
        asset_type: str,
        source: str,
        version: str,
        reason: str = "",
    ) -> LockEntry:
        """锁定一个资产版本。

        1. 遍历现有条目，若 asset_id 已存在则原地替换（保证唯一性）
        2. 不存在则追加新条目
        3. 返回最终的 LockEntry
        """
        for i, entry in enumerate(self.entries):
            if entry.asset_id == asset_id:
                new_entry = LockEntry(
                    asset_id=asset_id,
                    asset_type=asset_type,
                    source=source,
                    version=version,
                    locked_at=int(time.time()),
                    reason=reason,
                )
                self.entries[i] = new_entry
                return new_entry
        entry = LockEntry(
            asset_id=asset_id,
            asset_type=asset_type,
            source=source,
            version=version,
            locked_at=int(time.time()),
            reason=reason,
        )
        self.entries.append(entry)
        return entry

    def unlock(self, asset_id: str) -> bool:
        """解除资产版本锁定，返回是否实际移除了条目。"""
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.asset_id != asset_id]
        return len(self.entries) < before

    def get(self, asset_id: str) -> LockEntry | None:
        """按资产 ID 查找锁定条目，未找到返回 None。"""
        for entry in self.entries:
            if entry.asset_id == asset_id:
                return entry
        return None

    def is_locked(self, asset_id: str) -> bool:
        """判断指定资产是否已有版本锁定。"""
        return self.get(asset_id) is not None

    def list_locked(self) -> list[LockEntry]:
        """列出所有已锁定的资产，按 asset_id 排序。"""
        return sorted(self.entries, key=lambda e: e.asset_id)

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "entries": [e.to_dict() for e in self.entries],
        }

    def save(self, path: Path | None = None) -> None:
        """持久化锁文件到指定路径（或已绑定的 lockfile_path）。"""
        p = path or self.lockfile_path
        if p is None:
            raise ValueError("No path provided and no lockfile_path set")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> VersionLock:
        """从 JSON 锁文件加载，文件不存在时返回空的 VersionLock 并绑定路径。"""
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            entries = [
                LockEntry(
                    asset_id=e["asset_id"],
                    asset_type=e["asset_type"],
                    source=e["source"],
                    version=e["version"],
                    locked_at=e.get("locked_at", 0),
                    reason=e.get("reason", ""),
                )
                for e in data.get("entries", [])
            ]
            return cls(entries=entries, lockfile_path=path)
        return cls(lockfile_path=path)
