"""受控修改 CLI - 预览/应用/合约修改/回滚/审计/报告的命令定义和 handler。"""

from __future__ import annotations

import argparse
from typing import Any

from argus.cli._common import (
    _modification_application,
    _parse_field_updates,
    _print_json,
)


def add_modify_commands(subparsers: Any) -> None:
    """注册修改子命令：preview/apply/contract-preview/contract-apply/rollback/audit-log/report。"""
    preview = subparsers.add_parser("preview", help="Preview an asset modification without applying it.")
    preview.add_argument("--asset-id", required=True)
    preview.add_argument("--triggered-by", required=True)
    preview.add_argument("--trigger-reason", required=True)
    preview.add_argument("--new-status", default="")
    preview.add_argument("--store", default=".argus")

    apply_cmd = subparsers.add_parser("apply", help="Apply a controlled modification to an asset.")
    apply_cmd.add_argument("--asset-id", required=True)
    apply_cmd.add_argument("--triggered-by", required=True)
    apply_cmd.add_argument("--trigger-reason", required=True)
    apply_cmd.add_argument("--new-status", default="")
    apply_cmd.add_argument("--store", default=".argus")

    contract_preview = subparsers.add_parser("contract-preview", help="Preview a contract modification.")
    contract_preview.add_argument("--contract-id", required=True)
    contract_preview.add_argument("--triggered-by", required=True)
    contract_preview.add_argument("--trigger-reason", required=True)
    contract_preview.add_argument("--field", action="append", default=[], dest="fields")
    contract_preview.add_argument("--store", default=".argus")

    contract_apply = subparsers.add_parser("contract-apply", help="Apply a controlled modification to a contract.")
    contract_apply.add_argument("--contract-id", required=True)
    contract_apply.add_argument("--triggered-by", required=True)
    contract_apply.add_argument("--trigger-reason", required=True)
    contract_apply.add_argument("--field", action="append", default=[], dest="fields")
    contract_apply.add_argument("--store", default=".argus")

    rollback = subparsers.add_parser("rollback", help="Rollback a previous modification.")
    rollback.add_argument("--audit-id", required=True)
    rollback.add_argument("--reason", required=True)
    rollback.add_argument("--store", default=".argus")

    audit = subparsers.add_parser("audit-log", help="List all modification audit records.")
    audit.add_argument("--store", default=".argus")

    report = subparsers.add_parser("report", help="Write a modification report.")
    report.add_argument("--store", default=".argus")


def handle_modify_preview(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    diff = app.preview_asset_modification(
        asset_id=args.asset_id, triggered_by=args.triggered_by,
        trigger_reason=args.trigger_reason, new_status=args.new_status,
    )
    if diff is None:
        _print_json({"error": f"Asset {args.asset_id} not found."})
        return 1
    _print_json(diff.to_dict())
    return 0


def handle_modify_apply(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    result = app.apply_asset_modification(
        asset_id=args.asset_id, triggered_by=args.triggered_by,
        trigger_reason=args.trigger_reason, new_status=args.new_status,
    )
    if result is None:
        _print_json({"error": f"Asset {args.asset_id} not found."})
        return 1
    _print_json(result.to_dict())
    return 0


def handle_modify_contract_preview(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    updates = _parse_field_updates(args.fields)
    diff = app.preview_contract_modification(
        contract_id=args.contract_id, triggered_by=args.triggered_by,
        trigger_reason=args.trigger_reason, field_updates=updates,
    )
    if diff is None:
        _print_json({"error": f"Contract {args.contract_id} not found."})
        return 1
    _print_json(diff.to_dict())
    return 0


def handle_modify_contract_apply(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    updates = _parse_field_updates(args.fields)
    result = app.apply_contract_modification(
        contract_id=args.contract_id, triggered_by=args.triggered_by,
        trigger_reason=args.trigger_reason, field_updates=updates,
    )
    if result is None:
        _print_json({"error": f"Contract {args.contract_id} not found."})
        return 1
    _print_json(result.to_dict())
    return 0


def handle_modify_rollback(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    result = app.rollback(args.audit_id, args.reason)
    _print_json(result.to_dict())
    return 0 if result.outcome == "applied" else 1


def handle_modify_audit_log(args: argparse.Namespace) -> int:
    records = _modification_application(args).list_audit_log()
    _print_json([r.to_dict() for r in records])
    return 0


def handle_modify_report(args: argparse.Namespace) -> int:
    report = _modification_application(args).write_report()
    _print_json({"markdown_path": str(report.markdown_path), "json_path": str(report.json_path)})
    return 0
