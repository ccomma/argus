"""注册中心数据模型：定义能力注册条目和索引的数据结构。

RegistryEntry 描述一个能力资产的基本元信息，RegistryIndex 管理条目集合，
提供多维度搜索和持久化能力。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RegistryEntry:
    """能力注册条目（不可变数据类）。

    记录一个能力资产的元信息：名称、类型、来源、版本、描述、
    作者、风险评分、质量评分、下载次数和标签。
    """
    entry_id: str
    name: str
    entry_type: str
    source: str
    version: str = "latest"
    description: str = ""
    author: str = ""
    risk_score: float = 0.0
    quality_score: float = 0.5
    download_count: int = 0
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "entry_id": self.entry_id,
            "name": self.name,
            "entry_type": self.entry_type,
            "source": self.source,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "risk_score": self.risk_score,
            "quality_score": self.quality_score,
            "download_count": self.download_count,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegistryEntry:
        """从字典反序列化，缺失字段使用默认值。"""
        return cls(
            entry_id=data["entry_id"],
            name=data["name"],
            entry_type=data["entry_type"],
            source=data["source"],
            version=data.get("version", "latest"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            risk_score=data.get("risk_score", 0.0),
            quality_score=data.get("quality_score", 0.5),
            download_count=data.get("download_count", 0),
            tags=data.get("tags", []),
        )


@dataclass
class RegistryIndex:
    """能力注册索引。

    职责：管理 RegistryEntry 集合，提供搜索、添加、删除、持久化能力。
    搜索支持多维度组合过滤，结果按质量降序、风险升序排列。
    """

    entries: list[RegistryEntry] = field(default_factory=list)
    registries: list[str] = field(default_factory=lambda: ["local"])
    last_updated: int = 0

    def search(
        self,
        name: str = "",
        entry_type: str = "",
        tags: list[str] | None = None,
        min_quality: float = 0.0,
        max_risk: float = 1.0,
    ) -> list[RegistryEntry]:
        """多维度搜索能力条目。

        1. name: 大小写不敏感的子串匹配
        2. entry_type: 精确类型匹配
        3. tags: 任一标签匹配（OR 逻辑）
        4. 质量过滤: quality_score >= min_quality
        5. 风险过滤: risk_score <= max_risk
        6. 结果排序: 质量降序优先，相同质量则风险升序
        """
        results = self.entries
        if name:
            results = [e for e in results if name.lower() in e.name.lower()]
        if entry_type:
            results = [e for e in results if e.entry_type == entry_type]
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        results = [e for e in results if e.quality_score >= min_quality]
        results = [e for e in results if e.risk_score <= max_risk]
        return sorted(results, key=lambda e: (-e.quality_score, e.risk_score))

    def add(self, entry: RegistryEntry) -> None:
        """添加或更新条目：同一 (entry_id, source) 的条目会原地替换。"""
        for i, existing in enumerate(self.entries):
            if existing.entry_id == entry.entry_id and existing.source == entry.source:
                self.entries[i] = entry
                return
        self.entries.append(entry)

    def remove(self, entry_id: str, source: str = "") -> bool:
        """按 entry_id（和可选 source）移除条目，返回是否实际移除。"""
        before = len(self.entries)
        self.entries = [
            e for e in self.entries
            if not (e.entry_id == entry_id and (not source or e.source == source))
        ]
        return len(self.entries) < before

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "entries": [e.to_dict() for e in self.entries],
            "registries": self.registries,
            "last_updated": self.last_updated,
        }

    def save(self, path: Path) -> None:
        """持久化索引到 JSON 文件。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> RegistryIndex:
        """从 JSON 文件加载索引，文件不存在时返回空实例。"""
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                entries=[RegistryEntry.from_dict(e) for e in data.get("entries", [])],
                registries=data.get("registries", ["local"]),
                last_updated=data.get("last_updated", 0),
            )
        return cls()
