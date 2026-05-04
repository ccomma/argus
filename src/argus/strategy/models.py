from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class RiskLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionDecision(enum.Enum):
    AUTO = "auto"
    ASK = "ask"
    BLOCK = "block"


@dataclass(frozen=True)
class PolicyRule:
    action_type: str
    risk_level: RiskLevel
    decision: ActionDecision
    description: str = ""
    conditions: dict[str, Any] = field(default_factory=dict)

    def matches(self, action_type: str, context: dict[str, Any] | None = None) -> bool:
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
