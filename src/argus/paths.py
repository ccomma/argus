from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArgusPaths:
    root: Path

    @classmethod
    def from_store(cls, store: str | Path) -> ArgusPaths:
        return cls(root=Path(store))

    @property
    def events_ledger(self) -> Path:
        return self.root / "ledger" / "events.jsonl"

    @property
    def candidate_learnings(self) -> Path:
        return self.root / "ledger" / "candidate_learnings.jsonl"

    @property
    def reports_dir(self) -> Path:
        return self.root / "ledger" / "reports"

    @property
    def asset_inventory(self) -> Path:
        return self.root / "assets" / "inventory.json"

    @property
    def asset_reports_dir(self) -> Path:
        return self.root / "assets" / "reports"

    @property
    def capability_packs_dir(self) -> Path:
        return self.root / "capability-packs"

    @property
    def role_packs_dir(self) -> Path:
        return self.root / "role-packs"
