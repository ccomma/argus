from __future__ import annotations

"""角色包组合模块。

提供 RolePackStore 类——管理角色能力包（RoleCapabilityPack）的创建、
存储和完整性检查。角色包将多个能力包组合为一个可激活的"角色"，
定义代理在特定场景下应使用的完整能力集。
"""

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
    """角色能力包的持久化存储和管理。

    与 CapabilityPackStore 类似，以 <root>/<role_id>/<version>.json
    格式存储角色包。额外提供对角色包所引用的所有子能力包的
    批量完整性检查能力。
    """

    def __init__(self, root: str | Path, pack_store: CapabilityPackStore) -> None:
        """初始化角色包存储。

        Args:
            root: 角色包存储根目录
            pack_store: 底层能力包存储，用于解析包引用
        """
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
        """创建一个新的角色能力包版本。

        流程：
        1. 获取下一个版本号
        2. 为每个必选和可选包 ID 创建 CapabilityPackRef 引用
        3. 计算角色包的整体风险等级（取所有子包中最高的风险等级）
        4. 创建 RoleCapabilityPack 对象
        5. 序列化写入对应路径

        rollback_ref 指向上一版本，首次创建时为空字符串。
        默认激活策略为 "manual"，即需要人工确认后才激活。
        """
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
        """加载指定角色包版本，未指定版本时加载最新版本。"""
        resolved_version = version if version is not None else self.latest_version(role_id)
        return RoleCapabilityPack.from_dict(json.loads(self.manifest_path(role_id, resolved_version).read_text(encoding="utf-8")))

    def list_latest(self) -> list[RoleCapabilityPack]:
        """列出所有角色包的最新版本。"""
        if not self.root.exists():
            return []
        role_packs: list[RoleCapabilityPack] = []
        for role_dir in sorted(path for path in self.root.iterdir() if path.is_dir()):
            role_packs.append(self.load(role_dir.name))
        return role_packs

    def check(self, role_id: str, assets: list[CapabilityAsset], version: int | None = None) -> RolePackCheckReport:
        """检查角色包及其所有引用的子能力包的完整性。

        流程：
        1. 加载角色包
        2. 对每个引用的能力包（必选和可选）分别执行完整性检查
        3. 收集检查未通过的必选包 ID 到 failed_pack_ids
        4. complete 为 True 当且仅当没有必选包检查失败

        这使得可以通过一次调用验证整个角色的能力集是否仍然可用。
        """
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
        """获取角色包清单文件的路径。"""
        return self.root / role_id / f"{version}.json"

    def latest_version(self, role_id: str) -> int:
        """获取角色包的最新版本号。"""
        role_dir = self.root / role_id
        versions = sorted(int(path.stem) for path in role_dir.glob("*.json") if path.stem.isdigit())
        if not versions:
            raise FileNotFoundError(f"role capability pack not found: {role_id}")
        return versions[-1]

    def next_version(self, role_id: str) -> int:
        """获取下一个可用的版本号。"""
        try:
            return self.latest_version(role_id) + 1
        except FileNotFoundError:
            return 1

    def _pack_ref(self, pack_id: str, *, required: bool) -> CapabilityPackRef:
        """根据包 ID 创建对能力包的引用。

        从 pack_store 加载能力包的最新清单，提取包 ID、版本和内容哈希。
        """
        manifest, hash_value = self.pack_store.load(pack_id)
        return CapabilityPackRef(
            pack_id=manifest.pack_id,
            version=manifest.version,
            content_hash=hash_value,
            required=required,
        )


def _highest_pack_risk(pack_refs: list[CapabilityPackRef], pack_store: CapabilityPackStore) -> str:
    """计算一组能力包引用中的最高风险等级。

    遍历所有引用的包，加载其清单，取 aggregate_risk_tier_snapshot 的最大值。
    使用 tier_rank() 进行数值比较（low=0, medium=1, high=2, critical=3）。
    """
    highest = "low"
    for pack_ref in pack_refs:
        manifest, _ = pack_store.load(pack_ref.pack_id, pack_ref.version)
        if tier_rank(manifest.aggregate_risk_tier_snapshot) > tier_rank(highest):
            highest = manifest.aggregate_risk_tier_snapshot
    return highest
