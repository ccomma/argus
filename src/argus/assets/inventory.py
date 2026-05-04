from __future__ import annotations

import json
from pathlib import Path

from argus.assets.models import CapabilityAsset


class CapabilityInventory:
    def __init__(self, inventory_path: str | Path) -> None:
        self.inventory_path = Path(inventory_path)

    def write(self, assets: list[CapabilityAsset]) -> None:
        self.inventory_path.parent.mkdir(parents=True, exist_ok=True)
        self.inventory_path.write_text(
            json.dumps([asset.to_dict() for asset in assets], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def list_assets(self) -> list[CapabilityAsset]:
        if not self.inventory_path.exists():
            return []
        data = json.loads(self.inventory_path.read_text(encoding="utf-8"))
        return [CapabilityAsset.from_dict(item) for item in data]
