from __future__ import annotations

from typing import Any

from argus.assets import CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.capability_resolution.resolver import CapabilityResolver
from argus.capability_resolution.reporting import ResolutionReporter
from argus.handoff import HandoffManager, HandoffRecord
from argus.ledger import EventLedger, LearningLedger
from argus.ledger.learning import CandidateLearningItem
from argus.ledger.models import EventRecord
from argus.storage import ContractStorage


class QueryApplication:
    """Cross-cutting read-only queries across contracts, packs, roles, learnings, and assets."""

    def __init__(
        self,
        storage: ContractStorage,
        event_ledger: EventLedger,
        learning_ledger: LearningLedger,
        inventory: CapabilityInventory,
        pack_store: CapabilityPackStore,
        role_store: RolePackStore,
        handoff_mgr: HandoffManager,
        resolution_reports_dir: str = "",
    ) -> None:
        self.storage = storage
        self.event_ledger = event_ledger
        self.learning_ledger = learning_ledger
        self.inventory = inventory
        self.pack_store = pack_store
        self.role_store = role_store
        self.handoff_mgr = handoff_mgr
        self._resolver = CapabilityResolver(inventory, pack_store)
        self._resolution_reporter = ResolutionReporter(resolution_reports_dir) if resolution_reports_dir else None

    def query_contracts(
        self, *, status: str = "", role_id: str = "", contract_id: str = "", workspace: str = ""
    ) -> list[dict[str, Any]]:
        contracts = self.storage.list_contracts()
        if contract_id:
            contracts = [c for c in contracts if c.id == contract_id]
        if status:
            contracts = [c for c in contracts if c.status == status]
        results: list[dict[str, Any]] = []
        for c in contracts:
            d = c.to_dict()
            d["handoffs"] = [h.to_dict() for h in self.handoff_mgr.list_by_contract(c.id)]
            if role_id:
                d["handoffs"] = [h for h in d["handoffs"] if h["from_role_id"] == role_id or h["to_role_id"] == role_id]
            results.append(d)
        return results

    def query_roles(self, *, role_id: str = "", workspace: str = "") -> list[dict[str, Any]]:
        roles = self.role_store.list_latest()
        if role_id:
            roles = [r for r in roles if r.role_id == role_id]
        results: list[dict[str, Any]] = []
        for r in roles:
            d = r.to_dict()
            d["handoffs"] = [h.to_dict() for h in self.handoff_mgr.list_by_role(r.role_id)]
            results.append(d)
        return results

    def query_packs(self, *, pack_id: str = "") -> list[dict[str, Any]]:
        packs = self.pack_store.list_latest()
        if pack_id:
            packs = [p for p in packs if p.pack_id == pack_id]
        return [p.to_dict() for p in packs]

    def query_learnings(
        self,
        *,
        contract_id: str = "",
        role: str = "",
        learning_type: str = "",
        scope: str = "",
        min_confidence: float = 0.0,
    ) -> list[dict[str, Any]]:
        items = self.learning_ledger.list_items()
        if contract_id:
            items = [i for i in items if contract_id in i.evidence_refs]
        if learning_type:
            items = [i for i in items if i.type == learning_type]
        if scope:
            items = [i for i in items if i.scope == scope]
        if min_confidence > 0:
            items = [i for i in items if i.confidence >= min_confidence]
        return [i.to_dict() for i in items]

    def query_assets(
        self,
        *,
        asset_type: str = "",
        status: str = "",
        agent: str = "",
        risk: str = "",
        asset_id: str = "",
    ) -> list[dict[str, Any]]:
        assets = self.inventory.list_assets()
        if asset_id:
            assets = [a for a in assets if a.id == asset_id]
        if asset_type:
            assets = [a for a in assets if a.type == asset_type]
        if status:
            assets = [a for a in assets if a.status == status]
        if agent:
            assets = [a for a in assets if agent in a.agents]
        if risk:
            assets = [a for a in assets if a.risk_score == risk]
        return [a.to_dict() for a in assets]

    def check_role(self, role_id: str, version: int | None = None) -> dict[str, Any]:
        return self.role_store.check(role_id, self.inventory.list_assets(), version).to_dict()

    def run_resolution(self, gap_name: str, gap_description: str = "") -> dict[str, Any]:
        resolutions = self._resolver.resolve(
            gaps=[{"name": gap_name, "description": gap_description or gap_name}],
            contract_id="",
            role_id="",
        )
        return [r.to_dict() for r in resolutions]

    def submit_event(self, raw: dict[str, Any]) -> str:
        record = EventRecord.create(
            source=raw.get("source", "mcp"),
            agent=raw.get("agent", "unknown"),
            contract_id=raw.get("contract_id", ""),
            role=raw.get("role", ""),
            workspace=raw.get("workspace", ""),
            session=raw.get("session", ""),
            timestamp=raw.get("timestamp", ""),
            event_type=raw.get("event_type", "unknown"),
            evidence=raw.get("evidence", raw),
        )
        self.event_ledger.append(record)
        return record.id

    def list_events(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.event_ledger.list_events()]

    def handoff_role(
        self,
        *,
        from_role_id: str,
        to_role_id: str,
        contract_id: str = "",
        context: dict[str, Any] | None = None,
        handoff_reason: str = "",
    ) -> dict[str, Any]:
        record = self.handoff_mgr.create(
            from_role_id=from_role_id,
            to_role_id=to_role_id,
            contract_id=contract_id,
            context=context,
            handoff_reason=handoff_reason,
        )
        return record.to_dict()

    def list_handoffs(self, *, role_id: str = "", contract_id: str = "") -> list[dict[str, Any]]:
        if contract_id:
            records = self.handoff_mgr.list_by_contract(contract_id)
        elif role_id:
            records = self.handoff_mgr.list_by_role(role_id)
        else:
            records = self.handoff_mgr.list_all()
        return [r.to_dict() for r in records]
