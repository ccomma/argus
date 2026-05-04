from __future__ import annotations

from argus.assets import CapabilityAsset, find_potential_duplicates, normalize

from .models import CapabilityAdviceReport


class CapabilityPackAdvisor:
    def advise(self, *, required_capabilities: list[str], assets: list[CapabilityAsset]) -> CapabilityAdviceReport:
        asset_terms = [_search_text(asset) for asset in assets]
        missing = [
            capability
            for capability in required_capabilities
            if not any(normalize(capability) in terms for terms in asset_terms)
        ]
        return CapabilityAdviceReport(
            missing_capabilities=missing,
            duplicate_asset_groups=find_potential_duplicates(assets),
        )


def _search_text(asset: CapabilityAsset) -> str:
    return normalize(" ".join([asset.name, asset.type, asset.source, *asset.permissions]))
