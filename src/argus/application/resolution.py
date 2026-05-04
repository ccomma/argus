from __future__ import annotations

from pathlib import Path

from argus.assets import CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.capability_resolution import CapabilityResolver, CapabilityResolution, ResolutionReport, ResolutionReporter
from argus.governance import GovernanceFinding, GovernanceReporter, GovernanceReportResult
from argus.ledger import LearningLedger
from argus.storage import ContractStorage


class ResolutionApplication:
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
        self.resolver = CapabilityResolver(inventory, pack_store, role_store)

    def resolve_all(self) -> list[CapabilityResolution]:
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
        return ResolutionReporter(self.reports_dir).write(self.resolve_all())


def _load_findings(result: GovernanceReportResult) -> list[GovernanceFinding]:
    import json
    data = json.loads(result.json_path.read_text(encoding="utf-8"))
    return [
        GovernanceFinding(**{k: v for k, v in f.items() if k in GovernanceFinding.__dataclass_fields__})
        for f in data.get("findings", [])
    ]
