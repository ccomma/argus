from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ContractROI:
    total_contracts: int
    by_status: dict[str, int]
    avg_completeness: float
    avg_question_rounds: int
    total_change_history_entries: int
    deliverable_pass_rate: float
    deliverable_total: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_contracts": self.total_contracts,
            "by_status": self.by_status,
            "avg_completeness": self.avg_completeness,
            "avg_question_rounds": self.avg_question_rounds,
            "total_change_history_entries": self.total_change_history_entries,
            "deliverable_pass_rate": self.deliverable_pass_rate,
            "deliverable_total": self.deliverable_total,
        }


@dataclass(frozen=True)
class LearningROI:
    total_learnings: int
    by_type: dict[str, int]
    by_scope: dict[str, int]
    avg_confidence: float
    pending_count: int
    promoted_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_learnings": self.total_learnings,
            "by_type": self.by_type,
            "by_scope": self.by_scope,
            "avg_confidence": self.avg_confidence,
            "pending_count": self.pending_count,
            "promoted_count": self.promoted_count,
        }


@dataclass(frozen=True)
class RoleROI:
    total_roles: int
    total_handoffs: int
    roles_used_in_handoffs: list[str]
    avg_packs_per_role: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_roles": self.total_roles,
            "total_handoffs": self.total_handoffs,
            "roles_used_in_handoffs": self.roles_used_in_handoffs,
            "avg_packs_per_role": self.avg_packs_per_role,
        }


@dataclass(frozen=True)
class DashboardReport:
    markdown_path: Path
    json_path: Path
    contract_roi: ContractROI
    learning_roi: LearningROI
    role_roi: RoleROI
