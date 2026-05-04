"""治理 + 决议 CLI - 治理报告和决议执行的命令定义和 handler。"""

from __future__ import annotations

import argparse
from typing import Any

from argus.cli._common import (
    _governance_application,
    _print_json,
    _resolution_application,
)


def add_governance_commands(subparsers: Any) -> None:
    """注册治理子命令：report。"""
    report = subparsers.add_parser("report", help="Write a local governance report.")
    report.add_argument("--store", default=".argus")


def add_resolve_commands(subparsers: Any) -> None:
    """注册决议子命令：run/report。"""
    run = subparsers.add_parser("run", help="Run capability resolution against all capability gaps.")
    run.add_argument("--store", default=".argus")

    report = subparsers.add_parser("report", help="Write a capability resolution report.")
    report.add_argument("--store", default=".argus")


def handle_governance_report(args: argparse.Namespace) -> int:
    report = _governance_application(args).write_report()
    _print_json({
        "markdown_path": str(report.markdown_path),
        "json_path": str(report.json_path),
        "low_risk_log_path": str(report.low_risk_log_path),
        "pending_actions_path": str(report.pending_actions_path),
    })
    return 0


def handle_resolve_run(args: argparse.Namespace) -> int:
    resolutions = _resolution_application(args).resolve_all()
    _print_json([r.to_dict() for r in resolutions])
    return 0


def handle_resolve_report(args: argparse.Namespace) -> int:
    report = _resolution_application(args).write_report()
    _print_json({"markdown_path": str(report.markdown_path), "json_path": str(report.json_path)})
    return 0
