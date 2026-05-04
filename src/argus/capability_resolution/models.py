from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Decision(StrEnum):
    REUSE = "reuse"
    CONFIGURE = "configure"
    INSTALL_SUGGESTED = "install_suggested"
    CREATE_LOCAL = "create_local"
    MERGE = "merge"
    IGNORE = "ignore"


DECISION_RISK = {
    Decision.REUSE: "low",
    Decision.CONFIGURE: "low",
    Decision.IGNORE: "low",
    Decision.MERGE: "medium",
    Decision.CREATE_LOCAL: "medium",
    Decision.INSTALL_SUGGESTED: "high",
}


@dataclass(frozen=True)
class CapabilityResolution:
    gap_id: str
    gap_description: str
    decision: Decision
    risk_level: str
    matched_local_asset_ids: list[str]
    external_options: list[dict[str, str]]
    confidence: float
    evidence: list[str]
    recommended_action: str
    contract_id: str = ""
    role_id: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["decision"] = self.decision.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityResolution:
        copied = dict(data)
        copied["decision"] = Decision(copied["decision"])
        return cls(**copied)


@dataclass(frozen=True)
class ResolutionReport:
    markdown_path: Path
    json_path: Path
