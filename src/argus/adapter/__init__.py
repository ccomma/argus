"""适配器模块：将外部 AI Agent 的对话转录数据标准化为 Argus 内部事件记录。

本模块导出所有适配器基类及其具体实现，供上层调用方统一接入不同 Agent 来源的数据。
"""

from __future__ import annotations

from argus.adapter.base import BaseAdapter
from argus.adapter.claude import ClaudeAdapter
from argus.adapter.codex import CodexAdapter

__all__ = [
    "BaseAdapter",
    "ClaudeAdapter",
    "CodexAdapter",
]
