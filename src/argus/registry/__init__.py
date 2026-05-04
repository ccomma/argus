"""注册中心模块：管理能力资产的注册索引，支持搜索和过滤。

RegistryEntry 描述能力条目（名称、类型、来源、版本、风险评分等），
RegistryIndex 维护条目集合并提供按名称/类型/标签/质量/风险的筛选搜索能力。
"""

from __future__ import annotations

from argus.registry.models import RegistryEntry, RegistryIndex

__all__ = ["RegistryEntry", "RegistryIndex"]
