from __future__ import annotations

from argus.contracts.models import WorkContract
from argus.contracts.deliverables import DeliverableContract


class DeliverableRenderer:
    def render(self, contract: WorkContract, deliverable_contract: DeliverableContract) -> str:
        if deliverable_contract.deliverable_type == "roadmap":
            return _render_roadmap(contract)
        if deliverable_contract.deliverable_type == "research_plan":
            return _render_research_plan(contract)
        return _render_prd(contract)


def _render_prd(contract: WorkContract) -> str:
    return "\n".join(
        [
            "# PRD",
            "",
            "## Background",
            contract.context or contract.intent,
            "",
            "## Goals",
            contract.goal,
            "",
            "## Non-goals",
            contract.non_goals or "Not specified.",
            "",
            "## User Flows",
            f"1. User starts from intent: {contract.intent}",
            "2. Argus clarifies the work contract.",
            "3. Argus produces and evaluates the deliverable.",
            "",
            "## Success Criteria",
            contract.completion_definition,
            "",
            "## Acceptance Criteria",
            contract.acceptance_criteria,
            "",
        ]
    )


def _render_roadmap(contract: WorkContract) -> str:
    return "\n".join(
        [
            "# Roadmap",
            "",
            "## Goals",
            contract.goal,
            "",
            "## Phases",
            "1. Clarify the work contract.",
            "2. Produce the requested deliverable.",
            "3. Evaluate the deliverable against acceptance criteria.",
            "",
            "## Acceptance Criteria",
            contract.acceptance_criteria,
            "",
            "## Risks",
            contract.risks or "No explicit risks captured.",
            "",
        ]
    )


def _render_research_plan(contract: WorkContract) -> str:
    return "\n".join(
        [
            "# Research Plan",
            "",
            "## Questions",
            contract.goal or contract.intent,
            "",
            "## Sources",
            contract.inputs or "Sources to be identified.",
            "",
            "## Deliverables",
            contract.outputs,
            "",
        ]
    )
