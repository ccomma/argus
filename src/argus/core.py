from __future__ import annotations

from argus.contracts import (
    ContractSession,
    DeliverableContract,
    DeliverableEvaluation,
    DeliverableEvaluator,
    DeliverableRenderer,
    QuestionStrategy,
    WorkContract,
    WorkContractBuilder,
)
from argus.storage import ContractStorage


class ArgusCore:
    """Application boundary for Phase 1 workflows.

    CLI, future MCP tools, and later adapters should call this layer instead of
    duplicating contract, render, evaluate, and storage orchestration.
    """

    def __init__(self, storage: ContractStorage) -> None:
        self.storage = storage

    def draft_contract(
        self,
        *,
        intent: str,
        mode: str,
        answers: dict[str, str],
    ) -> WorkContract:
        session = ContractSession.start(intent, QuestionStrategy.for_mode(mode))
        session.answer(**answers)
        contract = WorkContractBuilder().build(session)
        self.storage.save_contract(contract)
        return contract

    def load_contract(self, contract_id: str) -> WorkContract:
        return self.storage.load_contract(contract_id)

    def render_deliverable(self, contract_id: str, deliverable_type: str) -> str:
        contract = self.storage.load_contract(contract_id)
        deliverable_contract = DeliverableContract.for_type(deliverable_type)
        rendered = DeliverableRenderer().render(contract, deliverable_contract)
        self.storage.save_deliverable(contract.id, deliverable_contract.deliverable_type, rendered)
        return rendered

    def evaluate_deliverable(
        self,
        *,
        contract_id: str,
        deliverable_type: str,
        text: str,
    ) -> DeliverableEvaluation:
        contract = self.storage.load_contract(contract_id)
        result = DeliverableEvaluator().evaluate(
            contract=contract,
            deliverable_contract=DeliverableContract.for_type(deliverable_type),
            text=text,
        )
        self.storage.save_evaluation(contract.id, result)
        return result
