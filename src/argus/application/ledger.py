"""账本应用服务，负责事件证据的摄取与查询。

实现合约证据和会话转录的摄入流程，是 Argus 证据驱动学习流水线的入口。
"""

from __future__ import annotations

from pathlib import Path

from argus.ledger import ContractEvidenceIngestor, EventLedger, EventRecord, TranscriptIngestor
from argus.storage import ContractStorage


class LedgerApplication:
    """事件账本的应用门面，编排证据摄入和事件查询操作。"""

    def __init__(self, storage: ContractStorage, event_ledger: EventLedger) -> None:
        self.storage = storage
        self.event_ledger = event_ledger

    def ingest_contract(self, contract_id: str) -> int:
        """从合约中提取证据并写入事件账本，返回提取的事件数量。"""
        return ContractEvidenceIngestor(self.storage, self.event_ledger).ingest(contract_id)

    def ingest_transcript(self, path: str | Path) -> int:
        """从会话转录文件中提取证据并写入事件账本，返回提取的事件数量。"""
        return TranscriptIngestor(self.event_ledger).ingest(path)

    def list_events(self) -> list[EventRecord]:
        """列出当前账本中的所有事件记录。"""
        return self.event_ledger.list_events()
