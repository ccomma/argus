from __future__ import annotations

"""账本事件模型模块。

定义 EventRecord 数据类——事件账本中每条记录的标准结构。
每条事件记录包含事件来源、代理信息、关联合同、角色、
工作空间等完整的审计上下文，用于支撑学习提取和治理审查。
"""

import json
from dataclasses import asdict, dataclass, field
from hashlib import sha1
from typing import Any


@dataclass(frozen=True)
class EventRecord:
    """事件账本中的单条事件记录。

    作为 Argus 系统中所有可审计事件的标准载体。每条记录不可变（frozen），
    通过 SHA1 摘要生成唯一 ID，确保事件的可追溯性和防篡改性。

    关键字段说明：
    - source: 事件来源（如 contract_evidence、codex_transcript）
    - agent: 产生事件的代理标识
    - contract_id / contract_version: 关联的工作合同
    - event_type: 事件类型（如 deliverable_evaluated、user_correction）
    - evidence / execution_evidence / risk_metadata: 多层证据信息
    """

    id: str
    source: str
    agent: str
    contract_id: str
    contract_version: int | None
    role: str
    workspace: str
    session: str
    timestamp: int | str
    event_type: str
    evidence: dict[str, Any] = field(default_factory=dict)
    execution_evidence: dict[str, Any] = field(default_factory=dict)
    risk_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventRecord:
        return cls(**data)

    @classmethod
    def create(
        cls,
        *,
        source: str,
        event_type: str,
        evidence: dict[str, Any],
        agent: str = "unknown",
        contract_id: str = "",
        contract_version: int | None = None,
        role: str = "",
        workspace: str = "",
        session: str = "",
        timestamp: int | str = "",
        execution_evidence: dict[str, Any] | None = None,
        risk_metadata: dict[str, Any] | None = None,
    ) -> EventRecord:
        """工厂方法：基于关键字段创建事件记录。

        流程：
        1. 组装核心负载数据（source, agent, contract 等）
        2. 对负载进行 SHA1 摘要计算，生成确定性的事件 ID
        3. 基于内容生成 ID 确保相同事件不会产生重复记录

        这样设计的好处是：事件 ID 由其内容决定，支持幂等写入。
        """
        payload = {
            "source": source,
            "agent": agent,
            "contract_id": contract_id,
            "contract_version": contract_version,
            "role": role,
            "workspace": workspace,
            "session": session,
            "timestamp": timestamp,
            "event_type": event_type,
            "evidence": evidence,
            "execution_evidence": execution_evidence or {},
        }
        digest = sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        return cls(
            id=f"event-{digest}",
            source=source,
            agent=agent,
            contract_id=contract_id,
            contract_version=contract_version,
            role=role,
            workspace=workspace,
            session=session,
            timestamp=timestamp,
            event_type=event_type,
            evidence=evidence,
            execution_evidence=execution_evidence or {},
            risk_metadata=risk_metadata or {},
        )
