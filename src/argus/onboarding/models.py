"""入职包模型 - OnboardingPack 数据类，包含入职规则、能力需求、推荐角色和 Markdown 渲染。"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OnboardingPack:
    """仓库入职包：为新仓库生态生成的能力入职指南。

    包含：
    - 规则列表（来自库存和合约）
    - 必需能力和推荐能力包
    - 推荐角色
    - 合约模板和初始化步骤
    - render_markdown 输出可读报告
    """

    pack_id: str
    pack_id: str
    repo_name: str
    team_id: str = ""
    rules: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    recommended_packs: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    contract_templates: list[dict[str, Any]] = field(default_factory=list)
    setup_instructions: list[str] = field(default_factory=list)
    created_at: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "repo_name": self.repo_name,
            "team_id": self.team_id,
            "rules": self.rules,
            "required_capabilities": self.required_capabilities,
            "recommended_packs": self.recommended_packs,
            "roles": self.roles,
            "contract_templates": self.contract_templates,
            "setup_instructions": self.setup_instructions,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OnboardingPack:
        return cls(
            pack_id=data["pack_id"],
            repo_name=data["repo_name"],
            team_id=data.get("team_id", ""),
            rules=data.get("rules", []),
            required_capabilities=data.get("required_capabilities", []),
            recommended_packs=data.get("recommended_packs", []),
            roles=data.get("roles", []),
            contract_templates=data.get("contract_templates", []),
            setup_instructions=data.get("setup_instructions", []),
            created_at=data.get("created_at", 0),
        )

    def render_markdown(self) -> str:
        """将入职包渲染为 Markdown 文档，方便人阅读和共享。

        1. 输出标题和生成时间
        2. 逐块输出规则、必需能力、推荐包、推荐角色和初始化步骤
        """
        lines = [
            f"# Onboarding Pack: {self.repo_name}",
            "",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M', time.localtime(self.created_at))}",
            "",
            "## Rules",
            "",
        ]
        for r in self.rules:
            lines.append(f"- {r}")
        lines.append("")

        if self.required_capabilities:
            lines.append("## Required Capabilities")
            lines.append("")
            for c in self.required_capabilities:
                lines.append(f"- {c}")
            lines.append("")

        if self.recommended_packs:
            lines.append("## Recommended Capability Packs")
            lines.append("")
            for p in self.recommended_packs:
                lines.append(f"- {p}")
            lines.append("")

        if self.roles:
            lines.append("## Recommended Roles")
            lines.append("")
            for r in self.roles:
                lines.append(f"- {r}")
            lines.append("")

        if self.setup_instructions:
            lines.append("## Setup Instructions")
            lines.append("")
            for i, step in enumerate(self.setup_instructions, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        return "\n".join(lines)
