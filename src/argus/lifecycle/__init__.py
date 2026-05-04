"""生命周期模块：管理 AI Agent 能力资产的状态转换与审计追踪。

本模块实现资产状态机（StateMachine），定义 DRAFT -> ACTIVE -> ARCHIVED 等状态转换规则。
LifecycleLedger 记录所有状态变更操作，形成完整的审计日志。
"""

from __future__ import annotations

from argus.lifecycle.models import (
    AssetState,
    LifecycleAction,
    LifecycleLedger,
    LifecycleRecord,
    StateMachine,
    state_machine_for,
)

__all__ = [
    "AssetState",
    "LifecycleAction",
    "LifecycleLedger",
    "LifecycleRecord",
    "StateMachine",
    "state_machine_for",
]
