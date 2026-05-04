from __future__ import annotations

from pathlib import Path

from argus.assets import CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.governance import GovernanceReporter, GovernanceReportResult
from argus.ledger import LearningLedger
from argus.storage import ContractStorage


class GovernanceApplication:
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
        return GovernanceReporter(self.reports_dir).write(
            contract_storage=self.contract_storage,
            learning_ledger=self.learning_ledger,
            inventory=self.inventory,
            pack_store=self.pack_store,
            role_store=self.role_store,
        )
