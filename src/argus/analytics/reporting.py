from __future__ import annotations

import json
from pathlib import Path

from .calculator import ROICalculator
from .models import DashboardReport


class DashboardReporter:
    def __init__(self, reports_dir: str | Path) -> None:
        self.reports_dir = Path(reports_dir)

    def write(self, calculator: ROICalculator, *, maintenance_summary: dict | None = None) -> DashboardReport:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        contract_roi = calculator.contract_roi()
        learning_roi = calculator.learning_roi()
        role_roi = calculator.role_roi()

        json_data = {
            "contract_roi": contract_roi.to_dict(),
            "learning_roi": learning_roi.to_dict(),
            "role_roi": role_roi.to_dict(),
            "maintenance": maintenance_summary or {},
        }
        json_path = self.reports_dir / "dashboard.json"
        json_path.write_text(json.dumps(json_data, sort_keys=True, indent=2), encoding="utf-8")

        md_path = self.reports_dir / "dashboard.md"
        md_path.write_text(_dashboard_markdown(contract_roi, learning_roi, role_roi, maintenance_summary), encoding="utf-8")

        return DashboardReport(
            markdown_path=md_path,
            json_path=json_path,
            contract_roi=contract_roi,
            learning_roi=learning_roi,
            role_roi=role_roi,
        )


def _dashboard_markdown(
    contract_roi, learning_roi, role_roi, maintenance: dict | None
) -> str:
    lines = [
        "# Argus Dashboard",
        "",
        "## Work Contracts",
        "",
        f"- Total: {contract_roi.total_contracts}",
        f"- By status: {contract_roi.by_status}",
        f"- Avg completeness: {contract_roi.avg_completeness}",
        f"- Avg question rounds: {contract_roi.avg_question_rounds}",
        f"- Change history entries: {contract_roi.total_change_history_entries}",
        f"- Deliverable pass rate: {contract_roi.deliverable_pass_rate} ({contract_roi.deliverable_total} evaluations)",
        "",
        "## Candidate Learnings",
        "",
        f"- Total: {learning_roi.total_learnings}",
        f"- By type: {learning_roi.by_type}",
        f"- By scope: {learning_roi.by_scope}",
        f"- Avg confidence: {learning_roi.avg_confidence}",
        f"- Pending: {learning_roi.pending_count}",
        f"- Promoted: {learning_roi.promoted_count}",
        "",
        "## Roles",
        "",
        f"- Total roles: {role_roi.total_roles}",
        f"- Total handoffs: {role_roi.total_handoffs}",
        f"- Active roles in handoffs: {role_roi.roles_used_in_handoffs}",
        f"- Avg packs per role: {role_roi.avg_packs_per_role}",
        "",
    ]
    if maintenance:
        lines.extend([
            "## Maintenance",
            "",
        ])
        for key, value in maintenance.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    return "\n".join(lines)
