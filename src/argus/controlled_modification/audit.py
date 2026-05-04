from __future__ import annotations

from pathlib import Path

from argus.ledger.jsonl import AppendOnlyJsonlStore

from .models import ModificationAuditRecord


class AuditLedger:
    def __init__(self, path: Path) -> None:
        self._store = AppendOnlyJsonlStore[ModificationAuditRecord](
            path,
            serializer=lambda r: r.to_dict(),
            deserializer=ModificationAuditRecord.from_dict,
            identity=lambda r: r.id,
        )

    def append(self, record: ModificationAuditRecord) -> bool:
        return self._store.append(record)

    def list_records(self) -> list[ModificationAuditRecord]:
        return self._store.list_items()

    def get_by_id(self, audit_id: str) -> ModificationAuditRecord | None:
        for r in self.list_records():
            if r.id == audit_id:
                return r
        return None
