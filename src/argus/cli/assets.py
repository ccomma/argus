"""资产 CLI - 能力扫描、列表、报告和学习链接的命令定义和 handler。"""

from __future__ import annotations

import argparse
from typing import Any

from argus.cli._common import (
    _asset_application,
    _asset_scan_profile,
    _paths,
    _print_json,
)


def add_asset_commands(subparsers: Any) -> None:
    """注册资产子命令：scan/list/report/link-learnings。"""
    scan = subparsers.add_parser("scan", help="Scan local capability assets into an inventory.")
    scan.add_argument("--store", default=".argus")
    scan.add_argument("--profile", choices=("local-codex",), action="append", default=[])
    scan.add_argument("--profile-home", default=None)
    scan.add_argument("--skill-dir", action="append", default=[])
    scan.add_argument("--plugin-dir", action="append", default=[])
    scan.add_argument("--mcp-config", action="append", default=[])
    scan.add_argument("--rule-file", action="append", default=[])
    scan.add_argument("--script-dir", action="append", default=[])
    scan.add_argument("--memory-dir", action="append", default=[])

    list_assets = subparsers.add_parser("list", help="List scanned capability assets.")
    list_assets.add_argument("--store", default=".argus")

    report = subparsers.add_parser("report", help="Write a capability asset scan report.")
    report.add_argument("--store", default=".argus")

    link = subparsers.add_parser("link-learnings", help="Link candidate learnings to scanned capability assets.")
    link.add_argument("--store", default=".argus")


def handle_assets_scan(args: argparse.Namespace) -> int:
    """扫描本地能力资产（技能/插件/MCP/规则/脚本/记忆），写入库存。"""
    profile = _asset_scan_profile(args)
    result, report = _asset_application(args).scan(profile)
    _print_json({
        "assets": len(result.assets),
        "profiles": args.profile,
        "warnings": result.warnings,
        "inventory_path": str(_paths(args).asset_inventory),
        "report_path": str(report.report_path),
    })
    return 0


def handle_assets_list(args: argparse.Namespace) -> int:
    _print_json([asset.to_dict() for asset in _asset_application(args).list_assets()])
    return 0


def handle_assets_report(args: argparse.Namespace) -> int:
    report = _asset_application(args).write_report()
    _print_json({"report_path": str(report.report_path)})
    return 0


def handle_assets_link_learnings(args: argparse.Namespace) -> int:
    links, report = _asset_application(args).link_learnings()
    _print_json({"links": len(links), "link_report_path": str(report.link_report_path)})
    return 0
