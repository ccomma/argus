"""交接模块：管理 AI Agent 角色之间的上下文交接记录。

在能力操作系统中，不同 Agent 角色之间需要移交工作上下文。
本模块提供 HandoffManager 用于创建和查询交接记录，HandoffRecord 为交接数据模型。
"""

from __future__ import annotations

from argus.handoff.manager import HandoffManager
from argus.handoff.models import HandoffRecord

__all__ = [
    "HandoffManager",
    "HandoffRecord",
]
