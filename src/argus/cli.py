from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from argus.application import (
    AssetApplication,
    CapabilityPackApplication,
    GovernanceApplication,
    LearningApplication,
    LedgerApplication,
    ModificationApplication,
    QueryApplication,
    ResolutionApplication,
    RolePackApplication,
)
from argus.controlled_modification import AuditLedger, AssetDiffer, RollbackManager, SnapshotManager
from argus.assets import AssetScanProfile, CapabilityInventory, local_codex_asset_profile
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.analytics import DashboardReporter, ROICalculator
from argus.contracts import ContractSession, QuestionStrategy
from argus.core import ArgusCore
from argus.handoff import HandoffManager
from argus.ledger import EventLedger, LearningLedger
from argus.maintenance import MaintenanceEngine, MaintenanceReporter
from argus.mcp import MCPServer
from argus.paths import ArgusPaths
from argus.storage import ContractStorage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="argus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    contract = subparsers.add_parser("contract", help="Work contract commands.")
    contract_subparsers = contract.add_subparsers(dest="contract_command", required=True)
    ledger = subparsers.add_parser("ledger", help="Event ledger commands.")
    ledger_subparsers = ledger.add_subparsers(dest="ledger_command", required=True)
    learning = subparsers.add_parser("learning", help="Candidate learning commands.")
    learning_subparsers = learning.add_subparsers(dest="learning_command", required=True)
    assets = subparsers.add_parser("assets", help="Capability asset inventory commands.")
    assets_subparsers = assets.add_subparsers(dest="assets_command", required=True)
    packs = subparsers.add_parser("packs", help="Capability pack commands.")
    packs_subparsers = packs.add_subparsers(dest="packs_command", required=True)
    roles = subparsers.add_parser("roles", help="Role capability pack commands.")
    roles_subparsers = roles.add_subparsers(dest="roles_command", required=True)
    governance = subparsers.add_parser("governance", help="Governance report commands.")
    governance_subparsers = governance.add_subparsers(dest="governance_command", required=True)
    resolve = subparsers.add_parser("resolve", help="Capability resolution commands.")
    resolve_subparsers = resolve.add_subparsers(dest="resolve_command", required=True)
    modify = subparsers.add_parser("modify", help="Controlled modification and rollback commands.")
    modify_subparsers = modify.add_subparsers(dest="modify_command", required=True)
    query = subparsers.add_parser("query", help="Cross-cutting lookup commands.")
    query_subparsers = query.add_subparsers(dest="query_command", required=True)
    mcp_serve = subparsers.add_parser("mcp-serve", help="Start the Argus MCP server on stdio.")
    dashboard = subparsers.add_parser("dashboard", help="Write a local dashboard report.")
    maintenance = subparsers.add_parser("maintenance", help="Run maintenance checks on the system.")
    maintenance_subparsers = maintenance.add_subparsers(dest="maintenance_command", required=True)

    _add_contract_commands(contract_subparsers)
    _add_ledger_commands(ledger_subparsers)
    _add_learning_commands(learning_subparsers)
    _add_asset_commands(assets_subparsers)
    _add_pack_commands(packs_subparsers)
    _add_role_commands(roles_subparsers)
    _add_governance_commands(governance_subparsers)
    _add_resolve_commands(resolve_subparsers)
    _add_modify_commands(modify_subparsers)
    _add_query_commands(query_subparsers)
    mcp_serve.add_argument("--store", default=".argus")
    dashboard.add_argument("--store", default=".argus")
    _add_maintenance_commands(maintenance_subparsers)

    args = parser.parse_args(argv)
    return _dispatch(parser, args)


