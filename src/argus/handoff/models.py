"""交接记录数据模型：定义角色交接的核心数据结构。

HandoffRecord 是一个不可变数据类，记录角色间的上下文移交信息。
交接记录 ID 基于内容哈希生成，确保相同内容的交接具有确定性的标识符。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha1
from pathlib import Path
from time import time
from typing import Any


@dataclass(frozen=True)
class HandoffRecord:
    """角色交接记录（不可变数据类）。

    记录一次角色间上下文移交的完整信息，包括来源角色、目标角色、
    关联合同、移交原因和上下文数据。ID 通过 SHA-1 哈希生成，保证内容唯一性。
    """
    id: str
    from_role_id: str
    to_role_id: str
    contract_id: str
    context: dict[str, Any]
    created_at: int
    handoff_reason: str

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HandoffRecord:
        """从字典反序列化。"""
        return cls(**data)

    @classmethod
    def create(
        cls,
        *,
        from_role_id: str,
        to_role_id: str,
        contract_id: str = "",
        context: dict[str, Any] | None = None,
        handoff_reason: str = "",
    ) -> HandoffRecord:
        """创建一条新的交接记录。

        1. 用核心字段构建 payload 字典
        2. 对 payload 做 SHA-1 哈希生成确定性的记录 ID（取前 16 位）
        3. 以当前 Unix 时间戳作为创建时间

        使用内容哈希作为 ID 的好处：相同内容的交接始终产生相同的 ID，
        避免重复记录，同时支持幂等创建。
        """
        payload = {
            "from_role_id": from_role_id,
            "to_role_id": to_role_id,
            "contract_id": contract_id,
            "context": context or {},
            "handoff_reason": handoff_reason,
        }
        digest = sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        return cls(
            id=f"handoff-{digest}",
            from_role_id=from_role_id,
            to_role_id=to_role_id,
            contract_id=contract_id,
            context=context or {},
            created_at=int(time()),
            handoff_reason=handoff_reason,
        )
