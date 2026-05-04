from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from argus.assets import CapabilityAsset

from .models import CapabilityPackManifest


def content_hash(manifest: CapabilityPackManifest) -> str:
    return sha256(canonical_json(manifest.to_dict()).encode("utf-8")).hexdigest()


def asset_snapshot_hash(asset: CapabilityAsset) -> str:
    return sha256(canonical_json(asset.to_dict()).encode("utf-8")).hexdigest()


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))