def _add_contract_commands(subparsers: Any) -> None:
    draft = subparsers.add_parser("draft", help="Draft a work contract from an intent.")
    draft.add_argument("--intent", required=True)
    draft.add_argument("--mode", choices=("quick", "standard", "strict"), default="standard")
    draft.add_argument("--goal", default="")
    draft.add_argument("--context", default="")
    draft.add_argument("--inputs", default="")
    draft.add_argument("--outputs", default="")
    draft.add_argument("--constraints", default="")
    draft.add_argument("--risks", default="")
    draft.add_argument("--acceptance-criteria", default="")
    draft.add_argument("--store", default=".argus")

    start = subparsers.add_parser("start", help="Interactively draft a work contract.")
    start.add_argument("--intent", required=True)
    start.add_argument("--mode", choices=("quick", "standard", "strict"), default="standard")
    start.add_argument("--store", default=".argus")

    evaluate = subparsers.add_parser("evaluate", help="Evaluate a deliverable against a contract.")
    evaluate.add_argument("contract_id")
    evaluate.add_argument("deliverable_path")
    evaluate.add_argument("--type", choices=("prd", "roadmap", "research_plan"), default="prd")
    evaluate.add_argument("--store", default=".argus")

    show = subparsers.add_parser("show", help="Show a stored work contract.")
    show.add_argument("contract_id")
    show.add_argument("--store", default=".argus")

    score = subparsers.add_parser("score", help="Show a stored work contract completeness score.")
    score.add_argument("contract_id")
    score.add_argument("--store", default=".argus")

    render = subparsers.add_parser("render", help="Render a deliverable draft from a work contract.")
    render.add_argument("contract_id")
    render.add_argument("--type", choices=("prd", "roadmap", "research_plan"), default="prd")
    render.add_argument("--store", default=".argus")

    bind_pack = subparsers.add_parser("bind-pack", help="Bind a concrete capability pack version to a work contract.")
    bind_pack.add_argument("contract_id")
    bind_pack.add_argument("pack_id")
    bind_pack.add_argument("--version", type=int, default=None)
    bind_pack.add_argument("--rationale", required=True)
    bind_pack.add_argument("--store", default=".argus")

    contract_list = subparsers.add_parser("list", help="List all stored work contracts.")
    contract_list.add_argument("--store", default=".argus")


def _add_ledger_commands(subparsers: Any) -> None:
    ingest_contract = subparsers.add_parser("ingest-contract", help="Import contract evidence into the event ledger.")
    ingest_contract.add_argument("contract_id")
    ingest_contract.add_argument("--store", default=".argus")

    ingest_transcript = subparsers.add_parser("ingest-transcript", help="Import a transcript JSONL fixture.")
    ingest_transcript.add_argument("path")
    ingest_transcript.add_argument("--store", default=".argus")

    ledger_list = subparsers.add_parser("list", help="List event ledger records.")
    ledger_list.add_argument("--store", default=".argus")


def _add_learning_commands(subparsers: Any) -> None:
    learning_extract = subparsers.add_parser("extract", help="Extract candidate learnings from the event ledger.")
    learning_extract.add_argument("--store", default=".argus")

    learning_list = subparsers.add_parser("list", help="List candidate learnings.")
    learning_list.add_argument("--store", default=".argus")

    learning_report = subparsers.add_parser("report", help="Write a local learning report.")
    learning_report.add_argument("--store", default=".argus")


def _add_asset_commands(subparsers: Any) -> None:
    scan = subparsers.add_parser("scan", help="Scan local capability assets into an inventory.")
    _add_asset_scan_args(scan)

    list_assets = subparsers.add_parser("list", help="List scanned capability assets.")
    list_assets.add_argument("--store", default=".argus")

    report = subparsers.add_parser("report", help="Write a capability asset scan report.")
    report.add_argument("--store", default=".argus")

    link = subparsers.add_parser("link-learnings", help="Link candidate learnings to scanned capability assets.")
    link.add_argument("--store", default=".argus")


def _add_pack_commands(subparsers: Any) -> None:
    propose = subparsers.add_parser("propose", help="Propose a capability pack manifest from inventory assets.")
    _add_pack_create_args(propose)

    create = subparsers.add_parser("create", help="Create a versioned capability pack manifest.")
    _add_pack_create_args(create)

    inspect = subparsers.add_parser("inspect", help="Inspect a capability pack manifest.")
    inspect.add_argument("pack_id")
    inspect.add_argument("--version", type=int, default=None)
    inspect.add_argument("--store", default=".argus")

    check = subparsers.add_parser("check", help="Check a capability pack against the current inventory.")
    check.add_argument("pack_id")
    check.add_argument("--version", type=int, default=None)
    check.add_argument("--store", default=".argus")

    advise = subparsers.add_parser("advise", help="Report missing and duplicate capabilities for requested capability names.")
    advise.add_argument("--required-capability", action="append", default=[])
    advise.add_argument("--store", default=".argus")

    pack_list = subparsers.add_parser("list", help="List all stored capability packs.")
    pack_list.add_argument("--store", default=".argus")


