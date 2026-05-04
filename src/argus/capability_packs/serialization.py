from __future__ import annotations

"""序列化与哈希工具模块。

提供能力包和资产的规范 JSON 序列化以及 SHA256 内容哈希计算。
这些工具是整个能力包系统中漂移检测和完整性验证的基础设施。

设计要点：
- canonical_json: 确保相同的字典内容始终产生完全一致的 JSON 字节序列
  （通过 sort_keys=True 和无缩进的紧凑格式实现）
- content_hash / asset_snapshot_hash: 基于规范 JSON 计算 SHA256，
  任何一个字段的变化都会导致哈希值变化，从而实现可靠的变更检测
"""

import json
from hashlib import sha256
from typing import Any

from argus.assets import CapabilityAsset

from .models import CapabilityPackManifest


def content_hash(manifest: CapabilityPackManifest) -> str:
    """计算能力包清单的 SHA256 内容哈希。

    用于唯一标识能力包的特定版本内容，支撑漂移检测和版本比较。
    """
    return sha256(canonical_json(manifest.to_dict()).encode("utf-8")).hexdigest()


def asset_snapshot_hash(asset: CapabilityAsset) -> str:
    """计算能力资产的 SHA256 内容哈希。

    用于能力包检查器（CapabilityPackChecker）的漂移检测：
    如果资产的哈希与能力包创建时的快照不同，说明资产已发生变化。
    """
    return sha256(canonical_json(asset.to_dict()).encode("utf-8")).hexdigest()


def canonical_json(data: dict[str, Any]) -> str:
    """生成规范 JSON 字符串。

    使用 sort_keys=True + 紧凑分隔符确保：
    1. 键始终按字母顺序排列
    2. 没有多余的空格或换行
    3. 相同的字典内容始终产生完全一致的字符串

    这种确定性是 SHA256 哈希比较正确性的前提。
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"))
