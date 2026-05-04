"""查询应用服务，提供跨领域的只读查询和事件/交接操作。

QueryApplication 是系统中唯一没有副作用查询的门面，
覆盖合约、角色、能力包、学习项、资产五个领域，
同时提供事件提交和角色交接等写操作。
"""

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
    """跨领域查询和事件管理的应用门面。

    覆盖五大查询维度：合约、角色、能力包、学习项、资产。
    同时提供事件提交和角色交接的写操作入口。
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
        resolution_reports_dir: str = "",
    ) -> None:
        self.storage = storage
        self.event_ledger = event_ledger
        self.learning_ledger = learning_ledger
        self.inventory = inventory
        self.pack_store = pack_store
        self.role_store = role_store
        self.handoff_mgr = handoff_mgr
        # 能力解析器用于按需执行缺口分析
        self._resolver = CapabilityResolver(inventory, pack_store)
        self._resolution_reporter = ResolutionReporter(resolution_reports_dir) if resolution_reports_dir else None

    def query_contracts(
        self, *, status: str = "", role_id: str = "", contract_id: str = "", workspace: str = ""
    ) -> list[dict[str, Any]]:
        """按条件查询合约，支持按状态、角色 ID、合约 ID 过滤，附带交接记录。

        1. 获取全部合约并依次应用过滤条件
        2. 为每个合约附加其关联的角色交接记录（handoffs）
        """
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
        """查询角色定义，可按角色 ID 过滤，附带关联的交接记录。"""
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
        """查询能力包，可按包 ID 过滤。"""
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
        """查询候选学习项，支持按合约、类型、作用域和最低置信度过滤。

        1. 获取全部学习项
        2. 依次应用各维度过滤条件（短路式逐层缩减）
        """
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
        """查询能力资产，支持按类型、状态、关联代理、风险等级和 ID 过滤。"""
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
        """对指定角色执行完整性检查并返回结果。"""
        return self.role_store.check(role_id, self.inventory.list_assets(), version).to_dict()

    def run_resolution(self, gap_name: str, gap_description: str = "") -> dict[str, Any]:
        """对单个能力缺口执行解析，返回处置建议列表。"""
        resolutions = self._resolver.resolve(
            gaps=[{"name": gap_name, "description": gap_description or gap_name}],
            contract_id="",
            role_id="",
        )
        return [r.to_dict() for r in resolutions]

    def submit_event(self, raw: dict[str, Any]) -> str:
        """提交原始事件到事件账本，返回生成的事件 ID。

        从原始字典中提取标准事件字段，构造 EventRecord 并持久化。
        """
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
        """列出所有已记录的事件。"""
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
        """创建角色交接记录，将上下文从一个角色传递到另一个角色。

        1. 构造交接记录（包含来源角色、目标角色、上下文和原因）
        2. 持久化到交接管理器
        """
        record = self.handoff_mgr.create(
            from_role_id=from_role_id,
            to_role_id=to_role_id,
            contract_id=contract_id,
            context=context,
            handoff_reason=handoff_reason,
        )
        return record.to_dict()

    def list_handoffs(self, *, role_id: str = "", contract_id: str = "") -> list[dict[str, Any]]:
        """列出交接记录，可按角色 ID 或合约 ID 过滤。"""
        if contract_id:
            records = self.handoff_mgr.list_by_contract(contract_id)
        elif role_id:
            records = self.handoff_mgr.list_by_role(role_id)
        else:
            records = self.handoff_mgr.list_all()
        return [r.to_dict() for r in records]
