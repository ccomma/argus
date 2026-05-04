from __future__ import annotations

"""治理报告模型模块。

定义治理子系统使用的核心数据模型：
- GovernanceFinding: 单个治理发现（如重复资产、过期资产、高风险资产等）
- PendingAction: 待处理的操作建议（需要确认或审查的行动）
- GovernanceReportResult: 治理报告的产物路径集合
"""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GovernanceFinding:
    """单个治理发现。

    治理报告的核心单元。每条发现涵盖了某个具体问题的类别、
    严重程度、涉及的主体、问题摘要和建议措施。

    发现类别包括：
    - dedupe: 重复的资产或学习项
    - stale: 过期的资产（非 ACTIVE 状态）
    - risk: 高风险资产或能力包
    - work_contract: 合同完整性问题
    - role: 角色包配置问题
    """

    category: str
    severity: str
    subject_id: str
    summary: str
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PendingAction:
    """待处理操作。

    从治理发现中提炼出的可执行操作项。每条操作明确了操作类型、
    风险级别、涉及主体、操作摘要和是否需要人工确认。

    操作类型示例：
    - question_strategy_improvement: 改进提问策略
    - deliverable_contract_improvement: 改进交付物合约
    - dedupe_review / stale_review / risk_review / role_review: 各类审查
    """

    type: str
    risk_level: str
    subject_id: str
    summary: str
    requires_confirmation: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GovernanceReportResult:
    """治理报告的产物路径集合。

    一次完整的治理报告生成会产生以下文件：
    - markdown_path: 人类可读的治理报告（.md）
    - json_path: 结构化完整报告（.json）
    - low_risk_log_path: 低风险维护日志（.json）
    - pending_actions_path: 待处理操作列表（.json）
    """

    markdown_path: Path
    json_path: Path
    low_risk_log_path: Path
    pending_actions_path: Path
