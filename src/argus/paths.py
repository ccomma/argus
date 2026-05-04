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

    @property
    def governance_reports_dir(self) -> Path:
        return self.root / "governance" / "reports"

    @property
    def resolution_reports_dir(self) -> Path:
        return self.root / "resolution" / "reports"

    @property
    def modifications_snapshots_dir(self) -> Path:
        return self.root / "modifications" / "snapshots"

    @property
    def modifications_audit_log(self) -> Path:
        return self.root / "modifications" / "audit.jsonl"

    @property
    def modifications_reports_dir(self) -> Path:
        return self.root / "modifications" / "reports"

    @property
    def handoffs_dir(self) -> Path:
        return self.root / "handoffs"
