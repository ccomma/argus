from __future__ import annotations

import json
from pathlib import Path

from argus.ledger.models import EventRecord
from argus.ledger.store import EventLedger
from argus.storage import ContractStorage


class ContractEvidenceIngestor:
    def __init__(self, storage: ContractStorage, ledger: EventLedger) -> None:
        self.storage = storage
        self.ledger = ledger

    def ingest(self, contract_id: str) -> int:
        contract = self.storage.load_contract(contract_id)
        events = [
            EventRecord.create(
                source="contract_evidence",
                agent="argus",
                contract_id=contract.id,
                contract_version=contract.version,
                event_type=entry.get("event_type", "unknown"),
                evidence=entry,
                execution_evidence=_execution_evidence(entry),
            )
            for entry in self.storage.list_evidence(contract_id)
        ]
        return self.ledger.append_many(events)


class TranscriptIngestor:
    def __init__(self, ledger: EventLedger) -> None:
        self.ledger = ledger

    def ingest(self, path: str | Path) -> int:
        events = []
        for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid transcript JSONL at line {line_number}: {exc.msg}") from exc
            events.append(
                EventRecord.create(
                    source="codex_transcript",
                    agent=raw.get("agent", "codex"),
                    session=raw.get("session", ""),
                    timestamp=raw.get("timestamp", ""),
                    event_type=raw.get("event_type", "unknown"),
                    evidence=raw.get("evidence", raw),
                )
            )
        return self.ledger.append_many(events)


def _execution_evidence(entry: dict) -> dict:
    return {
        key: entry[key]
        for key in ("deliverable_type", "status", "path", "missing_items")
        if key in entry
    }
