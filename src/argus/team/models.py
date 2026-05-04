from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class MemberRole(enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Permission(enum.Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    DELETE = "delete"


ROLE_PERMISSIONS: dict[MemberRole, list[Permission]] = {
    MemberRole.OWNER: [Permission.READ, Permission.WRITE, Permission.ADMIN, Permission.DELETE],
    MemberRole.ADMIN: [Permission.READ, Permission.WRITE, Permission.ADMIN],
    MemberRole.MEMBER: [Permission.READ, Permission.WRITE],
    MemberRole.VIEWER: [Permission.READ],
}


@dataclass(frozen=True)
class TeamMember:
    member_id: str
    name: str
    role: MemberRole = MemberRole.MEMBER
    email: str = ""

    def has_permission(self, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS.get(self.role, [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "member_id": self.member_id,
            "name": self.name,
            "role": self.role.value,
            "email": self.email,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TeamMember:
        return cls(
            member_id=data["member_id"],
            name=data["name"],
            role=MemberRole(data.get("role", "member")),
            email=data.get("email", ""),
        )


@dataclass
class Team:
    team_id: str
    name: str
    description: str = ""
    members: list[TeamMember] = field(default_factory=list)
    repositories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: int = 0

    def add_member(self, member: TeamMember) -> None:
        existing = [m for m in self.members if m.member_id == member.member_id]
        if existing:
            self.members = [m if m.member_id != member.member_id else member for m in self.members]
        else:
            self.members.append(member)

    def remove_member(self, member_id: str) -> bool:
        before = len(self.members)
        self.members = [m for m in self.members if m.member_id != member_id]
        return len(self.members) < before

    def get_member(self, member_id: str) -> TeamMember | None:
        for m in self.members:
            if m.member_id == member_id:
                return m
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "name": self.name,
            "description": self.description,
            "members": [m.to_dict() for m in self.members],
            "repositories": self.repositories,
            "tags": self.tags,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Team:
        return cls(
            team_id=data["team_id"],
            name=data["name"],
            description=data.get("description", ""),
            members=[TeamMember.from_dict(m) for m in data.get("members", [])],
            repositories=data.get("repositories", []),
            tags=data.get("tags", []),
            created_at=data.get("created_at", 0),
        )

    @classmethod
    def create(cls, team_id: str, name: str, description: str = "") -> Team:
        import time
        return cls(
            team_id=team_id,
            name=name,
            description=description,
            members=[],
            repositories=[],
            tags=[],
            created_at=int(time.time()),
        )
