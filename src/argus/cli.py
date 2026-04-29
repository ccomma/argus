from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from argus.assets import (
    AssetReporter,
    CandidateAssetLinker,
    CapabilityAssetScanner,
    CapabilityInventory,
    AssetScanProfile,
    local_codex_asset_profile,
)
from argus.contracts import ContractSession, QuestionStrategy
from argus.core import ArgusCore
from argus.ingestion import ContractEvidenceIngestor, TranscriptIngestor
from argus.ledger import EventLedger
from argus.learning import LearningExtractor, LearningLedger, LearningReporter
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

    _add_contract_commands(contract_subparsers)
    _add_ledger_commands(ledger_subparsers)
    _add_learning_commands(learning_subparsers)
    _add_asset_commands(assets_subparsers)

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
    handlers = {
        ("contract", "draft"): _draft,
        ("contract", "start"): _start,
        ("contract", "evaluate"): _evaluate,
        ("contract", "show"): _show,
        ("contract", "score"): _score,
        ("contract", "render"): _render,
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


def _ledger_ingest_contract(args: argparse.Namespace) -> int:
    imported = ContractEvidenceIngestor(_storage(args), _event_ledger(args)).ingest(args.contract_id)
    _print_json({"imported": imported})
    return 0


def _ledger_ingest_transcript(args: argparse.Namespace) -> int:
    imported = TranscriptIngestor(_event_ledger(args)).ingest(args.path)
    _print_json({"imported": imported})
    return 0


def _ledger_list(args: argparse.Namespace) -> int:
    _print_json([event.to_dict() for event in _event_ledger(args).list_events()])
    return 0


def _learning_extract(args: argparse.Namespace) -> int:
    items = LearningExtractor().extract(_event_ledger(args).list_events())
    created = _learning_ledger(args).append_many(items)
    _print_json({"created": created})
    return 0


def _learning_list(args: argparse.Namespace) -> int:
    _print_json([item.to_dict() for item in _learning_ledger(args).list_items()])
    return 0


def _learning_report(args: argparse.Namespace) -> int:
    report = LearningReporter(_reports_dir(args)).write(
        _event_ledger(args).list_events(),
        _learning_ledger(args).list_items(),
    )
    _print_json({"markdown_path": str(report.markdown_path), "json_path": str(report.json_path)})
    return 0


def _assets_scan(args: argparse.Namespace) -> int:
    profile = _asset_scan_profile(args)
    result = CapabilityAssetScanner().scan(**profile.to_scan_kwargs())
    _asset_inventory(args).write(result.assets)
    report = AssetReporter(_asset_reports_dir(args)).write(result.assets, warnings=result.warnings)
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
    _print_json([asset.to_dict() for asset in _asset_inventory(args).list_assets()])
    return 0


def _assets_report(args: argparse.Namespace) -> int:
    report = AssetReporter(_asset_reports_dir(args)).write(_asset_inventory(args).list_assets())
    _print_json({"report_path": str(report.report_path)})
    return 0


def _assets_link_learnings(args: argparse.Namespace) -> int:
    links = CandidateAssetLinker().link(_learning_ledger(args).list_items(), _asset_inventory(args).list_assets())
    report = AssetReporter(_asset_reports_dir(args)).write(_asset_inventory(args).list_assets(), links=links)
    _print_json(
        {
            "links": len(links),
            "link_report_path": str(report.link_report_path),
        }
    )
    return 0


def _core(args: argparse.Namespace) -> ArgusCore:
    return ArgusCore(_storage(args))


def _storage(args: argparse.Namespace) -> ContractStorage:
    return ContractStorage(args.store)


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


if __name__ == "__main__":
    raise SystemExit(main())
