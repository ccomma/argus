"""适配器抽象基类：定义 Agent 转录数据接入 Argus 系统的统一契约。

所有具体适配器（如 CodexAdapter、ClaudeAdapter）均继承此基类，
实现 normalize_event 方法将外部原始记录转换为 EventRecord 标准格式。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from argus.ledger.models import EventRecord


class BaseAdapter(ABC):
    """适配器抽象基类。

    职责：定义将外部 Agent 原始转录数据转换为 Argus EventRecord 的接口契约。
    每个子类对应一种特定的 Agent 来源（Codex、Claude 等），必须实现
    agent_name 属性和 normalize_event 方法。
    """

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """返回适配器对应的 Agent 名称标识（如 'codex'、'claude'）。"""
        ...

    @abstractmethod
    def normalize_event(self, raw: dict) -> EventRecord:
        """将一条原始转录记录标准化为 EventRecord。

        子类必须实现此方法，处理各自来源的字段映射和格式差异。
        """
        ...

    def submit_event(self, event: EventRecord) -> str:
        """提交标准化后的事件记录，默认返回事件 ID。

        子类可覆盖此方法以实现自定义的持久化逻辑（如写入账本）。
        """
        return event.id
