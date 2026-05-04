"""治理应用服务，聚合跨领域数据生成治理健康报告。

治理报告是 Argus 的中枢诊断工具，综合评估合约、学习、资产、能力包和角色包
五个维度的健康状态，发现重复、冲突、风险等问题。
"""

from __future__ import annotations

from pathlib import Path

from argus.assets import CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.governance import GovernanceReporter, GovernanceReportResult
from argus.ledger import LearningLedger
from argus.storage import ContractStorage


class GovernanceApplication:
    """治理子系统的应用门面，聚合全部治理数据生成诊断报告。"""

    def __init__(
        self,
        contract_storage: ContractStorage,
        learning_ledger: LearningLedger,
        inventory: CapabilityInventory,
        pack_store: CapabilityPackStore,
        role_store: RolePackStore,
        reports_dir: str | Path,
    ) -> None:
        self.contract_storage = contract_storage
        self.learning_ledger = learning_ledger
        self.inventory = inventory
        self.pack_store = pack_store
        self.role_store = role_store
        self.reports_dir = Path(reports_dir)

    def write_report(self) -> GovernanceReportResult:
        """综合合约、学习、资产、能力包和角色包五个维度生成治理报告。

        1. 收集各子系统的当前状态快照
        2. 执行去重、冲突检测、风险评估等治理检查
        3. 生成 Markdown 和 JSON 双格式报告
        """
        return GovernanceReporter(self.reports_dir).write(
            contract_storage=self.contract_storage,
            learning_ledger=self.learning_ledger,
            inventory=self.inventory,
            pack_store=self.pack_store,
            role_store=self.role_store,
        )
