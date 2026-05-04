"""审计账本，以追加写入方式持久化所有修改审计记录。

使用 AppendOnlyJsonlStore 确保不可变性——记录一旦写入不可删除或修改。
"""

from __future__ import annotations

from pathlib import Path

from argus.ledger.jsonl import AppendOnlyJsonlStore

from .models import ModificationAuditRecord


class AuditLedger:
    """不可变审计账本，存储所有修改操作的审计追踪。

    底层使用 JSONL 格式的 AppendOnlyJsonlStore，
    保证每条审计记录不可删除和篡改。
    """

    def __init__(self, path: Path) -> None:
        self._store = AppendOnlyJsonlStore[ModificationAuditRecord](
            path,
            serializer=lambda r: r.to_dict(),
            deserializer=ModificationAuditRecord.from_dict,
            identity=lambda r: r.id,
        )

    def append(self, record: ModificationAuditRecord) -> bool:
        """追加一条审计记录，一旦写入不可撤销。"""
        return self._store.append(record)

    def list_records(self) -> list[ModificationAuditRecord]:
        """列出所有已记录的审计条目。"""
        return self._store.list_items()

    def get_by_id(self, audit_id: str) -> ModificationAuditRecord | None:
        """按 ID 查找审计记录，用于回滚前的审计记录定位。"""
        for r in self.list_records():
            if r.id == audit_id:
                return r
        return None
