from __future__ import annotations

from pathlib import Path

from argus.asset_inventory import CapabilityInventory
from argus.asset_linking import CandidateAssetLinker
from argus.asset_models import (
    AssetLearningLink,
    AssetReport,
    AssetScanProfile,
    AssetScanResult,
    CapabilityAsset,
)
from argus.asset_reporting import AssetReporter
from argus.asset_scanning import CapabilityAssetScanner
from argus.capability_packs import (
    CapabilityPackAdvisor,
    CapabilityAdviceReport,
    CapabilityPackBinding,
    CapabilityPackBindingStore,
    CapabilityPackCheckReport,
    CapabilityPackChecker,
    CapabilityPackCreator,
    CapabilityPackManifest,
    CapabilityPackResult,
    CapabilityPackStore,
    RoleCapabilityPack,
    RolePackCheckReport,
    RolePackStore,
)
from argus.ingestion import ContractEvidenceIngestor, TranscriptIngestor
from argus.ledger import EventLedger, EventRecord
from argus.learning import (
    CandidateLearningItem,
    LearningExtractor,
    LearningLedger,
    LearningReport,
    LearningReporter,
)
from argus.storage import ContractStorage


class LedgerApplication:
    def __init__(self, storage: ContractStorage, event_ledger: EventLedger) -> None:
        self.storage = storage
        self.event_ledger = event_ledger

    def ingest_contract(self, contract_id: str) -> int:
        return ContractEvidenceIngestor(self.storage, self.event_ledger).ingest(contract_id)

    def ingest_transcript(self, path: str | Path) -> int:
        return TranscriptIngestor(self.event_ledger).ingest(path)

    def list_events(self) -> list[EventRecord]:
        return self.event_ledger.list_events()


class LearningApplication:
    def __init__(
        self,
        event_ledger: EventLedger,
        learning_ledger: LearningLedger,
        reports_dir: str | Path,
    ) -> None:
        self.event_ledger = event_ledger
        self.learning_ledger = learning_ledger
        self.reports_dir = Path(reports_dir)

    def extract(self) -> int:
        items = LearningExtractor().extract(self.event_ledger.list_events())
        return self.learning_ledger.append_many(items)

    def list_items(self) -> list[CandidateLearningItem]:
        return self.learning_ledger.list_items()

    def write_report(self) -> LearningReport:
        return LearningReporter(self.reports_dir).write(
            self.event_ledger.list_events(),
            self.learning_ledger.list_items(),
        )


class AssetApplication:
    def __init__(
        self,
        inventory: CapabilityInventory,
        reports_dir: str | Path,
        learning_ledger: LearningLedger,
    ) -> None:
        self.inventory = inventory
        self.reports_dir = Path(reports_dir)
        self.learning_ledger = learning_ledger

    def scan(self, profile: AssetScanProfile) -> tuple[AssetScanResult, AssetReport]:
        result = CapabilityAssetScanner().scan_profile(profile)
        self.inventory.write(result.assets)
        report = AssetReporter(self.reports_dir).write(result.assets, warnings=result.warnings)
        return result, report

    def list_assets(self) -> list[CapabilityAsset]:
        return self.inventory.list_assets()

    def write_report(self) -> AssetReport:
        return AssetReporter(self.reports_dir).write(self.inventory.list_assets())

    def link_learnings(self) -> tuple[list[AssetLearningLink], AssetReport]:
        assets = self.inventory.list_assets()
        links = CandidateAssetLinker().link(self.learning_ledger.list_items(), assets)
        report = AssetReporter(self.reports_dir).write(assets, links=links)
        return links, report


class CapabilityPackApplication:
    def __init__(
        self,
        inventory: CapabilityInventory,
        store: CapabilityPackStore,
        contract_storage: ContractStorage,
    ) -> None:
        self.inventory = inventory
        self.store = store
        self.contract_storage = contract_storage

    def propose(
        self,
        *,
        pack_id: str,
        display_name: str,
        required_asset_ids: list[str],
        optional_asset_ids: list[str],
        created_by: str,
        description: str = "",
    ) -> CapabilityPackResult:
        return CapabilityPackCreator(self.store).propose(
            pack_id=pack_id,
            display_name=display_name,
            required_asset_ids=required_asset_ids,
            optional_asset_ids=optional_asset_ids,
            assets=self.inventory.list_assets(),
            created_by=created_by,
            description=description,
        )

    def create(
        self,
        *,
        pack_id: str,
        display_name: str,
        required_asset_ids: list[str],
        optional_asset_ids: list[str],
        created_by: str,
        description: str = "",
    ) -> CapabilityPackResult:
        return CapabilityPackCreator(self.store).create(
            pack_id=pack_id,
            display_name=display_name,
            required_asset_ids=required_asset_ids,
            optional_asset_ids=optional_asset_ids,
            assets=self.inventory.list_assets(),
            created_by=created_by,
            description=description,
        )

    def inspect(self, pack_id: str, version: int | None = None) -> tuple[CapabilityPackManifest, str]:
        return self.store.load(pack_id, version)

    def check(self, pack_id: str, version: int | None = None) -> CapabilityPackCheckReport:
        manifest, _ = self.store.load(pack_id, version)
        return CapabilityPackChecker().check(manifest, self.inventory.list_assets())

    def bind_contract(self, contract_id: str, pack_id: str, rationale: str, version: int | None = None) -> CapabilityPackBinding:
        manifest, hash_value = self.store.load(pack_id, version)
        return CapabilityPackBindingStore(self.contract_storage).bind(
            contract_id=contract_id,
            pack=manifest,
            content_hash=hash_value,
            rationale=rationale,
        )

    def advise(self, required_capabilities: list[str]) -> CapabilityAdviceReport:
        return CapabilityPackAdvisor().advise(
            required_capabilities=required_capabilities,
            assets=self.inventory.list_assets(),
        )


class RolePackApplication:
    def __init__(
        self,
        inventory: CapabilityInventory,
        role_store: RolePackStore,
    ) -> None:
        self.inventory = inventory
        self.role_store = role_store

    def create(
        self,
        *,
        role_id: str,
        display_name: str,
        required_pack_ids: list[str],
        optional_pack_ids: list[str],
        created_by: str,
    ) -> RoleCapabilityPack:
        return self.role_store.create(
            role_id=role_id,
            display_name=display_name,
            required_pack_ids=required_pack_ids,
            optional_pack_ids=optional_pack_ids,
            created_by=created_by,
        )

    def inspect(self, role_id: str, version: int | None = None) -> RoleCapabilityPack:
        return self.role_store.load(role_id, version)

    def check(self, role_id: str, version: int | None = None) -> RolePackCheckReport:
        return self.role_store.check(role_id, self.inventory.list_assets(), version)
