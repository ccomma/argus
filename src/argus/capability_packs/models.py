from __future__ import annotations

"""能力包核心模型模块。

定义了能力包系统的完整数据模型，包括：
- RiskInference: 风险推断结果（风险等级 + 原因代码）
- CapabilityPackEntry: 能力包中的单个资产条目（附带快照信息）
- CapabilityPackManifest: 能力包清单（一组资产条目的集合）
- CapabilityPackBinding: 能力包与工作合同的绑定关系
- CapabilityPackRef: 角色包中对能力包的引用
- RoleCapabilityPack: 角色能力包（组合多个能力包）
- CapabilityAdviceReport: 能力建议报告
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from argus.assets import CapabilityAsset


MANIFEST_SCHEMA_VERSION = "capability-pack-v1"
RISK_POLICY_VERSION = "risk-policy-v1"


# ── 风险推断 ──


@dataclass(frozen=True)
class RiskInference:
    """风险推断结果。

    描述一个资产或能力包的风险评估结论。

    Attributes:
        tier: 风险等级（low / medium / high / critical）
        reason_codes: 触发该风险的代码列表
        reason: 风险的文字说明
        policy_version: 使用的风险策略版本
    """

    tier: str
    reason_codes: list[str]
    reason: str
    policy_version: str = RISK_POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── 能力包条目 ──


@dataclass(frozen=True)
class CapabilityPackEntry:
    """能力包中的单个资产条目。

    每个条目是某个能力资产的"快照"——记录在创建能力包时该资产的
    所有关键属性。快照的存在使得后续可以检测资产是否发生了漂移
    （drift：当前状态与快照不一致）。

    关键快照字段：
    - asset_snapshot_hash: 资产的完整哈希，用于漂移检测
    - risk_tier_snapshot / risk_reason_snapshot: 风险快照
    - permissions_snapshot: 权限快照
    """

    entry_id: str
    asset_id: str
    required: bool
    primary_purpose: str
    selection_rationale: str
    asset_type_snapshot: str
    asset_name_snapshot: str
    source_snapshot: str
    version_snapshot: str
    install_path_snapshot: str
    permissions_snapshot: list[str]
    asset_snapshot_hash: str
    inferred_reason_codes_snapshot: list[str]
    risk_tier_snapshot: str
    risk_reason_snapshot: str
    secondary_purposes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityPackEntry:
        return cls(**data)


# ── 能力包清单 ──


@dataclass(frozen=True)
class CapabilityPackManifest:
    """能力包清单。

    能力包的顶层数据结构。包含包的标识信息、版本号、资产条目列表
    以及聚合的风险评估。每个版本是对应时间段内资产组合的不可变快照。

    Attributes:
        entries: 该包包含的所有资产条目
        aggregate_risk_tier_snapshot: 聚合后的风险等级
        supersedes_version: 上一版本号（如果是新包则为 None）
    """

    manifest_schema_version: str
    pack_id: str
    version: int
    display_name: str
    entries: list[CapabilityPackEntry]
    aggregate_risk_tier_snapshot: str
    aggregate_risk_reason_snapshot: str
    aggregate_reason_codes_snapshot: list[str]
    aggregate_contributing_entry_ids_snapshot: list[str]
    risk_policy_version: str
    created_at: int
    created_by: str
    description: str = ""
    supersedes_version: int | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["entries"] = [entry.to_dict() for entry in self.entries]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityPackManifest:
        copied = dict(data)
        copied["entries"] = [CapabilityPackEntry.from_dict(item) for item in copied["entries"]]
        return cls(**copied)


# ── 能力包结果 ──


@dataclass(frozen=True)
class CapabilityPackResult:
    """能力包创建的产物。

    包含清单、内容哈希和可选的持久化存储路径。
    """

    manifest: CapabilityPackManifest
    content_hash: str
    path: Path | None = None


# ── 能力包检查报告 ──


@dataclass(frozen=True)
class CapabilityPackCheckReport:
    """能力包完整性检查报告。

    检查能力包中的每个资产条目是否仍然有效：
    - missing_required_entry_ids: 必要资产已被删除
    - drifted_required_entry_ids: 必要资产发生了变化
    - drifted_optional_entry_ids: 可选资产发生了变化

    complete 为 True 当且仅当没有缺失的必要资产且没有漂移的必要资产。
    """

    pack_id: str
    version: int
    complete: bool
    content_hash: str
    missing_required_entry_ids: list[str]
    drifted_required_entry_ids: list[str]
    drifted_optional_entry_ids: list[str]
    current_aggregate_risk_tier: str
    current_aggregate_risk_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── 能力包绑定 ──


@dataclass(frozen=True)
class CapabilityPackBinding:
    """能力包与工作合同的绑定记录。

    当某个工作合同需要使用一个特定版本的能力包时，
    通过此绑定记录来建立关联。绑定包含合同信息、包信息、
    内容哈希和绑定时间，用于审计追溯。
    """

    contract_id: str
    contract_version: int
    pack_id: str
    pack_version: int
    content_hash: str
    rationale: str
    bound_at: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityPackBinding:
        return cls(**data)


# ── 能力包引用 ──


@dataclass(frozen=True)
class CapabilityPackRef:
    """角色包中对能力包的引用。

    包含引用的包 ID、版本和内容哈希。
    required 字段指示该引用是否为必选。
    """

    pack_id: str
    version: int
    content_hash: str
    required: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityPackRef:
        return cls(**data)


# ── 角色能力包 ──


@dataclass(frozen=True)
class RoleCapabilityPack:
    """角色能力包。

    将一个或多个能力包组合为特定的"角色"。角色定义了代理在
    特定场景下应该使用哪些能力包。

    关键字段：
    - required_pack_refs: 该角色需要的必选能力包
    - optional_pack_refs: 可选能力包
    - activation_policy: 激活策略（默认 manual）
    - risk_level: 角色的整体风险等级
    - rollback_ref: 回滚引用（指向前一版本）
    """

    role_id: str
    version: int
    display_name: str
    required_pack_refs: list[CapabilityPackRef]
    optional_pack_refs: list[CapabilityPackRef]
    activation_policy: str
    risk_level: str
    rollback_ref: str
    created_at: int
    created_by: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["required_pack_refs"] = [pack_ref.to_dict() for pack_ref in self.required_pack_refs]
        data["optional_pack_refs"] = [pack_ref.to_dict() for pack_ref in self.optional_pack_refs]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoleCapabilityPack:
        copied = dict(data)
        copied["required_pack_refs"] = [CapabilityPackRef.from_dict(item) for item in copied["required_pack_refs"]]
        copied["optional_pack_refs"] = [CapabilityPackRef.from_dict(item) for item in copied["optional_pack_refs"]]
        return cls(**copied)


# ── 角色包检查报告 ──


@dataclass(frozen=True)
class RolePackCheckReport:
    """角色能力包完整性检查报告。

    包含所有引用的能力包的检查结果。
    failed_pack_ids: 属于必选引用但检查不通过的能力包 ID。
    """

    role_id: str
    version: int
    complete: bool
    required_pack_ids: list[str]
    optional_pack_ids: list[str]
    failed_pack_ids: list[str]
    pack_reports: list[CapabilityPackCheckReport]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["pack_reports"] = [report.to_dict() for report in self.pack_reports]
        return data


# ── 能力建议报告 ──


@dataclass(frozen=True)
class CapabilityAdviceReport:
    """能力建议报告。

    列出缺失的所需能力和检测到的重复资产。
    用于在创建能力包之前评估当前资产清单是否满足需求。
    """

    missing_capabilities: list[str]
    duplicate_asset_groups: list[list[CapabilityAsset]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "missing_capabilities": self.missing_capabilities,
            "duplicate_asset_groups": [
                [asset.to_dict() for asset in group]
                for group in self.duplicate_asset_groups
            ],
        }

    def to_markdown(self) -> str:
        """将建议报告渲染为 Markdown 格式。"""
        lines = ["# Capability Pack Advice", "", "## Missing Capabilities", ""]
        if not self.missing_capabilities:
            lines.append("No missing capabilities found.")
        for capability in self.missing_capabilities:
            lines.append(f"- {capability}")
        lines.extend(["", "## Duplicate Capabilities", ""])
        if not self.duplicate_asset_groups:
            lines.append("No duplicate capability assets found.")
        for group in self.duplicate_asset_groups:
            lines.append("- " + ", ".join(f"{asset.name} ({asset.type})" for asset in group))
        return "\n".join(lines) + "\n"
