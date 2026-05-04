from __future__ import annotations

"""治理（Governance）子系统模块。

提供系统治理报告的生成能力，从合同、学习账本、资产清单和能力包
等多个数据源聚合信息，生成结构化的治理发现、待处理操作和低风险维护日志。
"""

from argus.governance.models import GovernanceFinding, GovernanceReportResult, PendingAction
from argus.governance.reporting import GovernanceReporter


__all__ = [
    "GovernanceFinding",
    "GovernanceReportResult",
    "GovernanceReporter",
    "PendingAction",
]
