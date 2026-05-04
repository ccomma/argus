from __future__ import annotations

import json
from pathlib import Path
from time import time

from argus.assets import CapabilityAsset

from .checking import CapabilityPackChecker
from .models import CapabilityPackCheckReport, CapabilityPackRef, RoleCapabilityPack, RolePackCheckReport
from .risk import tier_rank
from .serialization import canonical_json
from .stores import CapabilityPackStore


class RolePackStore:
    def __init__(self, root: str | Path, pack_store: CapabilityPackStore) -> None:
        self.root = Path(root)
        self.pack_store = pack_store

    def create(
        self,
        *,
        role_id: str,
        display_name: str,
        required_pack_ids: list[str],
        optional_pack_ids: list[str],
        created_by: str,
        activation_policy: str = "manual",
    ) -> RoleCapabilityPack:
        version = self.next_version(role_id)
        required_refs = [self._pack_ref(pack_id, required=True) for pack_id in required_pack_ids]
        optional_refs = [self._pack_ref(pack_id, required=False) for pack_id in optional_pack_ids]
        risk = _highest_pack_risk(required_refs + optional_refs, self.pack_store)
        role_pack = RoleCapabilityPack(
            role_id=role_id,
            version=version,
            display_name=display_name,
            required_pack_refs=required_refs,
            optional_pack_refs=optional_refs,
            activation_policy=activation_policy,
            risk_level=risk,
            rollback_ref=f"{role_id}@{version - 1}" if version > 1 else "",
            created_at=int(time()),
            created_by=created_by,
        )
        path = self.manifest_path(role_id, version)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json(role_pack.to_dict()) + "\n", encoding="utf-8")
        return role_pack

    def load(self, role_id: str, version: int | None = None) -> RoleCapabilityPack:
        resolved_version = version if version is not None else self.latest_version(role_id)
        return RoleCapabilityPack.from_dict(json.loads(self.manifest_path(role_id, resolved_version).read_text(encoding="utf-8")))

    def list_latest(self) -> list[RoleCapabilityPack]:
        if not self.root.exists():
            return []
        role_packs: list[RoleCapabilityPack] = []
        for role_dir in sorted(path for path in self.root.iterdir() if path.is_dir()):
            role_packs.append(self.load(role_dir.name))
        return role_packs

    def check(self, role_id: str, assets: list[CapabilityAsset], version: int | None = None) -> RolePackCheckReport:
        role_pack = self.load(role_id, version)
        reports: list[CapabilityPackCheckReport] = []
        failed: list[str] = []
        for pack_ref in [*role_pack.required_pack_refs, *role_pack.optional_pack_refs]:
            manifest, _ = self.pack_store.load(pack_ref.pack_id, pack_ref.version)
            report = CapabilityPackChecker().check(manifest, assets)
            reports.append(report)
            if pack_ref.required and not report.complete:
                failed.append(pack_ref.pack_id)
        return RolePackCheckReport(
            role_id=role_pack.role_id,
            version=role_pack.version,
            complete=not failed,
            required_pack_ids=[pack_ref.pack_id for pack_ref in role_pack.required_pack_refs],
            optional_pack_ids=[pack_ref.pack_id for pack_ref in role_pack.optional_pack_refs],
            failed_pack_ids=failed,
            pack_reports=reports,
        )

    def manifest_path(self, role_id: str, version: int) -> Path:
        return self.root / role_id / f"{version}.json"

    def latest_version(self, role_id: str) -> int:
        role_dir = self.root / role_id
        versions = sorted(int(path.stem) for path in role_dir.glob("*.json") if path.stem.isdigit())
        if not versions:
            raise FileNotFoundError(f"role capability pack not found: {role_id}")
        return versions[-1]

    def next_version(self, role_id: str) -> int:
        try:
            return self.latest_version(role_id) + 1
        except FileNotFoundError:
            return 1

    def _pack_ref(self, pack_id: str, *, required: bool) -> CapabilityPackRef:
        manifest, hash_value = self.pack_store.load(pack_id)
        return CapabilityPackRef(
            pack_id=manifest.pack_id,
            version=manifest.version,
            content_hash=hash_value,
            required=required,
        )


def _highest_pack_risk(pack_refs: list[CapabilityPackRef], pack_store: CapabilityPackStore) -> str:
    highest = "low"
    for pack_ref in pack_refs:
        manifest, _ = pack_store.load(pack_ref.pack_id, pack_ref.version)
        if tier_rank(manifest.aggregate_risk_tier_snapshot) > tier_rank(highest):
            highest = manifest.aggregate_risk_tier_snapshot
    return highest
