"""Claude 适配器：将 Claude Code 对话转录数据接入 Argus 事件账本。

Claude 转录文件为 JSONL 格式，每行一条记录。与 Codex 格式的差异：
- 使用 ``type`` 字段替代 ``event_type``
- 使用 ``message`` 字段承载内容
- 工具调用结果存储在 ``tool_use`` 块中
本适配器处理这些字段映射差异，并将数据标准化为 EventRecord。
"""

from __future__ import annotations

import json
from pathlib import Path

from argus.ledger.models import EventRecord
from argus.ledger.store import EventLedger

from .base import BaseAdapter


class ClaudeAdapter(BaseAdapter):
    """Claude Code 转录适配器。

    职责：读取 Claude Code 的 JSONL 转录文件，将每条记录标准化为 Argus EventRecord。
    处理 Claude 特有的字段命名（type -> event_type, message -> evidence,
    session_id -> session），屏蔽不同 Agent 来源的数据格式差异。
    """

    def __init__(self, ledger: EventLedger) -> None:
        """初始化适配器，绑定目标事件账本。"""
        self._ledger = ledger

    @property
    def agent_name(self) -> str:
        return "claude"

    def normalize_event(self, raw: dict) -> EventRecord:
        """将 Claude 原始记录标准化为 EventRecord。

        1. 事件类型优先使用 Claude 的 ``type`` 字段，回退到 ``event_type``
        2. evidence 优先取 ``message`` 字段（若为字典），否则使用整个 raw 记录
        3. session 优先使用 ``session_id``（Claude 命名），回退到 ``session``
        4. 调用 EventRecord.create 构造标准化记录
        """
        # Claude 使用 'type' 而非 'event_type'，兼容两种命名
        event_type = raw.get("type") or raw.get("event_type", "unknown")
        # Claude 的消息内容在 'message' 字段中，优先提取
        evidence: dict = raw.get("message") if isinstance(raw.get("message"), dict) else raw
        return EventRecord.create(
            source="claude_adapter",
            agent="claude",
            # session_id 是 Claude 的字段名，回退到 session
            session=raw.get("session_id") or raw.get("session", ""),
            timestamp=raw.get("timestamp", ""),
            event_type=event_type,
            evidence=evidence,
        )

    def submit_event(self, event: EventRecord) -> str:
        """提交事件到账本并返回事件 ID。"""
        self._ledger.append(event)
        return event.id

    def ingest_transcript(self, path: str | Path) -> int:
        """批量导入 Claude JSONL 转录文件，返回成功导入的事件数量。

        1. 逐行读取 JSONL 文件，跳过空行
        2. 每行解析为 JSON 字典，通过 normalize_event 标准化
        3. 所有事件收集完毕后，批量写入账本（一次 I/O）
        4. 遇到非法的 JSON 行时抛出 ValueError，携带行号便于定位
        """
        events: list[EventRecord] = []
        for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                # 携带行号信息，便于排查损坏的转录文件
                raise ValueError(f"invalid transcript JSONL at line {line_number}: {exc.msg}") from exc
            events.append(self.normalize_event(raw))
        return self._ledger.append_many(events)
