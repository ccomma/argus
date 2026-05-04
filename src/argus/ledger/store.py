from __future__ import annotations

from pathlib import Path

from argus.ledger.jsonl import AppendOnlyJsonlStore
from argus.ledger.models import EventRecord


class EventLedger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._store = AppendOnlyJsonlStore(
            self.path,
            serializer=lambda event: event.to_dict(),
            deserializer=EventRecord.from_dict,
            identity=lambda event: event.id,
        )

    def append(self, event: EventRecord) -> bool:
        return self._store.append(event)

    def append_many(self, events: list[EventRecord]) -> int:
        return self._store.append_many(events)

    def list_events(self) -> list[EventRecord]:
        return self._store.list_items()
