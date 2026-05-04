"""Codex 适配器：将 Codex Agent 转录数据接入 Argus 事件账本。

Codex 转录文件使用 event_type 字段标识事件类型，evidence 字段承载具体内容。
本适配器封装了 TranscriptIngestor，支持批量导入转录文件。
"""

from __future__ import annotations

from argus.ledger.ingestion import TranscriptIngestor
from argus.ledger.models import EventRecord
from argus.ledger.store import EventLedger

from .base import BaseAdapter


class CodexAdapter(BaseAdapter):
    """Codex Agent 适配器。

    职责：读取 Codex 格式的转录数据，标准化后写入 Argus EventLedger。
    内部持有一个 TranscriptIngestor 实例用于批量导入完整转录文件。
    """

    def __init__(self, ledger: EventLedger) -> None:
        """初始化适配器，绑定目标账本并创建转录导入器。"""
        self._ledger = ledger
        self._ingestor = TranscriptIngestor(ledger)

    @property
    def agent_name(self) -> str:
        return "codex"

    def normalize_event(self, raw: dict) -> EventRecord:
        """将 Codex 原始记录标准化为 EventRecord。

        1. 从 raw 字典提取 session、timestamp、event_type 字段
        2. evidence 优先使用 raw["evidence"]，缺失时回退为整个 raw 字典
        3. 调用 EventRecord.create 构造标准化记录
        """
        return EventRecord.create(
            source="codex_adapter",
            agent="codex",
            session=raw.get("session", ""),
            timestamp=raw.get("timestamp", ""),
            event_type=raw.get("event_type", "unknown"),
            evidence=raw.get("evidence", raw),
        )

    def submit_event(self, event: EventRecord) -> str:
        """提交事件到账本并返回事件 ID。"""
        self._ledger.append(event)
        return event.id

    def ingest_transcript(self, path: str) -> int:
        """批量导入转录文件，返回成功导入的事件数量。

        委托给 TranscriptIngestor 处理文件解析和批量写入。
        """
        return self._ingestor.ingest(path)
