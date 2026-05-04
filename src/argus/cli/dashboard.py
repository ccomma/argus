"""Dashboard + 维护 CLI - 投资回报仪表盘和维护检查的命令定义和 handler。"""

from __future__ import annotations

import argparse
from typing import Any

from argus.analytics import DashboardReporter, ROICalculator
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.cli._common import (
    _asset_inventory,
    _event_ledger,
    _learning_ledger,
    _paths,
    _print_json,
    _storage,
)
from argus.handoff import HandoffManager
from argus.maintenance import MaintenanceEngine, MaintenanceReporter


def add_maintenance_commands(subparsers: Any) -> None:
    """注册维护子命令：run/report。"""
    run = subparsers.add_parser("run", help="Run maintenance checks (duplicates, conflicts, unused).")
    run.add_argument("--store", default=".argus")

    report = subparsers.add_parser("report", help="Write a maintenance report.")
    report.add_argument("--store", default=".argus")


def handle_dashboard(args: argparse.Namespace) -> int:
    """计算 ROI 并输出仪表盘报告路径和摘要数据。"""
    calculator = _roi_calculator(args)
    p = _paths(args)
    report = DashboardReporter(p.root / "reports").write(calculator)
    _print_json({
        "markdown_path": str(report.markdown_path),
        "json_path": str(report.json_path),
        "contract_roi": report.contract_roi.to_dict(),
        "learning_roi": report.learning_roi.to_dict(),
        "role_roi": report.role_roi.to_dict(),
    })
    return 0


def handle_maintenance_run(args: argparse.Namespace) -> int:
    engine = _maintenance_engine(args)
    report = engine.run()
    _print_json(report.to_dict())
    return 0


def handle_maintenance_report(args: argparse.Namespace) -> int:
    engine = _maintenance_engine(args)
    p = _paths(args)
    paths = MaintenanceReporter(p.root / "maintenance").write(engine)
    _print_json({
        "markdown_path": str(paths.markdown_path),
        "json_path": str(paths.json_path),
    })
    return 0


def _roi_calculator(args: argparse.Namespace) -> ROICalculator:
    p = _paths(args)
    pack_store = CapabilityPackStore(p.capability_packs_dir)
    role_store = RolePackStore(p.role_packs_dir, pack_store)
    return ROICalculator(
        _storage(args), _event_ledger(args), _learning_ledger(args),
        _asset_inventory(args), pack_store, role_store, HandoffManager(p.handoffs_dir),
    )


def _maintenance_engine(args: argparse.Namespace) -> MaintenanceEngine:
    p = _paths(args)
    pack_store = CapabilityPackStore(p.capability_packs_dir)
    role_store = RolePackStore(p.role_packs_dir, pack_store)
    return MaintenanceEngine(
        _asset_inventory(args), pack_store, role_store, _storage(args),
    )
