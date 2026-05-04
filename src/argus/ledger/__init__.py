from __future__ import annotations

"""账本（Ledger）子系统模块。

提供事件账本、候选学习项提取、学习报告和转录数据摄取的完整能力。
是 Argus 系统的"记忆"层——记录执行过程中发生的事件，
并从中提取可复用的学习经验。
"""

from argus.ledger.jsonl import AppendOnlyJsonlStore
from argus.ledger.models import EventRecord
from argus.ledger.store import EventLedger
from argus.ledger.learning import (
    CandidateLearningItem,
    LearningExtractor,
    LearningLedger,
    LearningReport,
    LearningReporter,
)
from argus.ledger.ingestion import ContractEvidenceIngestor, TranscriptIngestor

__all__ = [
    "AppendOnlyJsonlStore",
    "CandidateLearningItem",
    "ContractEvidenceIngestor",
    "EventLedger",
    "EventRecord",
    "LearningExtractor",
    "LearningLedger",
    "LearningReport",
    "LearningReporter",
    "TranscriptIngestor",
]
