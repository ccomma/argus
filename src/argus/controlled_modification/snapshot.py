"""快照管理器，负责在修改前捕获并持久化 subject 的状态快照。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ModificationSnapshot


class SnapshotManager:
    """快照管理器，在受控修改前捕获资产/合约的完整状态。

    每个快照以 JSON 文件持久化在 snapshots_dir 目录下，
    文件名即快照 ID（内容寻址），可随时按 ID 加载。
    """

    def __init__(self, snapshots_dir: Path) -> None:
        self.snapshots_dir = snapshots_dir

    def capture(
        self,
        *,
        subject_type: str,
        subject_id: str,
        content: dict[str, Any],
        version_before: str = "",
        triggered_by: str = "",
        trigger_reason: str = "",
    ) -> ModificationSnapshot:
        """捕获并持久化一个状态快照。

        1. 调用 ModificationSnapshot.capture 创建快照对象（内容寻址 ID）
        2. 确保快照目录存在
        3. 将快照序列化为 JSON 文件（文件名为 {snapshot_id}.json）
        """
        snapshot = ModificationSnapshot.capture(
            subject_type=subject_type,
            subject_id=subject_id,
            content=content,
            version_before=version_before,
            triggered_by=triggered_by,
            trigger_reason=trigger_reason,
        )
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        (self.snapshots_dir / f"{snapshot.id}.json").write_text(
            json.dumps(snapshot.to_dict(), sort_keys=True, indent=2), encoding="utf-8"
        )
        return snapshot

    def load(self, snapshot_id: str) -> ModificationSnapshot | None:
        """按 ID 加载持久化的快照，返回 None 表示快照不存在。"""
        path = self.snapshots_dir / f"{snapshot_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ModificationSnapshot.from_dict(data)
