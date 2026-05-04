"""剧本数据模型：定义 Playbook 结构和注册中心的实现。

Playbook 是不可变数据类，描述 AI Agent 执行特定任务时的完整流程模板。
PlaybookRegistry 以文件系统为后端管理剧本的增删改查。
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Playbook:
    """任务执行剧本（不可变数据类）。

    定义一套完整的标准化工作流程，包含：提问策略、确认点、交付物模板、
    合同模板、所需角色、能力包清单等。ID 基于名称和时间戳的 SHA-1 哈希生成。
    """
    playbook_id: str
    name: str
    description: str = ""
    question_strategies: list[str] = field(default_factory=list)
    confirmation_points: list[str] = field(default_factory=list)
    deliverable_templates: list[dict[str, Any]] = field(default_factory=list)
    contract_templates: list[dict[str, Any]] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    capability_pack_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    version: int = 1
    created_at: int = 0
    updated_at: int = 0

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "playbook_id": self.playbook_id,
            "name": self.name,
            "description": self.description,
            "question_strategies": self.question_strategies,
            "confirmation_points": self.confirmation_points,
            "deliverable_templates": self.deliverable_templates,
            "contract_templates": self.contract_templates,
            "roles": self.roles,
            "capability_pack_ids": self.capability_pack_ids,
            "tags": self.tags,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Playbook:
        """从字典反序列化，缺失字段使用默认值。"""
        return cls(
            playbook_id=data["playbook_id"],
            name=data["name"],
            description=data.get("description", ""),
            question_strategies=data.get("question_strategies", []),
            confirmation_points=data.get("confirmation_points", []),
            deliverable_templates=data.get("deliverable_templates", []),
            contract_templates=data.get("contract_templates", []),
            roles=data.get("roles", []),
            capability_pack_ids=data.get("capability_pack_ids", []),
            tags=data.get("tags", []),
            version=data.get("version", 1),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
        )

    @classmethod
    def create(
        cls,
        name: str,
        description: str = "",
        question_strategies: list[str] | None = None,
        confirmation_points: list[str] | None = None,
        deliverable_templates: list[dict] | None = None,
        contract_templates: list[dict] | None = None,
        roles: list[str] | None = None,
        capability_pack_ids: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Playbook:
        """创建新剧本。

        1. 基于名称和当前时间戳生成 SHA-1 哈希作为 playbook_id（取前 12 位）
        2. 所有可选列表字段缺失时设为空列表
        3. 版本号固定从 1 开始
        """
        now = int(time.time())
        raw = f"{name}{now}"
        playbook_id = hashlib.sha1(raw.encode()).hexdigest()[:12]
        return cls(
            playbook_id=playbook_id,
            name=name,
            description=description,
            question_strategies=question_strategies or [],
            confirmation_points=confirmation_points or [],
            deliverable_templates=deliverable_templates or [],
            contract_templates=contract_templates or [],
            roles=roles or [],
            capability_pack_ids=capability_pack_ids or [],
            tags=tags or [],
            version=1,
            created_at=now,
            updated_at=now,
        )


class PlaybookRegistry:
    """剧本注册中心。

    职责：管理 Playbook 的持久化存储——保存、加载、列表、删除。
    每条剧本以 {playbook_id}.json 的形式存储在指定目录中。
    """

    def __init__(self, store_dir: str | Path) -> None:
        self.store_dir = Path(store_dir)

    def save(self, playbook: Playbook) -> None:
        """持久化保存剧本，自动创建目录。"""
        self.store_dir.mkdir(parents=True, exist_ok=True)
        path = self.store_dir / f"{playbook.playbook_id}.json"
        path.write_text(json.dumps(playbook.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    def load(self, playbook_id: str) -> Playbook | None:
        """按 ID 加载剧本，不存在返回 None。"""
        path = self.store_dir / f"{playbook_id}.json"
        if not path.exists():
            return None
        return Playbook.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_all(self) -> list[Playbook]:
        """列出所有已注册的剧本，按文件名排序。"""
        if not self.store_dir.exists():
            return []
        results: list[Playbook] = []
        for f in sorted(self.store_dir.glob("*.json")):
            results.append(Playbook.from_dict(json.loads(f.read_text(encoding="utf-8"))))
        return results

    def delete(self, playbook_id: str) -> bool:
        """按 ID 删除剧本，返回是否成功删除。"""
        path = self.store_dir / f"{playbook_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
