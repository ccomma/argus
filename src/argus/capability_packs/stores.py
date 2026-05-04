from __future__ import annotations

"""能力包持久化存储模块。

提供两个存储类：
- CapabilityPackStore: 能力包清单的 JSON 文件存储，支持版本管理
- CapabilityPackBindingStore: 能力包与工作合同之间的绑定关系存储

存储目录结构：
    <root>/<pack_id>/<version>.json
每个能力包的每个版本独立存储为一个 JSON 文件。
"""

import json
from pathlib import Path
from time import time

from argus.storage import ContractStorage

from .models import CapabilityPackBinding, CapabilityPackManifest
from .serialization import canonical_json, content_hash


class CapabilityPackStore:
    """能力包清单的持久化存储。

    以 <root>/<pack_id>/<version>.json 的目录结构存储能力包清单。
    支持按包 ID 加载、按最新版本加载、版本号查询和递增。
    """

    def __init__(self, root: str | Path) -> None:
        """初始化存储。

        Args:
            root: 能力包存储的根目录
        """
        self.root = Path(root)

    def write(self, manifest: CapabilityPackManifest) -> Path:
        """写入能力包清单文件。

        使用规范 JSON 格式（无缩进、排序键）写入，确保相同的
        清单内容产生完全一致的字节序列，便于内容哈希比较。
        """
        path = self.manifest_path(manifest.pack_id, manifest.version)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json(manifest.to_dict()) + "\n", encoding="utf-8")
        return path

    def load(self, pack_id: str, version: int | None = None) -> tuple[CapabilityPackManifest, str]:
        """加载能力包清单及其内容哈希。

        流程：
        1. 如果未指定版本，自动解析为最新版本
        2. 读取对应版本的 JSON 文件
        3. 反序列化为 CapabilityPackManifest
        4. 计算并返回内容哈希

        Returns:
            (清单对象, 内容哈希字符串)
        """
        resolved_version = version if version is not None else self.latest_version(pack_id)
        path = self.manifest_path(pack_id, resolved_version)
        manifest = CapabilityPackManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))
        return manifest, content_hash(manifest)

    def list_latest(self) -> list[CapabilityPackManifest]:
        """列出所有能力包的最新版本。"""
        if not self.root.exists():
            return []
        manifests: list[CapabilityPackManifest] = []
        for pack_dir in sorted(path for path in self.root.iterdir() if path.is_dir()):
            manifest, _ = self.load(pack_dir.name)
            manifests.append(manifest)
        return manifests

    def manifest_path(self, pack_id: str, version: int) -> Path:
        """获取指定版本清单文件的路径。

        格式：<root>/<pack_id>/<version>.json
        """
        return self.root / pack_id / f"{version}.json"

    def latest_version(self, pack_id: str) -> int:
        """获取能力包的最新版本号。

        流程：
        1. 列出 pack_id 目录下所有扩展名为 .json 的文件
        2. 从文件名提取版本号（stem 部分）
        3. 取最大值

        如果能力包不存在，抛出 FileNotFoundError。
        """
        pack_dir = self.root / pack_id
        versions = sorted(int(path.stem) for path in pack_dir.glob("*.json") if path.stem.isdigit())
        if not versions:
            raise FileNotFoundError(f"capability pack not found: {pack_id}")
        return versions[-1]

    def next_version(self, pack_id: str) -> int:
        """获取下一个可用的版本号（latest_version + 1）。

        如果能力包还不存在，返回 1（首个版本）。
        """
        try:
            return self.latest_version(pack_id) + 1
        except FileNotFoundError:
            return 1


class CapabilityPackBindingStore:
    """能力包与工作合同的绑定关系存储。

    负责在合同上记录能力包的绑定信息，包括更新合同的
    capability_pack_ref 字段和追加证据事件。
    """

    def __init__(self, storage: ContractStorage) -> None:
        """初始化绑定存储。

        Args:
            storage: 合同存储实例
        """
        self.storage = storage

    def bind(
        self,
        *,
        contract_id: str,
        pack: CapabilityPackManifest,
        content_hash: str,
        rationale: str,
    ) -> CapabilityPackBinding:
        """将能力包绑定到特定的工作合同。

        流程：
        1. 加载合同对象
        2. 创建 CapabilityPackBinding 记录
        3. 更新合同的 capability_pack_ref 字段（格式：pack_id@version#hash）
        4. 将绑定事件追加到合同的 execution_evidence 和 evidence.jsonl
        5. 将绑定记录保存为合同工件（capability_pack_binding.json）

        这种多层记录方式确保绑定信息既可在合同对象内直接访问，
        又有独立的审计日志和工件文件。
        """
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
