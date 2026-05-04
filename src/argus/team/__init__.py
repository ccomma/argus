"""团队治理模块 - 定义团队成员/角色/权限模型、团队能力编目和安装/共享策略。"""

from __future__ import annotations

from argus.team.models import MemberRole, Permission, Team, TeamMember
from argus.team.catalog import TeamCatalog, TeamCatalogManager
from argus.team.policy import TeamPolicy

__all__ = [
    "MemberRole",
    "Permission",
    "Team",
    "TeamCatalog",
    "TeamCatalogManager",
    "TeamMember",
    "TeamPolicy",
]
