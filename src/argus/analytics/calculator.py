from __future__ import annotations

from argus.assets import CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.handoff import HandoffManager
from argus.ledger import EventLedger, LearningLedger
from argus.storage import ContractStorage

from .models import ContractROI, LearningROI, RoleROI


class ROICalculator:
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
        contracts = self.storage.list_contracts()
        total = len(contracts)
        by_status: dict[str, int] = {}
        completeness_sum = 0.0
        question_rounds_sum = 0
        change_entries = 0
        for c in contracts:
            by_status[c.status] = by_status.get(c.status, 0) + 1
            completeness_sum += c.completeness_score.overall_score
            question_rounds_sum += len(c.answers) if hasattr(c, "answers") and c.answers else len(c.question_history) if hasattr(c, "question_history") else 0
            change_entries += len(c.change_history)
        avg_completeness = completeness_sum / total if total > 0 else 0.0
        avg_rounds = question_rounds_sum // total if total > 0 else 0

        # Evaluate deliverable pass rate from events
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
        roles = self.role_store.list_latest()
        total_roles = len(roles)
        handoffs = self.handoff_mgr.list_all()
        total_handoffs = len(handoffs)
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
