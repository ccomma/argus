from __future__ import annotations

import json
from pathlib import Path

from .models import AssetDiff, ModificationAuditRecord, ModificationReport, ModificationSnapshot


class ModificationReporter:
    def __init__(self, reports_dir: Path) -> None:
        self.reports_dir = reports_dir

    def write(
        self,
        audit_records: list[ModificationAuditRecord],
        snapshots: list[ModificationSnapshot] = (),
        diffs: list[AssetDiff] = (),
    ) -> ModificationReport:
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        summary = {
            "total_audit_records": len(audit_records),
            "total_snapshots": len(snapshots),
            "total_diffs": len(diffs),
            "by_action": _count_by(audit_records, "action"),
            "by_outcome": _count_by(audit_records, "outcome"),
        }

        json_data = {
            "summary": summary,
            "audit_records": [r.to_dict() for r in audit_records],
            "snapshots": [s.to_dict() for s in snapshots],
            "diffs": [d.to_dict() for d in diffs],
        }
        json_path = self.reports_dir / "modifications-report.json"
        json_path.write_text(json.dumps(json_data, sort_keys=True, indent=2), encoding="utf-8")

        md_lines = [
            "# Controlled Modification Report",
            "",
            "## Summary",
            "",
            f"- Audit records: {summary['total_audit_records']}",
            f"- Snapshots: {summary['total_snapshots']}",
            f"- Diffs: {summary['total_diffs']}",
            "",
            "### By Action",
            "",
        ]
        for action, count in sorted(summary["by_action"].items()):
            md_lines.append(f"- {action}: {count}")

        md_lines.extend(["", "### By Outcome", ""])
        for outcome, count in sorted(summary["by_outcome"].items()):
            md_lines.append(f"- {outcome}: {count}")

        md_lines.extend(["", "## Audit Log", ""])
        for r in audit_records:
            md_lines.append(
                f"- [{r.action}] {r.subject_type}/{r.subject_id} — {r.outcome} "
                f"(snapshot: {r.snapshot_id}, diff: {r.diff_id})"
            )

        if diffs:
            md_lines.extend(["", "## Diffs", ""])
            for d in diffs:
                md_lines.append(f"### {d.subject_type}/{d.subject_id}")
                md_lines.append(f"Changed fields: {', '.join(d.changed_fields) if d.changed_fields else 'none'}")
                md_lines.append(f"Lines: +{d.added_lines}/-{d.removed_lines}")
                md_lines.append("")
                md_lines.append("```diff")
                for line in d.unified_diff_lines[:40]:
                    md_lines.append(line)
                if len(d.unified_diff_lines) > 40:
                    md_lines.append(f"... ({len(d.unified_diff_lines) - 40} more lines)")
                md_lines.append("```")
                md_lines.append("")

        md_path = self.reports_dir / "modifications-report.md"
        md_path.write_text("\n".join(md_lines), encoding="utf-8")

        return ModificationReport(markdown_path=md_path, json_path=json_path)


def _count_by(items: list, attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = getattr(item, attr, "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts
