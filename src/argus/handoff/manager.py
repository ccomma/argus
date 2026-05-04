from __future__ import annotations

import json
from pathlib import Path

from .models import HandoffRecord


class HandoffManager:
    def __init__(self, handoffs_dir: Path) -> None:
        self.handoffs_dir = handoffs_dir

    def create(
        self,
        *,
        from_role_id: str,
        to_role_id: str,
        contract_id: str = "",
        context: dict | None = None,
        handoff_reason: str = "",
    ) -> HandoffRecord:
        record = HandoffRecord.create(
            from_role_id=from_role_id,
            to_role_id=to_role_id,
            contract_id=contract_id,
            context=context,
            handoff_reason=handoff_reason,
        )
        self.handoffs_dir.mkdir(parents=True, exist_ok=True)
        (self.handoffs_dir / f"{record.id}.json").write_text(
            json.dumps(record.to_dict(), sort_keys=True, indent=2), encoding="utf-8"
        )
        return record

    def load(self, handoff_id: str) -> HandoffRecord | None:
        path = self.handoffs_dir / f"{handoff_id}.json"
        if not path.exists():
            return None
        return HandoffRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_by_contract(self, contract_id: str) -> list[HandoffRecord]:
        return self._list_filtered(lambda r: r.contract_id == contract_id)

    def list_by_role(self, role_id: str) -> list[HandoffRecord]:
        return self._list_filtered(lambda r: r.from_role_id == role_id or r.to_role_id == role_id)

    def list_all(self) -> list[HandoffRecord]:
        return self._list_filtered(lambda _: True)

    def _list_filtered(self, predicate) -> list[HandoffRecord]:
        if not self.handoffs_dir.exists():
            return []
        records: list[HandoffRecord] = []
        for path in sorted(self.handoffs_dir.glob("*.json")):
            record = HandoffRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if predicate(record):
                records.append(record)
        return records