def _add_role_commands(subparsers: Any) -> None:
    create = subparsers.add_parser("create-pack", help="Create a role capability pack from existing capability packs.")
    create.add_argument("--store", default=".argus")
    create.add_argument("--role-id", required=True)
    create.add_argument("--display-name", required=True)
    create.add_argument("--required-pack", action="append", default=[])
    create.add_argument("--optional-pack", action="append", default=[])
    create.add_argument("--created-by", default="argus-cli")

    inspect = subparsers.add_parser("inspect-pack", help="Inspect a role capability pack.")
    inspect.add_argument("role_id")
    inspect.add_argument("--version", type=int, default=None)
    inspect.add_argument("--store", default=".argus")

    check = subparsers.add_parser("check-pack", help="Check a role capability pack.")
    check.add_argument("role_id")
    check.add_argument("--version", type=int, default=None)
    check.add_argument("--store", default=".argus")

    role_list = subparsers.add_parser("list", help="List all stored role packs.")
    role_list.add_argument("--store", default=".argus")


def _add_governance_commands(subparsers: Any) -> None:
    report = subparsers.add_parser("report", help="Write a local governance report.")
    report.add_argument("--store", default=".argus")


def _add_resolve_commands(subparsers: Any) -> None:
    run = subparsers.add_parser("run", help="Run capability resolution against all capability gaps.")
    run.add_argument("--store", default=".argus")

    report = subparsers.add_parser("report", help="Write a capability resolution report.")
    report.add_argument("--store", default=".argus")


def _add_modify_commands(subparsers: Any) -> None:
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


def _add_maintenance_commands(subparsers: Any) -> None:
    run = subparsers.add_parser("run", help="Run maintenance checks (duplicates, conflicts, unused).")
    run.add_argument("--store", default=".argus")

    report = subparsers.add_parser("report", help="Write a maintenance report.")
    report.add_argument("--store", default=".argus")


def _add_query_commands(subparsers: Any) -> None:
    contract = subparsers.add_parser("contract", help="Query contracts with related objects.")
    contract.add_argument("contract_id")
    contract.add_argument("--store", default=".argus")

    role = subparsers.add_parser("role", help="Query a role with related packs and handoffs.")
    role.add_argument("role_id")
    role.add_argument("--store", default=".argus")


def _add_pack_create_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--store", default=".argus")
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--required-asset", action="append", default=[])
    parser.add_argument("--optional-asset", action="append", default=[])
    parser.add_argument("--created-by", default="argus-cli")


def _add_asset_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--store", default=".argus")
    parser.add_argument("--profile", choices=("local-codex",), action="append", default=[])
    parser.add_argument("--profile-home", default=None)
    parser.add_argument("--skill-dir", action="append", default=[])
    parser.add_argument("--plugin-dir", action="append", default=[])
    parser.add_argument("--mcp-config", action="append", default=[])
    parser.add_argument("--rule-file", action="append", default=[])
    parser.add_argument("--script-dir", action="append", default=[])
    parser.add_argument("--memory-dir", action="append", default=[])


