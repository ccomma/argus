from __future__ import annotations

import json
from pathlib import Path
from time import time

from argus.storage import ContractStorage

from .models import CapabilityPackBinding, CapabilityPackManifest
from .serialization import canonical_json, content_hash


class CapabilityPackStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def write(self, manifest: CapabilityPackManifest) -> Path:
        path = self.manifest_path(manifest.pack_id, manifest.version)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json(manifest.to_dict()) + "\n", encoding="utf-8")
        return path

    def load(self, pack_id: str, version: int | None = None) -> tuple[CapabilityPackManifest, str]:
        resolved_version = version if version is not None else self.latest_version(pack_id)
        path = self.manifest_path(pack_id, resolved_version)
        manifest = CapabilityPackManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))
        return manifest, content_hash(manifest)

    def list_latest(self) -> list[CapabilityPackManifest]:
        if not self.root.exists():
            return []
        manifests: list[CapabilityPackManifest] = []
        for pack_dir in sorted(path for path in self.root.iterdir() if path.is_dir()):
            manifest, _ = self.load(pack_dir.name)
            manifests.append(manifest)
        return manifests

    def manifest_path(self, pack_id: str, version: int) -> Path:
        return self.root / pack_id / f"{version}.json"

    def latest_version(self, pack_id: str) -> int:
        pack_dir = self.root / pack_id
        versions = sorted(int(path.stem) for path in pack_dir.glob("*.json") if path.stem.isdigit())
        if not versions:
            raise FileNotFoundError(f"capability pack not found: {pack_id}")
        return versions[-1]

    def next_version(self, pack_id: str) -> int:
        try:
            return self.latest_version(pack_id) + 1
        except FileNotFoundError:
            return 1


class CapabilityPackBindingStore:
    def __init__(self, storage: ContractStorage) -> None:
        self.storage = storage

    def bind(
        self,
        *,
        contract_id: str,
        pack: CapabilityPackManifest,
        content_hash: str,
        rationale: str,
    ) -> CapabilityPackBinding:
        contract = self.storage.load_contract(contract_id)
        binding = CapabilityPackBinding(
            contract_id=contract.id,
            contract_version=contract.version,
            pack_id=pack.pack_id,
            pack_version=pack.version,
            content_hash=content_hash,
            rationale=rationale,
            bound_at=int(time()),
        )
        event = {
            "event_type": "capability_pack_bound",
            "contract_id": contract.id,
            "contract_version": contract.version,
            "pack_id": pack.pack_id,
            "pack_version": pack.version,
            "content_hash": content_hash,
            "rationale": rationale,
        }
        contract.capability_pack_ref = f"{pack.pack_id}@{pack.version}#{content_hash}"
        contract.execution_evidence.append(event)
        self.storage.save_contract(contract)
        self.storage.append_evidence(contract.id, event)
        self.storage.save_contract_artifact(contract.id, "capability_pack_binding.json", binding.to_dict())
        return binding
