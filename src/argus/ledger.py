from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Any

from argus.jsonl import AppendOnlyJsonlStore


@dataclass(frozen=True)
class EventRecord:
    id: str
    source: str
    agent: str
    contract_id: str
    contract_version: int | None
    role: str
    workspace: str
    session: str
    timestamp: int | str
    event_type: str
    evidence: dict[str, Any] = field(default_factory=dict)
    execution_evidence: dict[str, Any] = field(default_factory=dict)
    risk_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventRecord:
        return cls(**data)

    @classmethod
    def create(
        cls,
        *,
        source: str,
        event_type: str,
        evidence: dict[str, Any],
        agent: str = "unknown",
        contract_id: str = "",
        contract_version: int | None = None,
        role: str = "",
        workspace: str = "",
        session: str = "",
        timestamp: int | str = "",
        execution_evidence: dict[str, Any] | None = None,
        risk_metadata: dict[str, Any] | None = None,
    ) -> EventRecord:
        payload = {
            "source": source,
            "agent": agent,
            "contract_id": contract_id,
            "contract_version": contract_version,
            "role": role,
            "workspace": workspace,
            "session": session,
            "timestamp": timestamp,
            "event_type": event_type,
            "evidence": evidence,
            "execution_evidence": execution_evidence or {},
        }
        digest = sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        return cls(
            id=f"event-{digest}",
            source=source,
            agent=agent,
            contract_id=contract_id,
            contract_version=contract_version,
            role=role,
            workspace=workspace,
            session=session,
            timestamp=timestamp,
            event_type=event_type,
            evidence=evidence,
            execution_evidence=execution_evidence or {},
            risk_metadata=risk_metadata or {},
        )


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
