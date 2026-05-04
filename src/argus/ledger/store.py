from __future__ import annotations

"""事件账本存储模块。

提供 EventLedger 类——基于 AppendOnlyJsonlStore 的事件专用存储层。
封装了 EventRecord 的序列化/反序列化逻辑，为上层提供简洁的事件
追加和查询接口。
"""

from pathlib import Path

from argus.ledger.jsonl import AppendOnlyJsonlStore
from argus.ledger.models import EventRecord


class EventLedger:
    """事件账本存储。

    对 AppendOnlyJsonlStore 进行了一层薄封装，适配 EventRecord 类型。
    负责事件的追加写入、批量写入和列表查询。
    """

    def __init__(self, path: str | Path) -> None:
        """初始化事件账本。

        Args:
            path: 事件账本 JSONL 文件的路径
        """
        self.path = Path(path)
        self._store = AppendOnlyJsonlStore(
            self.path,
            serializer=lambda event: event.to_dict(),
            deserializer=EventRecord.from_dict,
            identity=lambda event: event.id,
        )

    def append(self, event: EventRecord) -> bool:
        """追加单条事件。重复 ID 自动跳过，返回是否实际写入。"""
        return self._store.append(event)

    def append_many(self, events: list[EventRecord]) -> int:
        """批量追加事件。返回实际写入的条数。"""
        return self._store.append_many(events)

    def list_events(self) -> list[EventRecord]:
        """列出所有已记录的事件。"""
        return self._store.list_items()
