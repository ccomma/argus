"""CLI 共享工厂 - 为所有命令处理器提供统一的 Application/Service 实例化入口。

设计说明：
- 所有以 _ 开头的工厂函数都是懒初始化辅助，按需从 args 解析路径和依赖
- 避免在主流程或各 handler 中重复构造相同的依赖链
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from argus.application import (
    AssetApplication,
    CapabilityPackApplication,
    GovernanceApplication,
    LearningApplication,
    LedgerApplication,
    ModificationApplication,
    QueryApplication,
    ResolutionApplication,
    RolePackApplication,
)
from argus.controlled_modification import AuditLedger, AssetDiffer, RollbackManager, SnapshotManager
from argus.assets import AssetScanProfile, CapabilityInventory, local_codex_asset_profile
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.core import ArgusCore
from argus.handoff import HandoffManager
from argus.ledger import EventLedger, LearningLedger
from argus.paths import ArgusPaths
from argus.storage import ContractStorage


def _core(args: argparse.Namespace) -> ArgusCore:
    """创建 ArgusCore 实例，组合 ContractStorage。"""
    return ArgusCore(_storage(args))


def _storage(args: argparse.Namespace) -> ContractStorage:
    """创建合约存储实例，指向 --store 目录。"""
    return ContractStorage(args.store)


def _ledger_application(args: argparse.Namespace) -> LedgerApplication:
    return LedgerApplication(_storage(args), _event_ledger(args))


def _learning_application(args: argparse.Namespace) -> LearningApplication:
    return LearningApplication(_event_ledger(args), _learning_ledger(args), _reports_dir(args))


def _asset_application(args: argparse.Namespace) -> AssetApplication:
    return AssetApplication(_asset_inventory(args), _asset_reports_dir(args), _learning_ledger(args))


def _pack_application(args: argparse.Namespace) -> CapabilityPackApplication:
    return CapabilityPackApplication(
        _asset_inventory(args),
        CapabilityPackStore(_paths(args).capability_packs_dir),
        _storage(args),
    )


def _role_application(args: argparse.Namespace) -> RolePackApplication:
    pack_store = CapabilityPackStore(_paths(args).capability_packs_dir)
    return RolePackApplication(_asset_inventory(args), RolePackStore(_paths(args).role_packs_dir, pack_store))


def _governance_application(args: argparse.Namespace) -> GovernanceApplication:
    pack_store = CapabilityPackStore(_paths(args).capability_packs_dir)
    role_store = RolePackStore(_paths(args).role_packs_dir, pack_store)
    return GovernanceApplication(
        _storage(args), _learning_ledger(args), _asset_inventory(args),
        pack_store, role_store, _paths(args).governance_reports_dir,
    )


def _resolution_application(args: argparse.Namespace) -> ResolutionApplication:
    pack_store = CapabilityPackStore(_paths(args).capability_packs_dir)
    role_store = RolePackStore(_paths(args).role_packs_dir, pack_store)
    return ResolutionApplication(
        _asset_inventory(args), _learning_ledger(args), pack_store, role_store,
        _storage(args), _paths(args).resolution_reports_dir,
    )


def _query_application(args: argparse.Namespace) -> QueryApplication:
    p = _paths(args)
    pack_store = CapabilityPackStore(p.capability_packs_dir)
    role_store = RolePackStore(p.role_packs_dir, pack_store)
    return QueryApplication(
        _storage(args), _event_ledger(args), _learning_ledger(args),
        _asset_inventory(args), pack_store, role_store, HandoffManager(p.handoffs_dir),
    )


def _modification_application(args: argparse.Namespace) -> ModificationApplication:
    p = _paths(args)
    inventory = _asset_inventory(args)
    contract_storage = _storage(args)
    snapshot_mgr = SnapshotManager(p.modifications_snapshots_dir)
    differ = AssetDiffer()
    audit_ledger = AuditLedger(p.modifications_audit_log)
    rollback_mgr = RollbackManager(snapshot_mgr, inventory, contract_storage, audit_ledger)
    return ModificationApplication(
        inventory, contract_storage, snapshot_mgr, differ, rollback_mgr, audit_ledger,
        p.modifications_reports_dir,
    )


def _event_ledger(args: argparse.Namespace) -> EventLedger:
    return EventLedger(_paths(args).events_ledger)


def _learning_ledger(args: argparse.Namespace) -> LearningLedger:
    return LearningLedger(_paths(args).candidate_learnings)


def _reports_dir(args: argparse.Namespace) -> Path:
    return _paths(args).reports_dir


def _asset_inventory(args: argparse.Namespace) -> CapabilityInventory:
    return CapabilityInventory(_paths(args).asset_inventory)


def _asset_reports_dir(args: argparse.Namespace) -> Path:
    return _paths(args).asset_reports_dir


def _asset_scan_profile(args: argparse.Namespace) -> AssetScanProfile:
    """从 CLI 参数构建 AssetScanProfile，合并预设和手动指定的扫描目录。"""
    profile = AssetScanProfile()
    for name in args.profile:
        if name == "local-codex":
            profile = profile.merged_with(**local_codex_asset_profile(args.profile_home).to_scan_kwargs())
    return profile.merged_with(
        skill_dirs=args.skill_dir,
        plugin_dirs=args.plugin_dir,
        mcp_configs=args.mcp_config,
        rule_files=args.rule_file,
        script_dirs=args.script_dir,
        memory_dirs=args.memory_dir,
    )


def _paths(args: argparse.Namespace) -> ArgusPaths:
    return ArgusPaths.from_store(args.store)


def _answers_from_args(args: argparse.Namespace) -> dict[str, Any]:
    """从命令行参数中提取合约回答问题，映射到标准字段。"""
    return {
        "goal": args.goal,
        "context": args.context,
        "inputs": args.inputs,
        "outputs": args.outputs,
        "constraints": args.constraints,
        "risks": args.risks,
        "acceptance_criteria": args.acceptance_criteria,
    }


def _print_json(data: Any) -> None:
    """以缩进排序 JSON 格式输出数据到 stdout。"""
    print(json.dumps(data, indent=2, sort_keys=True))


def _pack_result_dict(result: Any) -> dict[str, Any]:
    """提取能力包的标准化结果字典（hash/manifest/id/path/version）。"""
    return {
        "content_hash": result.content_hash,
        "manifest": result.manifest.to_dict(),
        "pack_id": result.manifest.pack_id,
        "path": str(result.path) if result.path else None,
        "version": result.manifest.version,
    }


def _parse_field_updates(fields: list[str]) -> dict[str, Any]:
    """解析 key=value 格式的字段更新列表为字典，用于合约修改命令。"""
    updates: dict[str, Any] = {}
    for f in fields:
        if "=" in f:
            key, value = f.split("=", 1)
            updates[key] = value
    return updates
