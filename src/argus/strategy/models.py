"""策略配置模型：定义风险等级、行动决策和策略规则的核心数据结构。

策略系统是 Argus 安全治理的核心，通过规则匹配机制决定 AI Agent 操作是否需要
人工确认或直接阻止。StrategyConfig 为完整策略配置，可持久化为 JSON。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class RiskLevel(enum.Enum):
    """风险等级：低/中/高。"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionDecision(enum.Enum):
    """策略引擎的决策结果：自动执行 / 请求确认 / 阻止操作。"""
    AUTO = "auto"
    ASK = "ask"
    BLOCK = "block"


@dataclass(frozen=True)
class PolicyRule:
    """单条策略规则（不可变数据类）。

    定义某一操作类型在特定风险等级下的决策，以及触发该规则的条件。
    规则的 matches 方法用于在运行时判断当前操作是否匹配此规则。
    """
    action_type: str
    risk_level: RiskLevel
    decision: ActionDecision
    description: str = ""
    conditions: dict[str, Any] = field(default_factory=dict)

    def matches(self, action_type: str, context: dict[str, Any] | None = None) -> bool:
        """判断当前操作是否匹配此规则。

        1. action_type 必须完全匹配（大小写敏感）
        2. 无 conditions 时匹配所有同类型操作
        3. context 为 None 时跳过条件检查（宽松匹配）
        4. 逐条件比对：任一条件不满足则返回 False
        5. 全部条件满足返回 True
        """
        if self.action_type != action_type:
            return False
        if not self.conditions:
            return True
        if context is None:
            return True
        for key, val in self.conditions.items():
            if context.get(key) != val:
                return False
        return True


@dataclass
class StrategyConfig:
    """完整的策略配置。

    包含规则列表、信任源/阻止源名单、自动安装作用域、需确认操作清单。
    提供 to_dict/from_dict/default 方法用于序列化和默认配置生成。
    """
    rules: list[PolicyRule] = field(default_factory=list)
    trusted_sources: list[str] = field(default_factory=list)
    blocked_sources: list[str] = field(default_factory=list)
    auto_install_scopes: list[str] = field(default_factory=lambda: ["project"])
    require_confirmation_for: list[str] = field(default_factory=lambda: [
        "install_external_executable",
        "modify_global_rule",
        "delete_capability",
        "enable_unknown_mcp",
    ])

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典，枚举值转为字符串。"""
        return {
            "rules": [
                {
                    "action_type": r.action_type,
                    "risk_level": r.risk_level.value,
                    "decision": r.decision.value,
                    "description": r.description,
                    "conditions": r.conditions,
                }
                for r in self.rules
            ],
            "trusted_sources": self.trusted_sources,
            "blocked_sources": self.blocked_sources,
            "auto_install_scopes": self.auto_install_scopes,
            "require_confirmation_for": self.require_confirmation_for,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StrategyConfig:
        """从字典反序列化，字符串值转换回枚举类型。"""
        rules = [
            PolicyRule(
                action_type=r["action_type"],
                risk_level=RiskLevel(r["risk_level"]),
                decision=ActionDecision(r["decision"]),
                description=r.get("description", ""),
                conditions=r.get("conditions", {}),
            )
            for r in data.get("rules", [])
        ]
        return cls(
            rules=rules,
            trusted_sources=data.get("trusted_sources", []),
            blocked_sources=data.get("blocked_sources", []),
            auto_install_scopes=data.get("auto_install_scopes", ["project"]),
            require_confirmation_for=data.get("require_confirmation_for", [
                "install_external_executable",
                "modify_global_rule",
                "delete_capability",
                "enable_unknown_mcp",
            ]),
        )

    @classmethod
    def default(cls) -> StrategyConfig:
        """生成默认安全策略配置。

        定义 11 条默认规则，覆盖从低风险（资产扫描、报告生成）到高风险
        （未知来源 MCP 服务器）的操作类型。原则：低风险自动执行，
        中风险自动/确认，高风险确认/阻止。
        """
        rules = [
            PolicyRule(
                action_type="scan_assets",
                risk_level=RiskLevel.LOW,
                decision=ActionDecision.AUTO,
                description="Asset scanning is always safe",
            ),
            PolicyRule(
                action_type="generate_report",
                risk_level=RiskLevel.LOW,
                decision=ActionDecision.AUTO,
                description="Report generation is read-only",
            ),
            PolicyRule(
                action_type="install_trusted_skill",
                risk_level=RiskLevel.LOW,
                decision=ActionDecision.AUTO,
                description="Pure-text skills from trusted registries can auto-install",
            ),
            PolicyRule(
                action_type="update_project_rule",
                risk_level=RiskLevel.MEDIUM,
                decision=ActionDecision.AUTO,
                description="Project-level rules can auto-update with backup",
            ),
            PolicyRule(
                action_type="update_contract_template",
                risk_level=RiskLevel.MEDIUM,
                decision=ActionDecision.AUTO,
                description="Work contract templates auto-update with backup",
            ),
            PolicyRule(
                action_type="update_role_flow",
                risk_level=RiskLevel.MEDIUM,
                decision=ActionDecision.AUTO,
                description="Role flow updates auto-apply with backup",
            ),
            PolicyRule(
                action_type="enable_installed_mcp",
                risk_level=RiskLevel.MEDIUM,
                decision=ActionDecision.ASK,
                description="Enable already-installed MCP servers after review",
            ),
            PolicyRule(
                action_type="install_external_executable",
                risk_level=RiskLevel.HIGH,
                decision=ActionDecision.ASK,
                description="External executable code requires confirmation",
            ),
            PolicyRule(
                action_type="modify_global_rule",
                risk_level=RiskLevel.HIGH,
                decision=ActionDecision.ASK,
                description="Global rule modifications require confirmation",
            ),
            PolicyRule(
                action_type="delete_capability",
                risk_level=RiskLevel.HIGH,
                decision=ActionDecision.ASK,
                description="Capability deletion requires confirmation",
            ),
            PolicyRule(
                action_type="enable_unknown_mcp",
                risk_level=RiskLevel.HIGH,
                decision=ActionDecision.BLOCK,
                description="Unknown-source MCP servers are blocked by default",
            ),
        ]
        return cls(rules=rules)
