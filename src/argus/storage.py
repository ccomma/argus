from __future__ import annotations

import json
from pathlib import Path

from argus.contracts import WorkContract
from argus.deliverables import DeliverableEvaluation


class ContractStorage:
    def __init__(self, root: str | Path = ".argus") -> None:
        self.root = Path(root)

    def save_contract(self, contract: WorkContract) -> None:
        contract_dir = self._contract_dir(contract.id)
        versions_dir = contract_dir / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(contract_dir / "contract.json", contract.to_dict())
        (contract_dir / "contract.md").write_text(_contract_markdown(contract), encoding="utf-8")
        self._write_json(versions_dir / f"v{contract.version}.json", contract.to_dict())

    def load_contract(self, contract_id: str) -> WorkContract:
        path = self._contract_dir(contract_id) / "contract.json"
        return WorkContract.from_dict(self._read_json(path))

    def save_evaluation(self, contract_id: str, evaluation: DeliverableEvaluation) -> None:
        evaluations_dir = self._contract_dir(contract_id) / "evaluations"
        evaluations_dir.mkdir(parents=True, exist_ok=True)
        index = len(list(evaluations_dir.glob("*.json"))) + 1
        self._write_json(evaluations_dir / f"evaluation-{index}.json", evaluation.to_dict())
        self.append_evidence(
            contract_id,
            {
                "event_type": "deliverable_evaluated",
                "deliverable_type": evaluation.deliverable_type,
                "status": evaluation.status,
                "missing_items": evaluation.missing_items,
            },
        )

    def list_evaluations(self, contract_id: str) -> list[DeliverableEvaluation]:
        evaluations_dir = self._contract_dir(contract_id) / "evaluations"
        if not evaluations_dir.exists():
            return []
        return [
            DeliverableEvaluation.from_dict(self._read_json(path))
            for path in sorted(evaluations_dir.glob("*.json"))
        ]

    def save_deliverable(self, contract_id: str, deliverable_type: str, text: str) -> Path:
        deliverables_dir = self._contract_dir(contract_id) / "deliverables"
        deliverables_dir.mkdir(parents=True, exist_ok=True)
        path = deliverables_dir / f"{deliverable_type}.md"
        path.write_text(text, encoding="utf-8")
        self.append_evidence(
            contract_id,
            {
                "event_type": "deliverable_rendered",
                "deliverable_type": deliverable_type,
                "path": str(path),
            },
        )
        return path

    def append_evidence(self, contract_id: str, event: dict) -> None:
        path = self._contract_dir(contract_id) / "evidence.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    def list_evidence(self, contract_id: str) -> list[dict]:
        path = self._contract_dir(contract_id) / "evidence.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def contract_markdown_path(self, contract_id: str) -> Path:
        return self._contract_dir(contract_id) / "contract.md"

    def _contract_dir(self, contract_id: str) -> Path:
        return self.root / "contracts" / contract_id

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))


def _contract_markdown(contract: WorkContract) -> str:
    return "\n".join(
        [
            f"# Work Contract: {contract.id}",
            "",
            f"- Status: {contract.status}",
            f"- Version: {contract.version}",
            f"- Mode: {contract.questioning_mode}",
            "",
            "## Intent",
            contract.intent,
            "",
            "## Goal",
            contract.goal or "Not specified.",
            "",
            "## Context",
            contract.context or "Not specified.",
            "",
            "## Inputs",
            contract.inputs or "Not specified.",
            "",
            "## Outputs",
            contract.outputs or "Not specified.",
            "",
            "## Constraints",
            contract.constraints or "Not specified.",
            "",
            "## Risks",
            contract.risks or "Not specified.",
            "",
            "## Acceptance Criteria",
            contract.acceptance_criteria or "Not specified.",
            "",
            "## Completeness",
            f"{contract.completeness_score.overall_score}: {contract.completeness_score.rationale}",
            "",
        ]
    )
