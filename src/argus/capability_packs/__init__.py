from __future__ import annotations

"""能力包（Capability Packs）子系统模块。

提供能力包的创建、存储、检查、建议、角色组合和风险评分的完整能力。
能力包是 Argus 系统中将多个能力资产按用途组合为可执行单元的机制，
支持版本管理、完整性检查和风险评估。
"""

from argus.capability_packs.advice import CapabilityPackAdvisor
from argus.capability_packs.checking import CapabilityPackChecker
from argus.capability_packs.creation import CapabilityPackCreator, build_manifest
from argus.capability_packs.models import (
    MANIFEST_SCHEMA_VERSION,
    RISK_POLICY_VERSION,
    CapabilityAdviceReport,
    CapabilityPackBinding,
    CapabilityPackCheckReport,
    CapabilityPackEntry,
    CapabilityPackManifest,
    CapabilityPackRef,
    CapabilityPackResult,
    RiskInference,
    RoleCapabilityPack,
    RolePackCheckReport,
)
from argus.capability_packs.risk import (
    RISK_REASON_BY_PERMISSION,
    RISK_TIER_BY_REASON,
    RISK_TIERS,
    aggregate_risk,
    infer_risk,
)
from argus.capability_packs.roles import RolePackStore
from argus.capability_packs.serialization import asset_snapshot_hash, content_hash
from argus.capability_packs.stores import CapabilityPackBindingStore, CapabilityPackStore


__all__ = [
    "MANIFEST_SCHEMA_VERSION",
    "RISK_REASON_BY_PERMISSION",
    "RISK_TIER_BY_REASON",
    "RISK_POLICY_VERSION",
    "RISK_TIERS",
    "CapabilityAdviceReport",
    "CapabilityPackAdvisor",
    "CapabilityPackBinding",
    "CapabilityPackBindingStore",
    "CapabilityPackCheckReport",
    "CapabilityPackChecker",
    "CapabilityPackCreator",
    "CapabilityPackEntry",
    "CapabilityPackManifest",
    "CapabilityPackRef",
    "CapabilityPackResult",
    "CapabilityPackStore",
    "RiskInference",
    "RoleCapabilityPack",
    "RolePackCheckReport",
    "RolePackStore",
    "aggregate_risk",
    "asset_snapshot_hash",
    "build_manifest",
    "content_hash",
    "infer_risk",
]
