from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Playbook:
    playbook_id: str
    name: str
    description: str = ""
    question_strategies: list[str] = field(default_factory=list)
    confirmation_points: list[str] = field(default_factory=list)
    deliverable_templates: list[dict[str, Any]] = field(default_factory=list)
    contract_templates: list[dict[str, Any]] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    capability_pack_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    version: int = 1
    created_at: int = 0
    updated_at: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "playbook_id": self.playbook_id,
            "name": self.name,
            "description": self.description,
            "question_strategies": self.question_strategies,
            "confirmation_points": self.confirmation_points,
            "deliverable_templates": self.deliverable_templates,
            "contract_templates": self.contract_templates,
            "roles": self.roles,
            "capability_pack_ids": self.capability_pack_ids,
            "tags": self.tags,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Playbook:
        return cls(
            playbook_id=data["playbook_id"],
            name=data["name"],
            description=data.get("description", ""),
            question_strategies=data.get("question_strategies", []),
            confirmation_points=data.get("confirmation_points", []),
            deliverable_templates=data.get("deliverable_templates", []),
            contract_templates=data.get("contract_templates", []),
            roles=data.get("roles", []),
            capability_pack_ids=data.get("capability_pack_ids", []),
            tags=data.get("tags", []),
            version=data.get("version", 1),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
        )

    @classmethod
    def create(
        cls,
        name: str,
        description: str = "",
        question_strategies: list[str] | None = None,
        confirmation_points: list[str] | None = None,
        deliverable_templates: list[dict] | None = None,
        contract_templates: list[dict] | None = None,
        roles: list[str] | None = None,
        capability_pack_ids: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Playbook:
        now = int(time.time())
        raw = f"{name}{now}"
        playbook_id = hashlib.sha1(raw.encode()).hexdigest()[:12]
        return cls(
            playbook_id=playbook_id,
            name=name,
            description=description,
            question_strategies=question_strategies or [],
            confirmation_points=confirmation_points or [],
            deliverable_templates=deliverable_templates or [],
            contract_templates=contract_templates or [],
            roles=roles or [],
            capability_pack_ids=capability_pack_ids or [],
            tags=tags or [],
            version=1,
            created_at=now,
            updated_at=now,
        )


class PlaybookRegistry:
    def __init__(self, store_dir: str | Path) -> None:
        self.store_dir = Path(store_dir)

    def save(self, playbook: Playbook) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        path = self.store_dir / f"{playbook.playbook_id}.json"
        path.write_text(json.dumps(playbook.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    def load(self, playbook_id: str) -> Playbook | None:
        path = self.store_dir / f"{playbook_id}.json"
        if not path.exists():
            return None
        return Playbook.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_all(self) -> list[Playbook]:
        if not self.store_dir.exists():
            return []
        results: list[Playbook] = []
        for f in sorted(self.store_dir.glob("*.json")):
            results.append(Playbook.from_dict(json.loads(f.read_text(encoding="utf-8"))))
        return results

    def delete(self, playbook_id: str) -> bool:
        path = self.store_dir / f"{playbook_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
