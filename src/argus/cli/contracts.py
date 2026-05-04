"""合约 + 账本 + 学习 CLI - 工作合约起草/评估、事件导入、学习提取的命令定义和 handler。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from argus.cli._common import (
    _answers_from_args,
    _core,
    _learning_application,
    _ledger_application,
    _pack_application,
    _print_json,
    _storage,
)


def add_contract_commands(subparsers: Any) -> None:
    """注册合约子命令：draft/start/evaluate/show/score/render/bind-pack/list。"""
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


def add_ledger_commands(subparsers: Any) -> None:
    """注册账本子命令：ingest-contract/ingest-transcript/list。"""
    ingest_contract = subparsers.add_parser("ingest-contract", help="Import contract evidence into the event ledger.")
    ingest_contract.add_argument("contract_id")
    ingest_contract.add_argument("--store", default=".argus")

    ingest_transcript = subparsers.add_parser("ingest-transcript", help="Import a transcript JSONL fixture.")
    ingest_transcript.add_argument("path")
    ingest_transcript.add_argument("--store", default=".argus")

    ledger_list = subparsers.add_parser("list", help="List event ledger records.")
    ledger_list.add_argument("--store", default=".argus")


def add_learning_commands(subparsers: Any) -> None:
    """注册学习子命令：extract/list/report。"""
    learning_extract = subparsers.add_parser("extract", help="Extract candidate learnings from the event ledger.")
    learning_extract.add_argument("--store", default=".argus")

    learning_list = subparsers.add_parser("list", help="List candidate learnings.")
    learning_list.add_argument("--store", default=".argus")

    learning_report = subparsers.add_parser("report", help="Write a local learning report.")
    learning_report.add_argument("--store", default=".argus")


# ── contract handlers ────────────────────────────────────────────────

def handle_contract_draft(args: argparse.Namespace) -> int:
    """根据意图和预填答案一次性生成工作合约。"""
    contract = _core(args).draft_contract(
        intent=args.intent, mode=args.mode, answers=_answers_from_args(args),
    )
    _print_json(contract.to_dict())
    return 0


def handle_contract_start(args: argparse.Namespace) -> int:
    """交互式合约起草：逐步提问并收集答案，最终生成合约。"""
    from argus.contracts import ContractSession, QuestionStrategy
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


def handle_contract_evaluate(args: argparse.Namespace) -> int:
    text = Path(args.deliverable_path).read_text(encoding="utf-8")
    result = _core(args).evaluate_deliverable(
        contract_id=args.contract_id, deliverable_type=args.type, text=text,
    )
    _print_json(result.to_dict())
    return 0


def handle_contract_show(args: argparse.Namespace) -> int:
    contract = _core(args).load_contract(args.contract_id)
    _print_json(contract.to_dict())
    return 0


def handle_contract_score(args: argparse.Namespace) -> int:
    contract = _core(args).load_contract(args.contract_id)
    _print_json(contract.completeness_score.to_dict())
    return 0


def handle_contract_render(args: argparse.Namespace) -> int:
    rendered = _core(args).render_deliverable(args.contract_id, args.type)
    print(rendered, end="")
    return 0


def handle_contract_bind_pack(args: argparse.Namespace) -> int:
    binding = _pack_application(args).bind_contract(args.contract_id, args.pack_id, args.rationale, args.version)
    _print_json(binding.to_dict())
    return 0


def handle_contract_list(args: argparse.Namespace) -> int:
    _print_json([c.to_dict() for c in _storage(args).list_contracts()])
    return 0


# ── ledger handlers ──────────────────────────────────────────────────

def handle_ledger_ingest_contract(args: argparse.Namespace) -> int:
    imported = _ledger_application(args).ingest_contract(args.contract_id)
    _print_json({"imported": imported})
    return 0


def handle_ledger_ingest_transcript(args: argparse.Namespace) -> int:
    imported = _ledger_application(args).ingest_transcript(args.path)
    _print_json({"imported": imported})
    return 0


def handle_ledger_list(args: argparse.Namespace) -> int:
    _print_json([event.to_dict() for event in _ledger_application(args).list_events()])
    return 0


# ── learning handlers ────────────────────────────────────────────────

def handle_learning_extract(args: argparse.Namespace) -> int:
    created = _learning_application(args).extract()
    _print_json({"created": created})
    return 0


def handle_learning_list(args: argparse.Namespace) -> int:
    _print_json([item.to_dict() for item in _learning_application(args).list_items()])
    return 0


def handle_learning_report(args: argparse.Namespace) -> int:
    report = _learning_application(args).write_report()
    _print_json({"markdown_path": str(report.markdown_path), "json_path": str(report.json_path)})
    return 0
