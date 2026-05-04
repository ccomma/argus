"""维护报告生成器，将健康检查结果输出为 Markdown 和 JSON 双格式报告。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .engine import MaintenanceEngine, MaintenanceReport


@dataclass(frozen=True)
class MaintenanceReportPaths:
    """维护报告的文件路径对（Markdown + JSON）。"""
    markdown_path: Path
    json_path: Path


class MaintenanceReporter:
    """维护报告生成器，运行 MaintenanceEngine 并导出双格式报告。

    输出：
    - maintenance.md：Markdown 格式，分节列出六类问题
    - maintenance.json：结构化数据，便于趋势分析和告警集成
    """

    def __init__(self, reports_dir: str | Path) -> None:
        self.reports_dir = Path(reports_dir)

    def write(self, engine: MaintenanceEngine) -> MaintenanceReportPaths:
        """执行维护检查并生成报告。

        1. 调用 engine.run() 获取完整检查结果
        2. 序列化为 JSON 文件
        3. 渲染 Markdown 报告（仅展示有内容的节）
        """
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        report = engine.run()

        json_path = self.reports_dir / "maintenance.json"
        json_path.write_text(json.dumps(report.to_dict(), sort_keys=True, indent=2), encoding="utf-8")

        md_path = self.reports_dir / "maintenance.md"
        md_path.write_text(_maintenance_markdown(report), encoding="utf-8")

        return MaintenanceReportPaths(markdown_path=md_path, json_path=json_path)


def _maintenance_markdown(report: MaintenanceReport) -> str:
    """将维护报告渲染为 Markdown 格式。

    按六大检测类别分节，仅当对应列表非空时才输出该节。
    """
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
