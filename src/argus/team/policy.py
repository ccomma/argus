"""团队策略 - 控制安装权限、共享策略、来源黑白名单和例外规则，影响团队能力治理行为。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from argus.team.models import MemberRole, Permission, Team


@dataclass
class TeamPolicy:
    """团队治理策略：定义安装审批、合约/角色共享、版本来源管控和例外规则。

    核心决策方法：
    - can_install: 基于来源黑白名单和成员角色判断是否允许安装
    - can_share_contract / can_share_role: 基于共享开关和角色判断
    """

    team_id: str
    team_id: str
    default_member_role: str = "member"
    allow_self_enrollment: bool = False
    require_approval_for_install: bool = True
    shared_contract_templates: bool = True
    shared_role_packs: bool = True
    auto_install_trusted: bool = False
    blocked_sources: list[str] = field(default_factory=list)
    allowed_sources: list[str] = field(default_factory=list)
    exception_rules: list[dict[str, Any]] = field(default_factory=list)

    def can_install(self, source: str, member_role: MemberRole) -> bool:
        """判断指定来源的能力是否可被该角色安装。

        1. 被阻止的来源直接拒绝
        2. 被允许的来源直接放行
        3. OWNER/ADMIN 始终可安装
        4. 其余需查看 require_approval_for_install 开关
        """
        if source in self.blocked_sources:
            return False
        if source in self.allowed_sources:
            return True
        if member_role in (MemberRole.OWNER, MemberRole.ADMIN):
            return True
        return not self.require_approval_for_install

    def can_share_contract(self, member_role: MemberRole) -> bool:
        return self.shared_contract_templates and member_role in (
            MemberRole.OWNER, MemberRole.ADMIN, MemberRole.MEMBER,
        )

    def can_share_role(self, member_role: MemberRole) -> bool:
        return self.shared_role_packs and member_role in (
            MemberRole.OWNER, MemberRole.ADMIN, MemberRole.MEMBER,
        )

    def add_exception(self, subject: str, action: str, reason: str = "") -> None:
        for e in self.exception_rules:
            if e.get("subject") == subject and e.get("action") == action:
                e["reason"] = reason
                return
        self.exception_rules.append({"subject": subject, "action": action, "reason": reason})

    def remove_exception(self, subject: str, action: str) -> bool:
        before = len(self.exception_rules)
        self.exception_rules = [
            e for e in self.exception_rules
            if not (e.get("subject") == subject and e.get("action") == action)
        ]
        return len(self.exception_rules) < before

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "default_member_role": self.default_member_role,
            "allow_self_enrollment": self.allow_self_enrollment,
            "require_approval_for_install": self.require_approval_for_install,
            "shared_contract_templates": self.shared_contract_templates,
            "shared_role_packs": self.shared_role_packs,
            "auto_install_trusted": self.auto_install_trusted,
            "blocked_sources": self.blocked_sources,
            "allowed_sources": self.allowed_sources,
            "exception_rules": self.exception_rules,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TeamPolicy:
        return cls(
            team_id=data["team_id"],
            default_member_role=data.get("default_member_role", "member"),
            allow_self_enrollment=data.get("allow_self_enrollment", False),
            require_approval_for_install=data.get("require_approval_for_install", True),
            shared_contract_templates=data.get("shared_contract_templates", True),
            shared_role_packs=data.get("shared_role_packs", True),
            auto_install_trusted=data.get("auto_install_trusted", False),
            blocked_sources=data.get("blocked_sources", []),
            allowed_sources=data.get("allowed_sources", []),
            exception_rules=data.get("exception_rules", []),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> TeamPolicy:
        if path.exists():
            return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
        return cls(team_id=path.stem)
