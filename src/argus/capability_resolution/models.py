"""能力解析的领域模型：决策枚举、解析结果和报告路径。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Decision(StrEnum):
    """能力缺口处置决策类型。

    REUSE: 复用已有本地资产
    CONFIGURE: 配置现有资产以满足缺口
    INSTALL_SUGGESTED: 建议安装外部能力（高风险）
    CREATE_LOCAL: 参照相似资产创建新的本地能力
    MERGE: 合并多个资产以覆盖缺口
    IGNORE: 忽略低优先级缺口
    """
    REUSE = "reuse"
    CONFIGURE = "configure"
    INSTALL_SUGGESTED = "install_suggested"
    CREATE_LOCAL = "create_local"
    MERGE = "merge"
    IGNORE = "ignore"


# 每种决策对应的风险等级：外部安装风险最高，复用则最安全
DECISION_RISK = {
    Decision.REUSE: "low",
    Decision.CONFIGURE: "low",
    Decision.IGNORE: "low",
    Decision.MERGE: "medium",
    Decision.CREATE_LOCAL: "medium",
    Decision.INSTALL_SUGGESTED: "high",
}


@dataclass(frozen=True)
class CapabilityResolution:
    """单个能力缺口的解析结果，包含决策、匹配资产、证据和置信度。"""
    gap_id: str
    gap_description: str
    decision: Decision
    risk_level: str
    matched_local_asset_ids: list[str]
    external_options: list[dict[str, str]]
    confidence: float
    evidence: list[str]
    recommended_action: str
    contract_id: str = ""
    role_id: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典，将 Decision 枚举转换为其字符串值。"""
        data = asdict(self)
        data["decision"] = self.decision.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityResolution:
        """从字典反序列化，将 decision 字符串还原为 Decision 枚举。"""
        copied = dict(data)
        copied["decision"] = Decision(copied["decision"])
        return cls(**copied)


@dataclass(frozen=True)
class ResolutionReport:
    """解析报告的路径引用，包含 Markdown 和 JSON 双格式路径。"""
    markdown_path: Path
    json_path: Path
