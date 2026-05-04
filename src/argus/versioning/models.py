from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LockEntry:
    asset_id: str
    asset_type: str
    source: str
    version: str
    locked_at: int = 0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
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
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.asset_id != asset_id]
        return len(self.entries) < before

    def get(self, asset_id: str) -> LockEntry | None:
        for entry in self.entries:
            if entry.asset_id == asset_id:
                return entry
        return None

    def is_locked(self, asset_id: str) -> bool:
        return self.get(asset_id) is not None

    def list_locked(self) -> list[LockEntry]:
        return sorted(self.entries, key=lambda e: e.asset_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entries],
        }

    def save(self, path: Path | None = None) -> None:
        p = path or self.lockfile_path
        if p is None:
            raise ValueError("No path provided and no lockfile_path set")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> VersionLock:
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
