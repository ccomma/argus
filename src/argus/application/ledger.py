from __future__ import annotations

from pathlib import Path

from argus.ledger import ContractEvidenceIngestor, EventLedger, EventRecord, TranscriptIngestor
from argus.storage import ContractStorage


class LedgerApplication:
    def __init__(self, storage: ContractStorage, event_ledger: EventLedger) -> None:
        self.storage = storage
        self.event_ledger = event_ledger

    def ingest_contract(self, contract_id: str) -> int:
        return ContractEvidenceIngestor(self.storage, self.event_ledger).ingest(contract_id)

    def ingest_transcript(self, path: str | Path) -> int:
        return TranscriptIngestor(self.event_ledger).ingest(path)

    def list_events(self) -> list[EventRecord]:
        return self.event_ledger.list_events()
