from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ModificationSnapshot


class SnapshotManager:
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
        path = self.snapshots_dir / f"{snapshot_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ModificationSnapshot.from_dict(data)
