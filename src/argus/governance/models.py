from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GovernanceFinding:
    category: str
    severity: str
    subject_id: str
    summary: str
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PendingAction:
    type: str
    risk_level: str
    subject_id: str
    summary: str
    requires_confirmation: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GovernanceReportResult:
    markdown_path: Path
    json_path: Path
    low_risk_log_path: Path
    pending_actions_path: Path
