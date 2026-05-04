"""应用服务层入口模块，统一导出所有 Application 类。

Application 层是 Argus 能力操作系统的对外门面，将底层领域对象
（资产、学习、包、存储等）编排为面向用例的 9 个聚合服务。
"""

from __future__ import annotations

from argus.application.assets import AssetApplication
from argus.application.governance import GovernanceApplication
from argus.application.learning import LearningApplication
from argus.application.ledger import LedgerApplication
from argus.application.packs import CapabilityPackApplication, RolePackApplication
from argus.application.modification import ModificationApplication
from argus.application.query import QueryApplication
from argus.application.resolution import ResolutionApplication


__all__ = [
    "AssetApplication",
    "CapabilityPackApplication",
    "GovernanceApplication",
    "LearningApplication",
    "LedgerApplication",
    "ModificationApplication",
    "QueryApplication",
    "ResolutionApplication",
    "RolePackApplication",
]
