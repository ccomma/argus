from __future__ import annotations

import json
from pathlib import Path

from .models import CapabilityResolution, Decision, ResolutionReport


class ResolutionReporter:
    def __init__(self, reports_dir: str | Path) -> None:
        self.reports_dir = Path(reports_dir)

    def write(self, resolutions: list[CapabilityResolution]) -> ResolutionReport:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = self.reports_dir / "capability-resolution-report.md"
        json_path = self.reports_dir / "capability-resolution-report.json"

        summary = _summarize(resolutions)
        payload = {
            "summary": summary,
            "resolutions": [r.to_dict() for r in resolutions],
        }

        markdown_path.write_text(_markdown_report(payload), encoding="utf-8")
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return ResolutionReport(markdown_path=markdown_path, json_path=json_path)


def _summarize(resolutions: list[CapabilityResolution]) -> dict:
    by_decision: dict[str, int] = {}
    by_risk: dict[str, int] = {}
    for r in resolutions:
        d = r.decision.value if isinstance(r.decision, Decision) else str(r.decision)
        by_decision[d] = by_decision.get(d, 0) + 1
        by_risk[r.risk_level] = by_risk.get(r.risk_level, 0) + 1
    return {
        "total_gaps": len(resolutions),
        "by_decision": by_decision,
        "by_risk": by_risk,
    }


def _markdown_report(payload: dict) -> str:
    lines = [
        "# Argus Capability Resolution Report",
        "",
        "## Summary",
        "",
    ]
    for key, value in payload["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Resolutions", ""])
    if not payload["resolutions"]:
        lines.append("No capability gaps to resolve.")
    for r in payload["resolutions"]:
        decision = r["decision"]
        risk = r["risk_level"]
        lines.append(f"### [{decision}] [{risk}] {r['gap_description']}")
        lines.append("")
        lines.append(f"- Decision: **{decision}**")
        lines.append(f"- Risk: {risk}")
        lines.append(f"- Confidence: {r['confidence']:.2f}")
        lines.append(f"- Recommended: {r['recommended_action']}")
        if r["matched_local_asset_ids"]:
            lines.append(f"- Local assets: {', '.join(r['matched_local_asset_ids'])}")
        if r["evidence"]:
            lines.append(f"- Evidence: {'; '.join(r['evidence'])}")
        lines.append("")
    return "\n".join(lines) + "\n"