def _dispatch(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    if args.command == "mcp-serve":
        return _mcp_serve(args)
    if args.command == "dashboard":
        return _dashboard(args)

    handlers = {
        ("contract", "draft"): _draft,
        ("contract", "start"): _start,
        ("contract", "evaluate"): _evaluate,
        ("contract", "show"): _show,
        ("contract", "score"): _score,
        ("contract", "render"): _render,
        ("contract", "bind-pack"): _contract_bind_pack,
        ("contract", "list"): _contract_list,
        ("ledger", "ingest-contract"): _ledger_ingest_contract,
        ("ledger", "ingest-transcript"): _ledger_ingest_transcript,
        ("ledger", "list"): _ledger_list,
        ("learning", "extract"): _learning_extract,
        ("learning", "list"): _learning_list,
        ("learning", "report"): _learning_report,
        ("assets", "scan"): _assets_scan,
        ("assets", "list"): _assets_list,
        ("assets", "report"): _assets_report,
        ("assets", "link-learnings"): _assets_link_learnings,
        ("packs", "propose"): _packs_propose,
        ("packs", "create"): _packs_create,
        ("packs", "inspect"): _packs_inspect,
        ("packs", "check"): _packs_check,
        ("packs", "advise"): _packs_advise,
        ("packs", "list"): _packs_list,
        ("roles", "create-pack"): _roles_create_pack,
        ("roles", "inspect-pack"): _roles_inspect_pack,
        ("roles", "check-pack"): _roles_check_pack,
        ("roles", "list"): _roles_list,
        ("governance", "report"): _governance_report,
        ("resolve", "run"): _resolve_run,
        ("resolve", "report"): _resolve_report,
        ("modify", "preview"): _modify_preview,
        ("modify", "apply"): _modify_apply,
        ("modify", "contract-preview"): _modify_contract_preview,
        ("modify", "contract-apply"): _modify_contract_apply,
        ("modify", "rollback"): _modify_rollback,
        ("modify", "audit-log"): _modify_audit_log,
        ("modify", "report"): _modify_report,
        ("query", "contract"): _query_contract,
        ("query", "role"): _query_role,
        ("maintenance", "run"): _maintenance_run,
        ("maintenance", "report"): _maintenance_report,
    }
    subcommand = getattr(args, f"{args.command}_command")
    try:
        handler = handlers.get((args.command, subcommand))
        if handler:
            return handler(args)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    parser.error("unknown command")
    return 2


def _draft(args: argparse.Namespace) -> int:
    contract = _core(args).draft_contract(
        intent=args.intent,
        mode=args.mode,
        answers=_answers_from_args(args),
    )
    _print_json(contract.to_dict())
    return 0


def _start(args: argparse.Namespace) -> int:
    strategy = QuestionStrategy.for_mode(args.mode)
    session = ContractSession.start(args.intent, strategy)
    for question in session.next_questions():
        print(f"{question.question} [{question.field}]", file=sys.stderr)
        print("> ", end="", file=sys.stderr, flush=True)
        answer = sys.stdin.readline().strip()
        if answer:
            session.answer(**{question.field: answer})
    contract = _core(args).draft_contract(intent=session.intent, mode=args.mode, answers=session.answers)
    _print_json(contract.to_dict())
    return 0


def _evaluate(args: argparse.Namespace) -> int:
    text = Path(args.deliverable_path).read_text(encoding="utf-8")
    result = _core(args).evaluate_deliverable(
        contract_id=args.contract_id,
        deliverable_type=args.type,
        text=text,
    )
    _print_json(result.to_dict())
    return 0


def _show(args: argparse.Namespace) -> int:
    contract = _core(args).load_contract(args.contract_id)
    _print_json(contract.to_dict())
    return 0


def _score(args: argparse.Namespace) -> int:
    contract = _core(args).load_contract(args.contract_id)
    _print_json(contract.completeness_score.to_dict())
    return 0


def _render(args: argparse.Namespace) -> int:
    rendered = _core(args).render_deliverable(args.contract_id, args.type)
    print(rendered, end="")
    return 0


def _contract_bind_pack(args: argparse.Namespace) -> int:
    binding = _pack_application(args).bind_contract(args.contract_id, args.pack_id, args.rationale, args.version)
    _print_json(binding.to_dict())
    return 0


def _ledger_ingest_contract(args: argparse.Namespace) -> int:
    imported = _ledger_application(args).ingest_contract(args.contract_id)
    _print_json({"imported": imported})
    return 0


def _ledger_ingest_transcript(args: argparse.Namespace) -> int:
    imported = _ledger_application(args).ingest_transcript(args.path)
    _print_json({"imported": imported})
    return 0


def _ledger_list(args: argparse.Namespace) -> int:
    _print_json([event.to_dict() for event in _ledger_application(args).list_events()])
    return 0


def _learning_extract(args: argparse.Namespace) -> int:
    created = _learning_application(args).extract()
    _print_json({"created": created})
    return 0


def _learning_list(args: argparse.Namespace) -> int:
    _print_json([item.to_dict() for item in _learning_application(args).list_items()])
    return 0


def _learning_report(args: argparse.Namespace) -> int:
    report = _learning_application(args).write_report()
    _print_json({"markdown_path": str(report.markdown_path), "json_path": str(report.json_path)})
    return 0


def _assets_scan(args: argparse.Namespace) -> int:
    profile = _asset_scan_profile(args)
    result, report = _asset_application(args).scan(profile)
    _print_json(
        {
            "assets": len(result.assets),
            "profiles": args.profile,
            "warnings": result.warnings,
            "inventory_path": str(_paths(args).asset_inventory),
            "report_path": str(report.report_path),
        }
    )
    return 0


def _assets_list(args: argparse.Namespace) -> int:
    _print_json([asset.to_dict() for asset in _asset_application(args).list_assets()])
    return 0


def _assets_report(args: argparse.Namespace) -> int:
    report = _asset_application(args).write_report()
    _print_json({"report_path": str(report.report_path)})
    return 0


def _assets_link_learnings(args: argparse.Namespace) -> int:
    links, report = _asset_application(args).link_learnings()
    _print_json(
        {
            "links": len(links),
            "link_report_path": str(report.link_report_path),
        }
    )
    return 0


def _packs_propose(args: argparse.Namespace) -> int:
    result = _pack_application(args).propose(
        pack_id=args.pack_id,
        display_name=args.display_name,
        description=args.description,
        required_asset_ids=args.required_asset,
        optional_asset_ids=args.optional_asset,
        created_by=args.created_by,
    )
    _print_json(_pack_result_dict(result))
    return 0


def _packs_create(args: argparse.Namespace) -> int:
    result = _pack_application(args).create(
        pack_id=args.pack_id,
        display_name=args.display_name,
        description=args.description,
        required_asset_ids=args.required_asset,
        optional_asset_ids=args.optional_asset,
        created_by=args.created_by,
    )
    _print_json(_pack_result_dict(result))
    return 0


def _packs_inspect(args: argparse.Namespace) -> int:
    manifest, hash_value = _pack_application(args).inspect(args.pack_id, args.version)
    _print_json({"content_hash": hash_value, "manifest": manifest.to_dict()})
    return 0


def _packs_check(args: argparse.Namespace) -> int:
    _print_json(_pack_application(args).check(args.pack_id, args.version).to_dict())
    return 0


def _packs_advise(args: argparse.Namespace) -> int:
    report = _pack_application(args).advise(args.required_capability)
    _print_json(report.to_dict())
    return 0


def _roles_create_pack(args: argparse.Namespace) -> int:
    role_pack = _role_application(args).create(
        role_id=args.role_id,
        display_name=args.display_name,
        required_pack_ids=args.required_pack,
        optional_pack_ids=args.optional_pack,
        created_by=args.created_by,
    )
    _print_json(role_pack.to_dict())
    return 0


def _roles_inspect_pack(args: argparse.Namespace) -> int:
    _print_json(_role_application(args).inspect(args.role_id, args.version).to_dict())
    return 0


def _roles_check_pack(args: argparse.Namespace) -> int:
    _print_json(_role_application(args).check(args.role_id, args.version).to_dict())
    return 0


def _governance_report(args: argparse.Namespace) -> int:
    report = _governance_application(args).write_report()
    _print_json(
        {
            "markdown_path": str(report.markdown_path),
            "json_path": str(report.json_path),
            "low_risk_log_path": str(report.low_risk_log_path),
            "pending_actions_path": str(report.pending_actions_path),
        }
    )
    return 0


def _resolve_run(args: argparse.Namespace) -> int:
    resolutions = _resolution_application(args).resolve_all()
    _print_json([r.to_dict() for r in resolutions])
    return 0


def _resolve_report(args: argparse.Namespace) -> int:
    report = _resolution_application(args).write_report()
    _print_json(
        {
            "markdown_path": str(report.markdown_path),
            "json_path": str(report.json_path),
        }
    )
    return 0


def _modify_preview(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    diff = app.preview_asset_modification(
        asset_id=args.asset_id,
        triggered_by=args.triggered_by,
        trigger_reason=args.trigger_reason,
        new_status=args.new_status,
    )
    if diff is None:
        _print_json({"error": f"Asset {args.asset_id} not found."})
        return 1
    _print_json(diff.to_dict())
    return 0


def _modify_apply(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    result = app.apply_asset_modification(
        asset_id=args.asset_id,
        triggered_by=args.triggered_by,
        trigger_reason=args.trigger_reason,
        new_status=args.new_status,
    )
    if result is None:
        _print_json({"error": f"Asset {args.asset_id} not found."})
        return 1
    _print_json(result.to_dict())
    return 0


def _modify_contract_preview(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    updates = _parse_field_updates(args.fields)
    diff = app.preview_contract_modification(
        contract_id=args.contract_id,
        triggered_by=args.triggered_by,
        trigger_reason=args.trigger_reason,
        field_updates=updates,
    )
    if diff is None:
        _print_json({"error": f"Contract {args.contract_id} not found."})
        return 1
    _print_json(diff.to_dict())
    return 0


def _modify_contract_apply(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    updates = _parse_field_updates(args.fields)
    result = app.apply_contract_modification(
        contract_id=args.contract_id,
        triggered_by=args.triggered_by,
        trigger_reason=args.trigger_reason,
        field_updates=updates,
    )
    if result is None:
        _print_json({"error": f"Contract {args.contract_id} not found."})
        return 1
    _print_json(result.to_dict())
    return 0


def _modify_rollback(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    result = app.rollback(args.audit_id, args.reason)
    _print_json(result.to_dict())
    return 0 if result.outcome == "applied" else 1


def _modify_audit_log(args: argparse.Namespace) -> int:
    records = _modification_application(args).list_audit_log()
    _print_json([r.to_dict() for r in records])
    return 0


def _modify_report(args: argparse.Namespace) -> int:
    report = _modification_application(args).write_report()
    _print_json(
        {
            "markdown_path": str(report.markdown_path),
            "json_path": str(report.json_path),
        }
    )
    return 0


def _contract_list(args: argparse.Namespace) -> int:
    _print_json([c.to_dict() for c in _storage(args).list_contracts()])
    return 0


def _packs_list(args: argparse.Namespace) -> int:
    _print_json([p.to_dict() for p in CapabilityPackStore(_paths(args).capability_packs_dir).list_latest()])
    return 0


def _roles_list(args: argparse.Namespace) -> int:
    pack_store = CapabilityPackStore(_paths(args).capability_packs_dir)
    _print_json([r.to_dict() for r in RolePackStore(_paths(args).role_packs_dir, pack_store).list_latest()])
    return 0


def _query_contract(args: argparse.Namespace) -> int:
    results = _query_application(args).query_contracts(contract_id=args.contract_id)
    _print_json(results)
    return 0


def _query_role(args: argparse.Namespace) -> int:
    results = _query_application(args).query_roles(role_id=args.role_id)
    _print_json(results)
    return 0


def _mcp_serve(args: argparse.Namespace) -> int:
    MCPServer(store=args.store).serve()
    return 0


def _dashboard(args: argparse.Namespace) -> int:
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


def _maintenance_run(args: argparse.Namespace) -> int:
    engine = _maintenance_engine(args)
    report = engine.run()
    _print_json(report.to_dict())
    return 0


def _maintenance_report(args: argparse.Namespace) -> int:
    engine = _maintenance_engine(args)
    p = _paths(args)
    paths = MaintenanceReporter(p.root / "maintenance").write(engine)
    _print_json({
        "markdown_path": str(paths.markdown_path),
        "json_path": str(paths.json_path),
    })
    return 0


def _parse_field_updates(fields: list[str]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for f in fields:
        if "=" in f:
            key, value = f.split("=", 1)
            updates[key] = value
    return updates


def _core(args: argparse.Namespace) -> ArgusCore:
    return ArgusCore(_storage(args))


def _storage(args: argparse.Namespace) -> ContractStorage:
    return ContractStorage(args.store)


def _ledger_application(args: argparse.Namespace) -> LedgerApplication:
    return LedgerApplication(_storage(args), _event_ledger(args))


def _learning_application(args: argparse.Namespace) -> LearningApplication:
    return LearningApplication(_event_ledger(args), _learning_ledger(args), _reports_dir(args))


def _asset_application(args: argparse.Namespace) -> AssetApplication:
    return AssetApplication(_asset_inventory(args), _asset_reports_dir(args), _learning_ledger(args))


def _pack_application(args: argparse.Namespace) -> CapabilityPackApplication:
    return CapabilityPackApplication(
        _asset_inventory(args),
        CapabilityPackStore(_paths(args).capability_packs_dir),
        _storage(args),
    )


def _role_application(args: argparse.Namespace) -> RolePackApplication:
    pack_store = CapabilityPackStore(_paths(args).capability_packs_dir)
    return RolePackApplication(_asset_inventory(args), RolePackStore(_paths(args).role_packs_dir, pack_store))


def _governance_application(args: argparse.Namespace) -> GovernanceApplication:
    pack_store = CapabilityPackStore(_paths(args).capability_packs_dir)
    role_store = RolePackStore(_paths(args).role_packs_dir, pack_store)
    return GovernanceApplication(
        _storage(args),
        _learning_ledger(args),
        _asset_inventory(args),
        pack_store,
        role_store,
        _paths(args).governance_reports_dir,
    )


def _resolution_application(args: argparse.Namespace) -> ResolutionApplication:
    pack_store = CapabilityPackStore(_paths(args).capability_packs_dir)
    role_store = RolePackStore(_paths(args).role_packs_dir, pack_store)
    return ResolutionApplication(
        _asset_inventory(args),
        _learning_ledger(args),
        pack_store,
        role_store,
        _storage(args),
        _paths(args).resolution_reports_dir,
    )


def _query_application(args: argparse.Namespace) -> QueryApplication:
    p = _paths(args)
    pack_store = CapabilityPackStore(p.capability_packs_dir)
    role_store = RolePackStore(p.role_packs_dir, pack_store)
    return QueryApplication(
        _storage(args),
        _event_ledger(args),
        _learning_ledger(args),
        _asset_inventory(args),
        pack_store,
        role_store,
        HandoffManager(p.handoffs_dir),
    )


def _roi_calculator(args: argparse.Namespace) -> ROICalculator:
    p = _paths(args)
    pack_store = CapabilityPackStore(p.capability_packs_dir)
    role_store = RolePackStore(p.role_packs_dir, pack_store)
    return ROICalculator(
        _storage(args),
        _event_ledger(args),
        _learning_ledger(args),
        _asset_inventory(args),
        pack_store,
        role_store,
        HandoffManager(p.handoffs_dir),
    )


def _maintenance_engine(args: argparse.Namespace) -> MaintenanceEngine:
    p = _paths(args)
    pack_store = CapabilityPackStore(p.capability_packs_dir)
    role_store = RolePackStore(p.role_packs_dir, pack_store)
    return MaintenanceEngine(
        _asset_inventory(args),
        pack_store,
        role_store,
        _storage(args),
    )


def _modification_application(args: argparse.Namespace) -> ModificationApplication:
    p = _paths(args)
    inventory = _asset_inventory(args)
    contract_storage = _storage(args)
    snapshot_mgr = SnapshotManager(p.modifications_snapshots_dir)
    differ = AssetDiffer()
    audit_ledger = AuditLedger(p.modifications_audit_log)
    rollback_mgr = RollbackManager(snapshot_mgr, inventory, contract_storage, audit_ledger)
    return ModificationApplication(
        inventory,
        contract_storage,
        snapshot_mgr,
        differ,
        rollback_mgr,
        audit_ledger,
        p.modifications_reports_dir,
    )


def _event_ledger(args: argparse.Namespace) -> EventLedger:
    return EventLedger(_paths(args).events_ledger)


def _learning_ledger(args: argparse.Namespace) -> LearningLedger:
    return LearningLedger(_paths(args).candidate_learnings)


def _reports_dir(args: argparse.Namespace) -> Path:
    return _paths(args).reports_dir


def _asset_inventory(args: argparse.Namespace) -> CapabilityInventory:
    return CapabilityInventory(_paths(args).asset_inventory)


def _asset_reports_dir(args: argparse.Namespace) -> Path:
    return _paths(args).asset_reports_dir


def _asset_scan_profile(args: argparse.Namespace) -> AssetScanProfile:
    profile = AssetScanProfile()
    for name in args.profile:
        if name == "local-codex":
            profile = profile.merged_with(**local_codex_asset_profile(args.profile_home).to_scan_kwargs())
    return profile.merged_with(
        skill_dirs=args.skill_dir,
        plugin_dirs=args.plugin_dir,
        mcp_configs=args.mcp_config,
        rule_files=args.rule_file,
        script_dirs=args.script_dir,
        memory_dirs=args.memory_dir,
    )


def _paths(args: argparse.Namespace) -> ArgusPaths:
    return ArgusPaths.from_store(args.store)


def _answers_from_args(args: argparse.Namespace) -> dict[str, str]:
    return {
        "goal": args.goal,
        "context": args.context,
        "inputs": args.inputs,
        "outputs": args.outputs,
        "constraints": args.constraints,
        "risks": args.risks,
        "acceptance_criteria": args.acceptance_criteria,
    }


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _pack_result_dict(result: Any) -> dict[str, Any]:
    return {
        "content_hash": result.content_hash,
        "manifest": result.manifest.to_dict(),
        "pack_id": result.manifest.pack_id,
        "path": str(result.path) if result.path else None,
        "version": result.manifest.version,
    }


if __name__ == "__main__":
    raise SystemExit(main())
