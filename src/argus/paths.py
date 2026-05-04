from __future__ import annotations

"""Argus 统一路径解析模块。

提供 ArgusPaths 数据类，作为项目中所有文件路径的单一来源。
所有子系统的数据存储路径（ledger、assets、capability-packs、
role-packs、governance、resolution、modifications、handoffs）
均由此模块集中定义，避免路径字符串散落各处。
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArgusPaths:
    """Argus 文件系统路径的统一入口。

    以 root 目录为基础，通过只读属性提供各子系统的标准路径。
    使用 frozen dataclass 确保路径配置不可变，防止运行时意外修改。

    各子系统的路径约定：
    - ledger/：事件账本和候选学习项
    - assets/：能力资产清单和报告
    - capability-packs/ 和 role-packs/：能力包和角色包定义
    - governance/、resolution/、modifications/：治理和审计
    - handoffs/：上下文交接文档
    """

    root: Path

    @classmethod
    def from_store(cls, store: str | Path) -> ArgusPaths:
        """从存储根路径创建 ArgusPaths 实例。

        Args:
            store: 存储根目录的路径字符串或 Path 对象

        Returns:
            配置好的 ArgusPaths 实例
        """
        return cls(root=Path(store))

    # ── Ledger 子系统路径 ──

    @property
    def events_ledger(self) -> Path:
        """事件账本 JSONL 文件路径。"""
        return self.root / "ledger" / "events.jsonl"

    @property
    def candidate_learnings(self) -> Path:
        """候选学习项 JSONL 文件路径。"""
        return self.root / "ledger" / "candidate_learnings.jsonl"

    @property
    def reports_dir(self) -> Path:
        """学习报告输出目录。"""
        return self.root / "ledger" / "reports"

    # ── Assets 子系统路径 ──

    @property
    def asset_inventory(self) -> Path:
        """能力资产清单 JSON 文件路径。"""
        return self.root / "assets" / "inventory.json"

    @property
    def asset_reports_dir(self) -> Path:
        """资产扫描报告输出目录。"""
        return self.root / "assets" / "reports"

    # ── Capability / Role Packs 路径 ──

    @property
    def capability_packs_dir(self) -> Path:
        """能力包清单存储目录。"""
        return self.root / "capability-packs"

    @property
    def role_packs_dir(self) -> Path:
        """角色包清单存储目录。"""
        return self.root / "role-packs"

    # ── Governance 路径 ──

    @property
    def governance_reports_dir(self) -> Path:
        """治理报告输出目录。"""
        return self.root / "governance" / "reports"

    # ── Resolution 路径 ──

    @property
    def resolution_reports_dir(self) -> Path:
        """决议报告输出目录。"""
        return self.root / "resolution" / "reports"

    # ── Modifications 审计路径 ──

    @property
    def modifications_snapshots_dir(self) -> Path:
        """修改快照存储目录。"""
        return self.root / "modifications" / "snapshots"

    @property
    def modifications_audit_log(self) -> Path:
        """修改审计日志 JSONL 文件路径。"""
        return self.root / "modifications" / "audit.jsonl"

    @property
    def modifications_reports_dir(self) -> Path:
        """修改报告输出目录。"""
        return self.root / "modifications" / "reports"

    # ── Handoffs 路径 ──

    @property
    def handoffs_dir(self) -> Path:
        """上下文交接文档目录。"""
        return self.root / "handoffs"
