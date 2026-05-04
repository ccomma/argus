from __future__ import annotations

import json
from pathlib import Path

from argus.strategy.models import ActionDecision, PolicyRule, RiskLevel, StrategyConfig


class PolicyEngine:
    def __init__(self, config: StrategyConfig | None = None) -> None:
        self.config = config or StrategyConfig.default()

    def evaluate(
        self,
        action_type: str,
        risk_level: RiskLevel | None = None,
        context: dict | None = None,
    ) -> ActionDecision:
        for rule in self.config.rules:
            if rule.matches(action_type, context):
                return rule.decision

        if risk_level is None:
            return ActionDecision.ASK

        if risk_level == RiskLevel.LOW:
            return ActionDecision.AUTO
        elif risk_level == RiskLevel.MEDIUM:
            return ActionDecision.ASK
        else:
            return ActionDecision.BLOCK

    def is_trusted_source(self, source: str) -> bool:
        if source in self.config.blocked_sources:
            return False
        if source in self.config.trusted_sources:
            return True
        return False

    def can_auto_install(self, scope: str) -> bool:
        return scope in self.config.auto_install_scopes

    def needs_confirmation(self, action_type: str) -> bool:
        return action_type in self.config.require_confirmation_for

    def add_rule(self, rule: PolicyRule) -> None:
        self.config.rules.append(rule)

    def remove_rule(self, action_type: str) -> int:
        before = len(self.config.rules)
        self.config.rules = [r for r in self.config.rules if r.action_type != action_type]
        return before - len(self.config.rules)

    def set_risk_default(self, risk_level: RiskLevel, decision: ActionDecision) -> None:
        pass

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.config.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> PolicyEngine:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(StrategyConfig.from_dict(data))
        return cls()
