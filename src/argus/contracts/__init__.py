from __future__ import annotations

"""合同子系统模块。

提供工作合同（WorkContract）的定义、澄清问题策略、交付物合约、
交付物渲染和评估，以及证据事件的全套模型和工具。
"""

from argus.contracts.models import (
    CONTRACT_FIELDS,
    QUESTION_PRIORITY,
    QUESTION_TEXT,
    ClarifyingQuestion,
    CompletenessScore,
    ContractSession,
    QuestionStrategy,
    WorkContract,
    WorkContractBuilder,
    score_answers,
)
from argus.contracts.deliverables import DeliverableContract, DeliverableEvaluation, DeliverableEvaluator
from argus.contracts.rendering import DeliverableRenderer
from argus.contracts.evidence import deliverable_evaluated_event, deliverable_rendered_event

__all__ = [
    "CONTRACT_FIELDS",
    "QUESTION_PRIORITY",
    "QUESTION_TEXT",
    "ClarifyingQuestion",
    "CompletenessScore",
    "ContractSession",
    "DeliverableContract",
    "DeliverableEvaluation",
    "DeliverableEvaluator",
    "DeliverableRenderer",
    "QuestionStrategy",
    "WorkContract",
    "WorkContractBuilder",
    "deliverable_evaluated_event",
    "deliverable_rendered_event",
    "score_answers",
]
