"""ROI 计算器，从三大维度评估 Argus 系统的投资回报率。

三个计算维度：
  - ContractROI：合约的完整性、变更频率和交付物通过率
  - LearningROI：学习项的量、质量（置信度）和审核推进情况
  - RoleROI：角色利用率、交接活跃度和能力包密度
"""

from __future__ import annotations

from argus.assets import CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.handoff import HandoffManager
from argus.ledger import EventLedger, LearningLedger
from argus.storage import ContractStorage

from .models import ContractROI, LearningROI, RoleROI


class ROICalculator:
    """ROI 计算器，从合约、学习和角色三个维度生成量化指标。

    需要注入 7 个数据源：合约存储、事件账本、学习账本、
    资产清单、能力包存储、角色包存储和交接管理器。
    """

    def __init__(
        self,
        storage: ContractStorage,
        event_ledger: EventLedger,
        learning_ledger: LearningLedger,
        inventory: CapabilityInventory,
        pack_store: CapabilityPackStore,
        role_store: RolePackStore,
        handoff_mgr: HandoffManager,
    ) -> None:
        self.storage = storage
        self.event_ledger = event_ledger
        self.learning_ledger = learning_ledger
        self.inventory = inventory
        self.pack_store = pack_store
        self.role_store = role_store
        self.handoff_mgr = handoff_mgr

    def contract_roi(self) -> ContractROI:
        """计算工作合约维度的 ROI。

        1. 遍历所有合约，统计状态分布、完整性均值和问询轮次
        2. 从事件账本中过滤 deliverable_evaluated 事件计算交付物通过率
        3. 汇总变更历史条目数以评估合约稳定性
        """
        contracts = self.storage.list_contracts()
        total = len(contracts)
        by_status: dict[str, int] = {}
        completeness_sum = 0.0
        question_rounds_sum = 0
        change_entries = 0
        for c in contracts:
            by_status[c.status] = by_status.get(c.status, 0) + 1
            completeness_sum += c.completeness_score.overall_score
            # 兼容新旧合约模型的问询轮次来源，优先使用 answers，备选 question_history
            question_rounds_sum += len(c.answers) if hasattr(c, "answers") and c.answers else len(c.question_history) if hasattr(c, "question_history") else 0
            change_entries += len(c.change_history)
        avg_completeness = completeness_sum / total if total > 0 else 0.0
        avg_rounds = question_rounds_sum // total if total > 0 else 0

        # 从事件账本中评估交付物通过率
        events = self.event_ledger.list_events()
        deliverable_events = [e for e in events if e.event_type == "deliverable_evaluated"]
        passed = sum(1 for e in deliverable_events if e.execution_evidence.get("status") == "pass")
        pass_rate = passed / len(deliverable_events) if deliverable_events else 0.0

        return ContractROI(
            total_contracts=total,
            by_status=by_status,
            avg_completeness=round(avg_completeness, 3),
            avg_question_rounds=avg_rounds,
            total_change_history_entries=change_entries,
            deliverable_pass_rate=round(pass_rate, 3),
            deliverable_total=len(deliverable_events),
        )

    def learning_roi(self) -> LearningROI:
        """计算候选学习维度的 ROI。

        1. 遍历所有学习项，按类型和作用域分组
        2. 计算平均置信度和审核状态分布（pending vs promoted）
        """
        items = self.learning_ledger.list_items()
        total = len(items)
        by_type: dict[str, int] = {}
        by_scope: dict[str, int] = {}
        confidence_sum = 0.0
        pending = 0
        promoted = 0
        for item in items:
            by_type[item.type] = by_type.get(item.type, 0) + 1
            by_scope[item.scope] = by_scope.get(item.scope, 0) + 1
            confidence_sum += item.confidence
            if item.status == "pending":
                pending += 1
            elif item.status == "promoted":
                promoted += 1
        return LearningROI(
            total_learnings=total,
            by_type=by_type,
            by_scope=by_scope,
            avg_confidence=round(confidence_sum / total, 3) if total > 0 else 0.0,
            pending_count=pending,
            promoted_count=promoted,
        )

    def role_roi(self) -> RoleROI:
        """计算角色维度的 ROI。

        1. 统计角色总数和交接记录总数
        2. 从交接记录中提取活跃角色集合（至少参与过一次交接的角色）
        3. 计算每个角色平均引用的能力包数
        """
        roles = self.role_store.list_latest()
        total_roles = len(roles)
        handoffs = self.handoff_mgr.list_all()
        total_handoffs = len(handoffs)
        # 活跃角色：在任意交接中作为来源或目标的角色
        role_ids = sorted(set(h.from_role_id for h in handoffs) | set(h.to_role_id for h in handoffs))
        total_required = sum(len(r.required_pack_refs) for r in roles)
        total_optional = sum(len(r.optional_pack_refs) for r in roles)
        avg_packs = round((total_required + total_optional) / total_roles, 1) if total_roles > 0 else 0.0
        return RoleROI(
            total_roles=total_roles,
            total_handoffs=total_handoffs,
            roles_used_in_handoffs=role_ids,
            avg_packs_per_role=avg_packs,
        )
