"""入职包生成器 - 收集活跃规则、能力、推荐包/角色和合约模板，生成 OnboardingPack。"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from argus.assets import CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.onboarding.models import OnboardingPack
from argus.storage import ContractStorage
from argus.team.catalog import TeamCatalogManager
from argus.team.policy import TeamPolicy


class OnboardingGenerator:
    """入职包生成器：聚合库存规则、活跃能力、团队编目信息，生成 OnboardingPack。

    职责：
    1. generate 主流程，调用各子收集方法
    2. 支持保存为 Markdown 和 JSON 双格式
    """

    def __init__(
        self,
        storage: ContractStorage,
        inventory: CapabilityInventory,
        pack_store: CapabilityPackStore,
        role_store: RolePackStore,
        catalog_mgr: TeamCatalogManager | None = None,
    ) -> None:
        self.storage = storage
        self.inventory = inventory
        self.pack_store = pack_store
        self.role_store = role_store
        self.catalog_mgr = catalog_mgr

    def generate(
        self,
        repo_name: str,
        team_id: str = "",
        policy: TeamPolicy | None = None,
    ) -> OnboardingPack:
        """主生成流程：收集所有维度的信息后组装 OnboardingPack。

        1. 生成唯一 pack_id（基于 repo + team + 时间戳的 SHA1）
        2. 收集规则、必需能力、推荐包/角色、合约模板、初始化步骤
        3. 组装并返回不可变 OnboardingPack
        """
        now = int(time.time())
        raw = f"{repo_name}{team_id}{now}"
        pack_id = hashlib.sha1(raw.encode()).hexdigest()[:12]

        rules = self._gather_rules(repo_name)
        required_capabilities = self._gather_required_capabilities()
        recommended_packs = self._gather_recommended_packs(team_id)
        roles = self._gather_roles(team_id)
        contract_templates = self._gather_contract_templates(team_id)
        setup_instructions = self._build_setup_instructions(repo_name, rules, required_capabilities)

        return OnboardingPack(
            pack_id=pack_id,
            repo_name=repo_name,
            team_id=team_id,
            rules=rules,
            required_capabilities=required_capabilities,
            recommended_packs=recommended_packs,
            roles=roles,
            contract_templates=contract_templates,
            setup_instructions=setup_instructions,
            created_at=now,
        )

    def _gather_rules(self, repo_name: str) -> list[str]:
        rules = []
        assets = self.inventory.list_assets()
        for a in assets:
            if a.type == "rule" and a.status == "active":
                desc = f"{a.name}: rule active in inventory"
                rules.append(desc)
        contracts = self.storage.list_contracts()
        for c in contracts:
            if c.workspace and repo_name in c.workspace:
                rules.append(f"Work contract {c.contract_id}: {c.intent[:80]}")
        return rules

    def _gather_required_capabilities(self) -> list[str]:
        caps = []
        assets = self.inventory.list_assets()
        for a in assets:
            if a.status == "active":
                caps.append(f"{a.type}/{a.name} ({a.source})")
        return caps[:20]

    def _gather_recommended_packs(self, team_id: str) -> list[str]:
        packs = []
        if self.catalog_mgr and team_id:
            catalog = self.catalog_mgr.load(team_id)
            packs = catalog.pack_ids[:10]
        all_packs = self.pack_store.list_latest()
        for p in all_packs:
            if p.pack_id not in packs:
                packs.append(p.pack_id)
        return packs[:10]

    def _gather_roles(self, team_id: str) -> list[str]:
        roles = []
        if self.catalog_mgr and team_id:
            catalog = self.catalog_mgr.load(team_id)
            roles = catalog.role_ids[:10]
        all_roles = self.role_store.list_latest()
        for r in all_roles:
            if r.role_id not in roles:
                roles.append(r.role_id)
        return roles[:10]

    def _gather_contract_templates(self, team_id: str) -> list[dict]:
        if self.catalog_mgr and team_id:
            catalog = self.catalog_mgr.load(team_id)
            return catalog.shared_templates[:5]
        return []

    def _build_setup_instructions(
        self,
        repo_name: str,
        rules: list[str],
        capabilities: list[str],
    ) -> list[str]:
        steps = [
            f"Clone repository: git clone {repo_name}",
            "Install Argus: pip install argus",
            "Initialize Argus store: python -m argus.cli assets scan",
            f"Review {len(rules)} active rules in inventory",
            f"Review {len(capabilities)} available capabilities",
        ]
        return steps

    def save(self, pack: OnboardingPack, out_dir: Path) -> Path:
        """保存入职包到指定目录：生成 .md 和 .json 双文件，返回 Markdown 路径。"""
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / f"{pack.pack_id}.md"
        md_path.write_text(pack.render_markdown(), encoding="utf-8")
        json_path = out_dir / f"{pack.pack_id}.json"
        json_path.write_text(json.dumps(pack.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return md_path
