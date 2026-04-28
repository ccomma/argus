from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from argus.contracts import WorkContract


@dataclass(frozen=True)
class DeliverableContract:
    id: str
    deliverable_type: str
    required_sections: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    missing_item_policy: str = "warn"

    @classmethod
    def prd(cls) -> DeliverableContract:
        return cls(
            id="prd",
            deliverable_type="prd",
            required_sections=(
                "Background",
                "Goals",
                "Non-goals",
                "User Flows",
                "Success Criteria",
                "Acceptance Criteria",
            ),
            acceptance_criteria=("covers_contract_goal", "includes_acceptance_criteria"),
            missing_item_policy="warn",
        )

    @classmethod
    def roadmap(cls) -> DeliverableContract:
        return cls(
            id="roadmap",
            deliverable_type="roadmap",
            required_sections=("Goals", "Phases", "Acceptance Criteria", "Risks"),
            acceptance_criteria=("covers_contract_goal", "includes_phase_exit_conditions"),
        )

    @classmethod
    def research_plan(cls) -> DeliverableContract:
        return cls(
            id="research_plan",
            deliverable_type="research_plan",
            required_sections=("Questions", "Sources", "Deliverables"),
            acceptance_criteria=("defines_questions", "defines_deliverables"),
        )

    @classmethod
    def for_type(cls, deliverable_type: str) -> DeliverableContract:
        if deliverable_type == "roadmap":
            return cls.roadmap()
        if deliverable_type == "research_plan":
            return cls.research_plan()
        return cls.prd()


@dataclass
class DeliverableEvaluation:
    contract_id: str
    deliverable_type: str
    status: str
    covered_items: list[str]
    missing_items: list[str]
    risks: list[str]
    suggested_follow_ups: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeliverableEvaluation:
        return cls(**data)


class DeliverableEvaluator:
    def evaluate(
        self,
        contract: WorkContract,
        deliverable_contract: DeliverableContract,
        text: str,
    ) -> DeliverableEvaluation:
        missing = [
            section
            for section in deliverable_contract.required_sections
            if not _has_heading(text, section)
        ]
        risks = []
        if (
            contract.acceptance_criteria
            and "Acceptance Criteria" in deliverable_contract.required_sections
            and "acceptance" not in text.lower()
        ):
            if "Acceptance Criteria" not in missing:
                missing.append("Acceptance Criteria")
            risks.append("Deliverable does not visibly address the work contract acceptance criteria.")

        if not missing:
            status = "pass"
        elif len(missing) < len(deliverable_contract.required_sections):
            status = "partial"
        else:
            status = "fail"

        covered = [section for section in deliverable_contract.required_sections if section not in missing]
        follow_ups = [f"Add or clarify section: {item}" for item in missing]
        return DeliverableEvaluation(
            contract_id=contract.id,
            deliverable_type=deliverable_contract.deliverable_type,
            status=status,
            covered_items=covered,
            missing_items=missing,
            risks=risks,
            suggested_follow_ups=follow_ups,
        )


def _has_heading(text: str, section: str) -> bool:
    normalized = section.strip().lower()
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip().rstrip(":").lower()
        if stripped == normalized:
            return True
    return False
