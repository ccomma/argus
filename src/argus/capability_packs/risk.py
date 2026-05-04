from __future__ import annotations

from argus.assets import CapabilityAsset

from .models import CapabilityPackEntry, RiskInference


RISK_TIERS = ("low", "medium", "high", "critical")
RISK_REASON_BY_PERMISSION = {
    "read": "reads_files",
    "reads_files": "reads_files",
    "write": "writes_files",
    "writes_files": "writes_files",
    "network": "network_access",
    "network_access": "network_access",
    "process": "executes_commands",
    "executes_commands": "executes_commands",
    "secret": "uses_secrets",
    "uses_secrets": "uses_secrets",
    "external_service": "external_service",
}
RISK_TIER_BY_REASON = {
    "reads_files": "low",
    "writes_files": "medium",
    "network_access": "high",
    "executes_commands": "medium",
    "changes_agent_behavior": "high",
    "uses_secrets": "critical",
    "external_service": "high",
    "unknown": "medium",
}


def infer_risk(reason_codes: list[str]) -> RiskInference:
    known_codes = sorted(set(reason_codes or ["unknown"]))
    highest = "low"
    highest_codes: list[str] = []
    for code in known_codes:
        tier = RISK_TIER_BY_REASON.get(code, "medium")
        if tier_rank(tier) > tier_rank(highest):
            highest = tier
            highest_codes = [code]
        elif tier == highest:
            highest_codes.append(code)
    return RiskInference(tier=highest, reason_codes=highest_codes, reason=", ".join(highest_codes))


def aggregate_risk(entries: list[CapabilityPackEntry]) -> RiskInference:
    highest = "low"
    reason_codes: list[str] = []
    entry_ids: list[str] = []
    for entry in entries:
        tier = entry.risk_tier_snapshot
        if tier_rank(tier) > tier_rank(highest):
            highest = tier
            reason_codes = list(entry.inferred_reason_codes_snapshot)
            entry_ids = [entry.entry_id]
        elif tier == highest:
            reason_codes.extend(entry.inferred_reason_codes_snapshot)
            entry_ids.append(entry.entry_id)
    codes = sorted(set(reason_codes or ["reads_files"]))
    reason = ", ".join(codes)
    if entry_ids:
        reason = f"{reason}; entries={','.join(entry_ids)}"
    return RiskInference(tier=highest, reason_codes=codes, reason=reason)


def reason_codes_for_asset(asset: CapabilityAsset) -> list[str]:
    codes = [RISK_REASON_BY_PERMISSION.get(permission, "unknown") for permission in asset.permissions]
    if not codes:
        codes = ["reads_files"]
    return sorted(set(codes))


def tier_rank(tier: str) -> int:
    return RISK_TIERS.index(tier) if tier in RISK_TIERS else RISK_TIERS.index("medium")


def highest_risk_entry_ids(entries: list[CapabilityPackEntry], tier: str) -> list[str]:
    return [entry.entry_id for entry in entries if entry.risk_tier_snapshot == tier]
