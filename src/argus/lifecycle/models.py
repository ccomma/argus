from __future__ import annotations

import enum
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class AssetState(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DISABLED = "disabled"
    ISOLATED = "isolated"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    DELETED = "deleted"


class LifecycleAction(enum.Enum):
    CREATE = "create"
    ACTIVATE = "activate"
    DISABLE = "disable"
    ISOLATE = "isolate"
    RELEASE = "release"
    DEPRECATE = "deprecate"
    ARCHIVE = "archive"
    DELETE = "delete"
    ROLLBACK = "rollback"


TRANSITIONS: dict[AssetState, dict[LifecycleAction, AssetState]] = {
    AssetState.DRAFT: {
        LifecycleAction.ACTIVATE: AssetState.ACTIVE,
        LifecycleAction.ARCHIVE: AssetState.ARCHIVED,
        LifecycleAction.DELETE: AssetState.DELETED,
    },
    AssetState.ACTIVE: {
        LifecycleAction.DISABLE: AssetState.DISABLED,
        LifecycleAction.ISOLATE: AssetState.ISOLATED,
        LifecycleAction.DEPRECATE: AssetState.DEPRECATED,
        LifecycleAction.ARCHIVE: AssetState.ARCHIVED,
    },
    AssetState.DISABLED: {
        LifecycleAction.ACTIVATE: AssetState.ACTIVE,
        LifecycleAction.ARCHIVE: AssetState.ARCHIVED,
    },
    AssetState.ISOLATED: {
        LifecycleAction.RELEASE: AssetState.ACTIVE,
        LifecycleAction.ARCHIVE: AssetState.ARCHIVED,
    },
    AssetState.DEPRECATED: {
        LifecycleAction.ACTIVATE: AssetState.ACTIVE,
        LifecycleAction.ARCHIVE: AssetState.ARCHIVED,
    },
    AssetState.ARCHIVED: {
        LifecycleAction.ACTIVATE: AssetState.ACTIVE,
        LifecycleAction.DELETE: AssetState.DELETED,
    },
    AssetState.DELETED: {},
}


class StateMachine:
    def __init__(self, current: AssetState) -> None:
        self.current = current
        self.transitions = TRANSITIONS

    def can(self, action: LifecycleAction) -> bool:
        return action in self.transitions.get(self.current, {})

    def available_actions(self) -> list[LifecycleAction]:
        return list(self.transitions.get(self.current, {}).keys())

    def apply(self, action: LifecycleAction) -> AssetState:
        next_state = self.transitions.get(self.current, {}).get(action)
        if next_state is None:
            raise ValueError(f"Cannot {action.value} from {self.current.value}")
        self.current = next_state
        return self.current


def state_machine_for(status: str) -> StateMachine:
    try:
        return StateMachine(AssetState(status))
    except ValueError:
        return StateMachine(AssetState.DRAFT)


@dataclass(frozen=True)
class LifecycleRecord:
    record_id: str
    asset_id: str
    asset_type: str
    action: LifecycleAction
    from_state: AssetState
    to_state: AssetState
    triggered_by: str
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    timestamp: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "action": self.action.value,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "triggered_by": self.triggered_by,
            "reason": self.reason,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }

    @classmethod
    def create(
        cls,
        asset_id: str,
        asset_type: str,
        action: LifecycleAction,
        from_state: AssetState,
        to_state: AssetState,
        triggered_by: str,
        reason: str = "",
        evidence: dict | None = None,
    ) -> LifecycleRecord:
        now = int(time.time())
        raw = f"{asset_id}{action.value}{now}"
        record_id = hashlib.sha1(raw.encode()).hexdigest()[:12]
        return cls(
            record_id=record_id,
            asset_id=asset_id,
            asset_type=asset_type,
            action=action,
            from_state=from_state,
            to_state=to_state,
            triggered_by=triggered_by,
            reason=reason,
            evidence=evidence or {},
            timestamp=now,
        )


class LifecycleLedger:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def append(self, record: LifecycleRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")

    def list_all(self) -> list[LifecycleRecord]:
        if not self.path.exists():
            return []
        records: list[LifecycleRecord] = []
        for line in self.path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                data = json.loads(line)
                records.append(LifecycleRecord(
                    record_id=data["record_id"],
                    asset_id=data["asset_id"],
                    asset_type=data["asset_type"],
                    action=LifecycleAction(data["action"]),
                    from_state=AssetState(data["from_state"]),
                    to_state=AssetState(data["to_state"]),
                    triggered_by=data["triggered_by"],
                    reason=data.get("reason", ""),
                    evidence=data.get("evidence", {}),
                    timestamp=data.get("timestamp", 0),
                ))
        return records

    def for_asset(self, asset_id: str) -> list[LifecycleRecord]:
        return [r for r in self.list_all() if r.asset_id == asset_id]
