from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Any


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

    def append(self, event: EventRecord) -> bool:
        existing_ids = {existing.id for existing in self.list_events()}
        if event.id in existing_ids:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
        return True

    def append_many(self, events: list[EventRecord]) -> int:
        return sum(1 for event in events if self.append(event))

    def list_events(self) -> list[EventRecord]:
        if not self.path.exists():
            return []
        return [
            EventRecord.from_dict(json.loads(line))
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
