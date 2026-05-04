"""生命周期数据模型：定义资产状态机、状态转换表和相关数据结构。

状态机是 Argus 治理的核心基础设施，确保每个能力资产的状态转换
严格遵循预定义规则，所有变更记录到 LifecycleLedger 形成审计追踪。
"""

from __future__ import annotations

import enum
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class AssetState(enum.Enum):
    """资产状态枚举。

    DRAFT: 草稿态（创建后初始状态）
    ACTIVE: 活跃态（可正常使用）
    DISABLED: 禁用态（临时关闭）
    ISOLATED: 隔离态（安全隔离中）
    DEPRECATED: 弃用态（即将移除）
    ARCHIVED: 归档态（历史保留）
    DELETED: 删除态（终态，不可逆）
    """
    DRAFT = "draft"
    ACTIVE = "active"
    DISABLED = "disabled"
    ISOLATED = "isolated"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    DELETED = "deleted"


class LifecycleAction(enum.Enum):
    """生命周期操作枚举。

    定义可对资产执行的状态变更操作，每种操作只能在特定状态下执行。
    """
    CREATE = "create"
    ACTIVATE = "activate"
    DISABLE = "disable"
    ISOLATE = "isolate"
    RELEASE = "release"
    DEPRECATE = "deprecate"
    ARCHIVE = "archive"
    DELETE = "delete"
    ROLLBACK = "rollback"


# 状态转换表：定义每个状态下可执行的操作及其目标状态。
# 采用两层 dict 结构，外层 key 为当前状态，内层 key 为操作，value 为目标状态。
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
    """资产状态机。

    职责：管理单个资产的合法状态转换。通过 TRANSITIONS 表约束转换规则，
    拒绝非法操作时抛出 ValueError。每个实例追踪一个资产的当前状态。
    """

    def __init__(self, current: AssetState) -> None:
        """初始化状态机，设置当前状态并绑定全局转换表。"""
        self.current = current
        self.transitions = TRANSITIONS

    def can(self, action: LifecycleAction) -> bool:
        """检查在当前状态下是否可以执行指定操作。"""
        return action in self.transitions.get(self.current, {})

    def available_actions(self) -> list[LifecycleAction]:
        """列出当前状态下所有可用的生命周期操作。"""
        return list(self.transitions.get(self.current, {}).keys())

    def apply(self, action: LifecycleAction) -> AssetState:
        """执行状态转换。

        1. 在转换表中查找 (current, action) 对应的目标状态
        2. 若转换不存在，抛出 ValueError（非法操作）
        3. 更新当前状态并返回新状态
        """
        next_state = self.transitions.get(self.current, {}).get(action)
        if next_state is None:
            raise ValueError(f"Cannot {action.value} from {self.current.value}")
        self.current = next_state
        return self.current


def state_machine_for(status: str) -> StateMachine:
    """根据状态字符串创建状态机，非法状态值回退为 DRAFT。"""
    try:
        return StateMachine(AssetState(status))
    except ValueError:
        return StateMachine(AssetState.DRAFT)


@dataclass(frozen=True)
class LifecycleRecord:
    """生命周期变更记录（不可变数据类）。

    每次状态转换产生一条记录，包含操作者、原因、证据和时间戳。
    record_id 基于 asset_id、action 和时间戳的 SHA-1 哈希生成，保证唯一性。
    """
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
        """序列化为字典，枚举值转为字符串。"""
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
        """创建生命周期变更记录。

        1. 用 asset_id + action + 时间戳拼接后 SHA-1 哈希生成 record_id（取前 12 位）
        2. 所有可选字段缺失时使用默认值
        3. 时间戳精确到秒（Unix 时间）
        """
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
    """生命周期审计账本。

    职责：持久化记录所有资产的状态变更操作。采用追加写入 JSONL 格式，
    保证写入的原子性（单行追加）和可追溯性。支持全量列表和按资产筛选。
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def append(self, record: LifecycleRecord) -> None:
        """追加一条变更记录到账本（JSONL 格式，一行一条记录）。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")

    def list_all(self) -> list[LifecycleRecord]:
        """读取账本中所有变更记录，文件不存在时返回空列表。"""
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
        """按资产 ID 筛选变更记录。"""
        return [r for r in self.list_all() if r.asset_id == asset_id]
