"""能力缺口解析应用服务，从多源信号中发现并解决能力差距。

Resolution 是 Argus 的核心决策环节，将学习项、包检查、治理发现
三条信号源汇聚为统一的能力缺口列表，并通过 CapabilityResolver
给出每个缺口的处置建议（复用/配置/创建/安装等）。
"""

from __future__ import annotations

from pathlib import Path

from argus.assets import CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.capability_resolution import CapabilityResolver, CapabilityResolution, ResolutionReport, ResolutionReporter
from argus.governance import GovernanceFinding, GovernanceReporter, GovernanceReportResult
from argus.ledger import LearningLedger
from argus.storage import ContractStorage


class ResolutionApplication:
    """能力缺口解析的应用门面，汇总多源信号并给出处置建议。"""

    def __init__(
        self,
        inventory: CapabilityInventory,
        learning_ledger: LearningLedger,
        pack_store: CapabilityPackStore,
        role_store: RolePackStore,
        contract_storage: ContractStorage,
        reports_dir: str | Path,
    ) -> None:
        self.inventory = inventory
        self.learning_ledger = learning_ledger
        self.pack_store = pack_store
        self.role_store = role_store
        self.contract_storage = contract_storage
        self.reports_dir = Path(reports_dir)
        # 能力解析器：将缺口信号映射为具体的处置决策
        self.resolver = CapabilityResolver(inventory, pack_store, role_store)

    def resolve_all(self) -> list[CapabilityResolution]:
        """全面解析能力缺口，汇集三条信号源：

        1. 候选学习项：反向学习目标指向能力包/合约的学习信号
        2. 能力包完整性检查：能力包中缺失引用的资产条目
        3. 治理发现：治理报告中的去重、风险、角色类发现

        返回去重后的处置建议列表。
        """
        resolutions: list[CapabilityResolution] = []

        learnings = self.learning_ledger.list_items()
        resolutions.extend(self.resolver.resolve_from_learnings(learnings))

        for pack in self.pack_store.list_latest():
            from argus.capability_packs import CapabilityPackChecker
            report = CapabilityPackChecker().check(pack, self.inventory.list_assets())
            missing = [f"Pack {pack.pack_id}: missing asset {eid}" for eid in report.missing_required_entry_ids]
            resolutions.extend(
                self.resolver.resolve(
                    gaps=[{"gap_id": f"pack-{pack.pack_id}-{i}", "gap_description": m, "source": "pack_check"} for i, m in enumerate(missing)],
                    contract_id="",
                )
            )

        governance_result = GovernanceReporter(self.reports_dir).write(
            contract_storage=self.contract_storage,
            learning_ledger=self.learning_ledger,
            inventory=self.inventory,
            pack_store=self.pack_store,
            role_store=self.role_store,
        )
        findings = _load_findings(governance_result)
        resolutions.extend(self.resolver.resolve_from_findings(findings))

        return resolutions

    def write_report(self) -> ResolutionReport:
        """执行全面解析并以 Markdown/JSON 双格式生成报告。"""
        return ResolutionReporter(self.reports_dir).write(self.resolve_all())


def _load_findings(result: GovernanceReportResult) -> list[GovernanceFinding]:
    """从治理报告的 JSON 文件中反序列化治理发现列表。

    GovernanceFinding 使用 __dataclass_fields__ 进行字段过滤，
    确保只构造模型定义中存在的字段，兼容 JSON 中的额外键。
    """
    import json
    data = json.loads(result.json_path.read_text(encoding="utf-8"))
    return [
        GovernanceFinding(**{k: v for k, v in f.items() if k in GovernanceFinding.__dataclass_fields__})
        for f in data.get("findings", [])
    ]
