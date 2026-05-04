"""策略引擎：根据策略规则评估操作风险并返回决策。

PolicyEngine 是 Argus 治理的安全决策中枢，它根据 StrategyConfig 中定义的规则集，
对每个 AI Agent 操作返回 AUTO（自动执行）、ASK（请求确认）或 BLOCK（阻止）决策。
"""

from __future__ import annotations

import json
from pathlib import Path

from argus.strategy.models import ActionDecision, PolicyRule, RiskLevel, StrategyConfig


class PolicyEngine:
    """策略引擎：将策略规则应用于运行时操作，产出自动化治理决策。

    职责：
    1. 根据 action_type 匹配规则，返回对应决策
    2. 未匹配到规则时按风险等级回退：LOW->AUTO, MEDIUM->ASK, HIGH->BLOCK
    3. 管理信任源/阻止源名单
    4. 检查自动安装范围与需确认操作
    5. 支持运行时增删规则和持久化保存/加载
    """

    def __init__(self, config: StrategyConfig | None = None) -> None:
        """初始化引擎，未提供配置时使用安全默认配置。"""
        self.config = config or StrategyConfig.default()

    def evaluate(
        self,
        action_type: str,
        risk_level: RiskLevel | None = None,
        context: dict | None = None,
    ) -> ActionDecision:
        """评估操作的治理决策。

        1. 遍历所有规则，调用 matches 查找匹配项
        2. 命中规则：直接返回规则定义的决策
        3. 未命中规则 + 无风险等级：默认返回 ASK（保守策略）
        4. 未命中规则 + 有风险等级：LOW->AUTO, MEDIUM->ASK, HIGH->BLOCK
        """
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
        """检查来源是否受信任。

        阻止名单优先于信任名单：先查阻止名单，再查信任名单，均不在则视为不信任。
        """
        if source in self.config.blocked_sources:
            return False
        if source in self.config.trusted_sources:
            return True
        return False

    def can_auto_install(self, scope: str) -> bool:
        """检查指定作用域是否允许自动安装。"""
        return scope in self.config.auto_install_scopes

    def needs_confirmation(self, action_type: str) -> bool:
        """检查指定操作类型是否需要人工确认。"""
        return action_type in self.config.require_confirmation_for

    def add_rule(self, rule: PolicyRule) -> None:
        """运行时追加一条策略规则。"""
        self.config.rules.append(rule)

    def remove_rule(self, action_type: str) -> int:
        """按操作类型移除所有匹配规则，返回移除数量。"""
        before = len(self.config.rules)
        self.config.rules = [r for r in self.config.rules if r.action_type != action_type]
        return before - len(self.config.rules)

    def set_risk_default(self, risk_level: RiskLevel, decision: ActionDecision) -> None:
        """设置风险等级的回退默认决策（当前预留接口）。"""
        pass

    def save(self, path: Path) -> None:
        """将当前策略配置持久化为 JSON 文件。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.config.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> PolicyEngine:
        """从 JSON 文件加载策略引擎，文件不存在时使用默认配置。"""
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(StrategyConfig.from_dict(data))
        return cls()
