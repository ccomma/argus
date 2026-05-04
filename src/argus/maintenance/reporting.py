from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .engine import MaintenanceEngine, MaintenanceReport


@dataclass(frozen=True)
class MaintenanceReportPaths:
    markdown_path: Path
    json_path: Path


class MaintenanceReporter:
    def __init__(self, reports_dir: str | Path) -> None:
        self.reports_dir = Path(reports_dir)

    def write(self, engine: MaintenanceEngine) -> MaintenanceReportPaths:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        report = engine.run()

        json_path = self.reports_dir / "maintenance.json"
        json_path.write_text(json.dumps(report.to_dict(), sort_keys=True, indent=2), encoding="utf-8")

        md_path = self.reports_dir / "maintenance.md"
        md_path.write_text(_maintenance_markdown(report), encoding="utf-8")

        return MaintenanceReportPaths(markdown_path=md_path, json_path=json_path)


def _maintenance_markdown(report: MaintenanceReport) -> str:
    lines = [
        "# Maintenance Report",
        "",
        "## Summary",
        "",
    ]
    for key, val in report.summary.items():
        lines.append(f"- {key}: {val}")
    lines.append("")

    if report.duplicates:
        lines.extend(["## Duplicate Assets", ""])
        for d in report.duplicates:
            lines.append(f"- {d['asset_ids']}: {d['reason']}")
        lines.append("")

    if report.conflicts:
        lines.extend(["## Conflicts", ""])
        for c in report.conflicts:
            lines.append(f"- {c['asset_ids']}: {c['reason']}")
        lines.append("")

    if report.deprecated_assets:
        lines.extend(["## Deprecated Assets", ""])
        for a in report.deprecated_assets:
            lines.append(f"- {a}")
        lines.append("")

    if report.archived_assets:
        lines.extend(["## Archived Assets", ""])
        for a in report.archived_assets:
            lines.append(f"- {a}")
        lines.append("")

    if report.unused_capability_packs:
        lines.extend(["## Unused Capability Packs", ""])
        for p in report.unused_capability_packs:
            lines.append(f"- {p}")
        lines.append("")

    if report.unused_role_packs:
        lines.extend(["## Unused Role Packs", ""])
        for r in report.unused_role_packs:
            lines.append(f"- {r}")
        lines.append("")

    return "\n".join(lines)
