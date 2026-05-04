from __future__ import annotations

from argus.ledger.ingestion import TranscriptIngestor
from argus.ledger.models import EventRecord
from argus.ledger.store import EventLedger

from .base import BaseAdapter


class CodexAdapter(BaseAdapter):
    def __init__(self, ledger: EventLedger) -> None:
        self._ledger = ledger
        self._ingestor = TranscriptIngestor(ledger)

    @property
    def agent_name(self) -> str:
        return "codex"

    def normalize_event(self, raw: dict) -> EventRecord:
        return EventRecord.create(
            source="codex_adapter",
            agent="codex",
            session=raw.get("session", ""),
            timestamp=raw.get("timestamp", ""),
            event_type=raw.get("event_type", "unknown"),
            evidence=raw.get("evidence", raw),
        )

    def submit_event(self, event: EventRecord) -> str:
        self._ledger.append(event)
        return event.id

    def ingest_transcript(self, path: str) -> int:
        return self._ingestor.ingest(path)
