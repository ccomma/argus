"""分析子系统入口，导出 ROI 计算器和仪表盘报告工具。"""

from __future__ import annotations

from argus.analytics.calculator import ROICalculator
from argus.analytics.models import ContractROI, DashboardReport, LearningROI, RoleROI
from argus.analytics.reporting import DashboardReporter

__all__ = [
    "ContractROI",
    "DashboardReport",
    "DashboardReporter",
    "LearningROI",
    "ROICalculator",
    "RoleROI",
]
