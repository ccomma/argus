from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha1
from pathlib import Path
from time import time
from typing import Any


@dataclass(frozen=True)
class HandoffRecord:
    id: str
    from_role_id: str
    to_role_id: str
    contract_id: str
    context: dict[str, Any]
    created_at: int
    handoff_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HandoffRecord:
        return cls(**data)

    @classmethod
    def create(
        cls,
        *,
        from_role_id: str,
        to_role_id: str,
        contract_id: str = "",
        context: dict[str, Any] | None = None,
        handoff_reason: str = "",
    ) -> HandoffRecord:
        payload = {
            "from_role_id": from_role_id,
            "to_role_id": to_role_id,
            "contract_id": contract_id,
            "context": context or {},
            "handoff_reason": handoff_reason,
        }
        digest = sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        return cls(
            id=f"handoff-{digest}",
            from_role_id=from_role_id,
            to_role_id=to_role_id,
            contract_id=contract_id,
            context=context or {},
            created_at=int(time()),
            handoff_reason=handoff_reason,
        )
