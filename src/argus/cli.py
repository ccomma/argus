from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from argus.contracts import ContractSession, QuestionStrategy
from argus.core import ArgusCore
from argus.storage import ContractStorage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="argus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    contract = subparsers.add_parser("contract", help="Work contract commands.")
    contract_subparsers = contract.add_subparsers(dest="contract_command", required=True)

    draft = contract_subparsers.add_parser("draft", help="Draft a work contract from an intent.")
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

    start = contract_subparsers.add_parser("start", help="Interactively draft a work contract.")
    start.add_argument("--intent", required=True)
    start.add_argument("--mode", choices=("quick", "standard", "strict"), default="standard")
    start.add_argument("--store", default=".argus")

    evaluate = contract_subparsers.add_parser("evaluate", help="Evaluate a deliverable against a contract.")
    evaluate.add_argument("contract_id")
    evaluate.add_argument("deliverable_path")
    evaluate.add_argument("--type", choices=("prd", "roadmap", "research_plan"), default="prd")
    evaluate.add_argument("--store", default=".argus")

    show = contract_subparsers.add_parser("show", help="Show a stored work contract.")
    show.add_argument("contract_id")
    show.add_argument("--store", default=".argus")

    score = contract_subparsers.add_parser("score", help="Show a stored work contract completeness score.")
    score.add_argument("contract_id")
    score.add_argument("--store", default=".argus")

    render = contract_subparsers.add_parser("render", help="Render a deliverable draft from a work contract.")
    render.add_argument("contract_id")
    render.add_argument("--type", choices=("prd", "roadmap", "research_plan"), default="prd")
    render.add_argument("--store", default=".argus")

    args = parser.parse_args(argv)
    if args.command == "contract" and args.contract_command == "draft":
        return _draft(args)
    if args.command == "contract" and args.contract_command == "start":
        return _start(args)
    if args.command == "contract" and args.contract_command == "evaluate":
        return _evaluate(args)
    if args.command == "contract" and args.contract_command == "show":
        return _show(args)
    if args.command == "contract" and args.contract_command == "score":
        return _score(args)
    if args.command == "contract" and args.contract_command == "render":
        return _render(args)
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


def _core(args: argparse.Namespace) -> ArgusCore:
    return ArgusCore(ContractStorage(args.store))


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


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
