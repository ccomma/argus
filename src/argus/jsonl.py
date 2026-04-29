from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar


T = TypeVar("T")


class AppendOnlyJsonlStore(Generic[T]):
    """Small append-only JSONL store for local Argus ledgers."""

    def __init__(
        self,
        path: str | Path,
        *,
        serializer: Callable[[T], dict[str, Any]],
        deserializer: Callable[[dict[str, Any]], T],
        identity: Callable[[T], str],
    ) -> None:
        self.path = Path(path)
        self._serializer = serializer
        self._deserializer = deserializer
        self._identity = identity

    def append(self, item: T) -> bool:
        existing_ids = {self._identity(existing) for existing in self.list_items()}
        if self._identity(item) in existing_ids:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(self._serializer(item), sort_keys=True) + "\n")
        return True

    def append_many(self, items: list[T]) -> int:
        existing_ids = {self._identity(existing) for existing in self.list_items()}
        pending: list[T] = []
        for item in items:
            item_id = self._identity(item)
            if item_id in existing_ids:
                continue
            existing_ids.add(item_id)
            pending.append(item)
        if not pending:
            return 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            for item in pending:
                handle.write(json.dumps(self._serializer(item), sort_keys=True) + "\n")
        return len(pending)

    def list_items(self) -> list[T]:
        if not self.path.exists():
            return []
        return [
            self._deserializer(json.loads(line))
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
