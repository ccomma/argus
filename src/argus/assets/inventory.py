from __future__ import annotations

"""能力资产清单管理模块。

提供 CapabilityInventory 类——将扫描结果持久化为结构化 JSON 清单（inventory.json）。
支持清单的写入（write）和读取（list_assets），是资产扫描和后续分析之间的桥梁。
"""

import json
from pathlib import Path

from argus.assets.models import CapabilityAsset


class CapabilityInventory:
    """能力资产清单。

    管理一个 JSON 格式的资产清单文件。负责资产的序列化写入和反序列化读取，
    为分析、报告和包创建等下游模块提供统一的资产数据源。
    """

    def __init__(self, inventory_path: str | Path) -> None:
        """初始化清单管理器。

        Args:
            inventory_path: inventory.json 文件的路径
        """
        self.inventory_path = Path(inventory_path)

    def write(self, assets: list[CapabilityAsset]) -> None:
        """将资产列表写入清单文件。

        以美化、排序的 JSON 格式写入，自动创建父目录。
        覆盖式写入（非追加），每次全量更新清单。
        """
        self.inventory_path.parent.mkdir(parents=True, exist_ok=True)
        self.inventory_path.write_text(
            json.dumps([asset.to_dict() for asset in assets], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def list_assets(self) -> list[CapabilityAsset]:
        """从清单文件读取所有资产。

        如果清单文件不存在，返回空列表（而非抛出异常），
        这是为了支持首次使用时清单尚未创建的场景。
        """
        if not self.inventory_path.exists():
            return []
        data = json.loads(self.inventory_path.read_text(encoding="utf-8"))
        return [CapabilityAsset.from_dict(item) for item in data]
