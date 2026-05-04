"""Workbench CLI - 策略/playbook/版本锁定/安全/web/团队/入职/生命周期/注册表/反馈的命令定义和 handler。

涵盖 Phase 10-12 的 CLI 命令族，是 CLI 中最大的命令注册文件。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.cli._common import (
    _asset_inventory,
    _learning_ledger,
    _paths,
    _print_json,
    _storage,
)
from argus.feedback import FeedbackLoop
from argus.lifecycle import LifecycleLedger, state_machine_for
from argus.onboarding import OnboardingGenerator
from argus.playbook import PlaybookRegistry
from argus.registry import RegistryIndex
from argus.security import SecurityScanner
from argus.strategy import PolicyEngine, StrategyConfig
from argus.team import Team, TeamCatalogManager, TeamMember, TeamPolicy
from argus.versioning import VersionLock
from argus.web import WebServer


# ── strategy ─────────────────────────────────────────────────────────

def add_strategy_commands(subparsers: Any) -> None:
    """注册策略子命令：show/set-rule/reset。"""
    show = subparsers.add_parser("show", help="Show current strategy configuration.")
    show.add_argument("--store", default=".argus")

    set_rule = subparsers.add_parser("set-rule", help="Set a policy rule.")
    set_rule.add_argument("--action-type", required=True)
    set_rule.add_argument("--risk-level", choices=("low", "medium", "high"), required=True)
    set_rule.add_argument("--decision", choices=("auto", "ask", "block"), required=True)
    set_rule.add_argument("--description", default="")
    set_rule.add_argument("--store", default=".argus")

    reset = subparsers.add_parser("reset", help="Reset strategy to defaults.")
    reset.add_argument("--store", default=".argus")


def handle_strategy_show(args: argparse.Namespace) -> int:
    engine = _policy_engine(args)
    _print_json(engine.config.to_dict())
    return 0


def handle_strategy_set_rule(args: argparse.Namespace) -> int:
    from argus.strategy.models import ActionDecision, PolicyRule, RiskLevel
    engine = _policy_engine(args)
    rule = PolicyRule(
        action_type=args.action_type,
        risk_level=RiskLevel(args.risk_level),
        decision=ActionDecision(args.decision),
        description=args.description,
    )
    engine.add_rule(rule)
    strategy_path = _paths(args).root / "strategy.json"
    engine.save(strategy_path)
    _print_json({"status": "ok", "action_type": args.action_type})
    return 0


def handle_strategy_reset(args: argparse.Namespace) -> int:
    engine = PolicyEngine(StrategyConfig.default())
    strategy_path = _paths(args).root / "strategy.json"
    engine.save(strategy_path)
    _print_json({"status": "ok", "message": "Strategy reset to defaults"})
    return 0


def _policy_engine(args: argparse.Namespace) -> PolicyEngine:
    return PolicyEngine.load(_paths(args).root / "strategy.json")


# ── playbook ─────────────────────────────────────────────────────────

def add_playbook_commands(subparsers: Any) -> None:
    """注册 playbook 子命令：create/list/show/delete。"""
    create = subparsers.add_parser("create", help="Create a personal playbook.")
    create.add_argument("--name", required=True)
    create.add_argument("--description", default="")
    create.add_argument("--role", action="append", default=[], dest="roles")
    create.add_argument("--tag", action="append", default=[], dest="tags")
    create.add_argument("--store", default=".argus")

    list_cmd = subparsers.add_parser("list", help="List personal playbooks.")
    list_cmd.add_argument("--store", default=".argus")

    show = subparsers.add_parser("show", help="Show a playbook.")
    show.add_argument("playbook_id")
    show.add_argument("--store", default=".argus")

    delete = subparsers.add_parser("delete", help="Delete a playbook.")
    delete.add_argument("playbook_id")
    delete.add_argument("--store", default=".argus")


def handle_playbook_create(args: argparse.Namespace) -> int:
    from argus.playbook import Playbook
    p = _paths(args)
    registry = PlaybookRegistry(p.root / "playbooks")
    pb = Playbook.create(name=args.name, description=args.description, roles=args.roles, tags=args.tags)
    registry.save(pb)
    _print_json(pb.to_dict())
    return 0


def handle_playbook_list(args: argparse.Namespace) -> int:
    p = _paths(args)
    registry = PlaybookRegistry(p.root / "playbooks")
    _print_json([pb.to_dict() for pb in registry.list_all()])
    return 0


def handle_playbook_show(args: argparse.Namespace) -> int:
    p = _paths(args)
    registry = PlaybookRegistry(p.root / "playbooks")
    pb = registry.load(args.playbook_id)
    if pb is None:
        _print_json({"error": f"Playbook {args.playbook_id} not found"})
        return 1
    _print_json(pb.to_dict())
    return 0


def handle_playbook_delete(args: argparse.Namespace) -> int:
    p = _paths(args)
    registry = PlaybookRegistry(p.root / "playbooks")
    ok = registry.delete(args.playbook_id)
    _print_json({"deleted": ok})
    return 0 if ok else 1


# ── version-lock ─────────────────────────────────────────────────────

def add_version_lock_commands(subparsers: Any) -> None:
    """注册版本锁定子命令：lock/unlock/list。"""
    lock = subparsers.add_parser("lock", help="Lock a capability version.")
    lock.add_argument("--asset-id", required=True)
    lock.add_argument("--asset-type", required=True)
    lock.add_argument("--source", required=True)
    lock.add_argument("--version", required=True)
    lock.add_argument("--reason", default="")
    lock.add_argument("--store", default=".argus")

    unlock = subparsers.add_parser("unlock", help="Unlock a capability version.")
    unlock.add_argument("--asset-id", required=True)
    unlock.add_argument("--store", default=".argus")

    list_cmd = subparsers.add_parser("list", help="List all version locks.")
    list_cmd.add_argument("--store", default=".argus")


def handle_version_lock_lock(args: argparse.Namespace) -> int:
    lock = _version_lock(args)
    entry = lock.lock(
        asset_id=args.asset_id, asset_type=args.asset_type,
        source=args.source, version=args.version, reason=args.reason,
    )
    lock.save()
    _print_json(entry.to_dict())
    return 0


def handle_version_lock_unlock(args: argparse.Namespace) -> int:
    lock = _version_lock(args)
    ok = lock.unlock(args.asset_id)
    lock.save()
    _print_json({"deleted": ok})
    return 0 if ok else 1


def handle_version_lock_list(args: argparse.Namespace) -> int:
    lock = _version_lock(args)
    _print_json([e.to_dict() for e in lock.list_locked()])
    return 0


def _version_lock(args: argparse.Namespace) -> VersionLock:
    return VersionLock.load(_paths(args).root / "locks" / "versions.json")


# ── security ─────────────────────────────────────────────────────────

def add_security_commands(subparsers: Any) -> None:
    """注册安全扫描子命令：scan。"""
    scan = subparsers.add_parser("scan", help="Scan content for prompt-injection and supply-chain risks.")
    scan.add_argument("--content", default="")
    scan.add_argument("--file", default="")
    scan.add_argument("--source", default="")
    scan.add_argument("--store", default=".argus")


def handle_security_scan(args: argparse.Namespace) -> int:
    scanner = SecurityScanner()
    content = args.content
    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
    report = scanner.scan_capability(content=content, source=args.source, location=args.file or "cli")
    _print_json(report.to_dict())
    return 0


# ── web ──────────────────────────────────────────────────────────────

def handle_web_serve(args: argparse.Namespace) -> int:
    WebServer(store=args.store, host=args.host, port=args.port).serve()
    return 0


# ── team ─────────────────────────────────────────────────────────────

def add_team_commands(subparsers: Any) -> None:
    """注册团队子命令：create/add-member/remove-member/show/list/catalog/policy/set-policy。"""
    create = subparsers.add_parser("create", help="Create a team.")
    create.add_argument("--team-id", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--description", default="")
    create.add_argument("--store", default=".argus")

    add_member = subparsers.add_parser("add-member", help="Add a member to a team.")
    add_member.add_argument("--team-id", required=True)
    add_member.add_argument("--member-id", required=True)
    add_member.add_argument("--name", required=True)
    add_member.add_argument("--role", choices=("owner", "admin", "member", "viewer"), default="member")
    add_member.add_argument("--store", default=".argus")

    remove_member = subparsers.add_parser("remove-member", help="Remove a member from a team.")
    remove_member.add_argument("--team-id", required=True)
    remove_member.add_argument("--member-id", required=True)
    remove_member.add_argument("--store", default=".argus")

    show = subparsers.add_parser("show", help="Show team details.")
    show.add_argument("--team-id", required=True)
    show.add_argument("--store", default=".argus")

    list_cmd = subparsers.add_parser("list", help="List all teams.")
    list_cmd.add_argument("--store", default=".argus")

    catalog = subparsers.add_parser("catalog", help="Show team catalog stats.")
    catalog.add_argument("--team-id", required=True)
    catalog.add_argument("--store", default=".argus")

    policy_show = subparsers.add_parser("policy", help="Show team policy.")
    policy_show.add_argument("--team-id", required=True)
    policy_show.add_argument("--store", default=".argus")

    policy_set = subparsers.add_parser("set-policy", help="Set team policy.")
    policy_set.add_argument("--team-id", required=True)
    policy_set.add_argument("--allow-self-enrollment", action="store_true", default=None)
    policy_set.add_argument("--require-approval-for-install", action="store_true", default=None)
    policy_set.add_argument("--shared-contract-templates", action="store_true", default=None)
    policy_set.add_argument("--shared-role-packs", action="store_true", default=None)
    policy_set.add_argument("--auto-install-trusted", action="store_true", default=None)
    policy_set.add_argument("--blocked-source", action="append", default=[], dest="blocked_sources")
    policy_set.add_argument("--allowed-source", action="append", default=[], dest="allowed_sources")
    policy_set.add_argument("--store", default=".argus")


def handle_team_create(args: argparse.Namespace) -> int:
    team = Team.create(args.team_id, args.name, args.description)
    _team_store(args).mkdir(parents=True, exist_ok=True)
    _save_team(args, team)
    _print_json(team.to_dict())
    return 0


def handle_team_add_member(args: argparse.Namespace) -> int:
    from argus.team.models import MemberRole
    team = _load_team(args, args.team_id)
    if team is None:
        _print_json({"error": f"Team {args.team_id} not found"})
        return 1
    member = TeamMember(member_id=args.member_id, name=args.name, role=MemberRole(args.role))
    team.add_member(member)
    _save_team(args, team)
    _print_json(team.to_dict())
    return 0


def handle_team_remove_member(args: argparse.Namespace) -> int:
    team = _load_team(args, args.team_id)
    if team is None:
        _print_json({"error": f"Team {args.team_id} not found"})
        return 1
    ok = team.remove_member(args.member_id)
    _save_team(args, team)
    _print_json({"removed": ok})
    return 0 if ok else 1


def handle_team_show(args: argparse.Namespace) -> int:
    team = _load_team(args, args.team_id)
    if team is None:
        _print_json({"error": f"Team {args.team_id} not found"})
        return 1
    _print_json(team.to_dict())
    return 0


def handle_team_list(args: argparse.Namespace) -> int:
    store = _team_store(args)
    teams = []
    if store.exists():
        for f in sorted(store.glob("*.json")):
            teams.append(Team.from_dict(json.loads(f.read_text(encoding="utf-8"))).to_dict())
    _print_json(teams)
    return 0


def handle_team_catalog(args: argparse.Namespace) -> int:
    p = _paths(args)
    catalog_mgr = TeamCatalogManager(p.root / "teams" / "catalogs")
    pack_store = CapabilityPackStore(p.capability_packs_dir)
    role_store = RolePackStore(p.role_packs_dir, pack_store)
    stats = catalog_mgr.compute_stats(
        args.team_id, _storage(args), _asset_inventory(args), pack_store, role_store,
    )
    _print_json(stats)
    return 0


def handle_team_policy_show(args: argparse.Namespace) -> int:
    policy = _load_team_policy(args, args.team_id)
    _print_json(policy.to_dict())
    return 0


def handle_team_policy_set(args: argparse.Namespace) -> int:
    policy = _load_team_policy(args, args.team_id)
    if args.allow_self_enrollment is not None:
        policy.allow_self_enrollment = args.allow_self_enrollment
    if args.require_approval_for_install is not None:
        policy.require_approval_for_install = args.require_approval_for_install
    if args.shared_contract_templates is not None:
        policy.shared_contract_templates = args.shared_contract_templates
    if args.shared_role_packs is not None:
        policy.shared_role_packs = args.shared_role_packs
    if args.auto_install_trusted is not None:
        policy.auto_install_trusted = args.auto_install_trusted
    if args.blocked_sources:
        policy.blocked_sources.extend(args.blocked_sources)
    if args.allowed_sources:
        policy.allowed_sources.extend(args.allowed_sources)
    _save_team_policy(args, policy)
    _print_json(policy.to_dict())
    return 0


def _team_store(args: argparse.Namespace) -> Path:
    return _paths(args).root / "teams"


def _save_team(args: argparse.Namespace, team: Team) -> None:
    path = _team_store(args) / f"{team.team_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(team.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def _load_team(args: argparse.Namespace, team_id: str) -> Team | None:
    path = _team_store(args) / f"{team_id}.json"
    if path.exists():
        return Team.from_dict(json.loads(path.read_text(encoding="utf-8")))
    return None


def _load_team_policy(args: argparse.Namespace, team_id: str) -> TeamPolicy:
    path = _paths(args).root / "teams" / "policies" / f"{team_id}.json"
    return TeamPolicy.load(path)


def _save_team_policy(args: argparse.Namespace, policy: TeamPolicy) -> None:
    path = _paths(args).root / "teams" / "policies" / f"{policy.team_id}.json"
    policy.save(path)


# ── onboarding ───────────────────────────────────────────────────────

def add_onboarding_commands(subparsers: Any) -> None:
    """注册入职子命令：generate。"""
    generate = subparsers.add_parser("generate", help="Generate an onboarding pack for a repo.")
    generate.add_argument("--repo-name", required=True)
    generate.add_argument("--team-id", default="")
    generate.add_argument("--store", default=".argus")


def handle_onboarding_generate(args: argparse.Namespace) -> int:
    p = _paths(args)
    pack_store = CapabilityPackStore(p.capability_packs_dir)
    role_store = RolePackStore(p.role_packs_dir, pack_store)
    catalog_mgr = TeamCatalogManager(p.root / "teams" / "catalogs")
    gen = OnboardingGenerator(
        _storage(args), _asset_inventory(args), pack_store, role_store, catalog_mgr,
    )
    policy = None
    if args.team_id:
        policy = _load_team_policy(args, args.team_id)
    pack = gen.generate(args.repo_name, args.team_id, policy)
    out_dir = p.root / "onboarding"
    md_path = gen.save(pack, out_dir)
    _print_json({"markdown_path": str(md_path), "pack": pack.to_dict()})
    return 0


# ── lifecycle ────────────────────────────────────────────────────────

def add_lifecycle_commands(subparsers: Any) -> None:
    """注册生命周期子命令：show/apply/history。"""
    show = subparsers.add_parser("show", help="Show lifecycle state and available transitions.")
    show.add_argument("--asset-id", required=True)
    show.add_argument("--asset-type", default="capability")
    show.add_argument("--current-state", default="draft")
    show.add_argument("--store", default=".argus")

    apply_cmd = subparsers.add_parser("apply", help="Apply a lifecycle transition to an asset.")
    apply_cmd.add_argument("--asset-id", required=True)
    apply_cmd.add_argument("--asset-type", required=True)
    apply_cmd.add_argument("--action", required=True)
    apply_cmd.add_argument("--from-state", required=True)
    apply_cmd.add_argument("--triggered-by", default="argus-cli")
    apply_cmd.add_argument("--reason", default="")
    apply_cmd.add_argument("--store", default=".argus")

    history = subparsers.add_parser("history", help="List lifecycle history for an asset.")
    history.add_argument("--asset-id", required=True)
    history.add_argument("--store", default=".argus")


def handle_lifecycle_show(args: argparse.Namespace) -> int:
    sm = state_machine_for(args.current_state)
    _print_json({
        "asset_id": args.asset_id,
        "current_state": sm.current.value,
        "available_actions": [a.value for a in sm.available_actions()],
    })
    return 0


def handle_lifecycle_apply(args: argparse.Namespace) -> int:
    from argus.lifecycle import AssetState, LifecycleAction, LifecycleRecord
    from_state = AssetState(args.from_state)
    sm = state_machine_for(args.from_state)
    action = LifecycleAction(args.action)
    try:
        to_state = sm.apply(action)
    except ValueError as exc:
        _print_json({"error": str(exc)})
        return 1
    record = LifecycleRecord.create(
        asset_id=args.asset_id, asset_type=args.asset_type,
        action=action, from_state=from_state, to_state=to_state,
        triggered_by=args.triggered_by, reason=args.reason,
    )
    ledger = LifecycleLedger(_paths(args).root / "lifecycle" / "ledger.jsonl")
    ledger.append(record)
    _print_json(record.to_dict())
    return 0


def handle_lifecycle_history(args: argparse.Namespace) -> int:
    ledger = LifecycleLedger(_paths(args).root / "lifecycle" / "ledger.jsonl")
    records = ledger.for_asset(args.asset_id)
    _print_json([r.to_dict() for r in records])
    return 0


# ── registry ─────────────────────────────────────────────────────────

def add_registry_commands(subparsers: Any) -> None:
    """注册注册表子命令：search/add/list。"""
    search = subparsers.add_parser("search", help="Search the capability registry.")
    search.add_argument("--name", default="")
    search.add_argument("--type", default="", dest="entry_type")
    search.add_argument("--tag", action="append", default=[], dest="tags")
    search.add_argument("--min-quality", type=float, default=0.0)
    search.add_argument("--max-risk", type=float, default=1.0)
    search.add_argument("--store", default=".argus")

    add = subparsers.add_parser("add", help="Add an entry to the registry index.")
    add.add_argument("--entry-id", required=True)
    add.add_argument("--name", required=True)
    add.add_argument("--type", required=True, dest="entry_type")
    add.add_argument("--source", required=True)
    add.add_argument("--version", default="latest")
    add.add_argument("--description", default="")
    add.add_argument("--quality-score", type=float, default=0.5)
    add.add_argument("--risk-score", type=float, default=0.0)
    add.add_argument("--store", default=".argus")

    list_cmd = subparsers.add_parser("list", help="List all registry entries.")
    list_cmd.add_argument("--store", default=".argus")


def handle_registry_search(args: argparse.Namespace) -> int:
    idx = RegistryIndex.load(_paths(args).root / "registry" / "index.json")
    results = idx.search(
        name=args.name, entry_type=args.entry_type,
        tags=args.tags if args.tags else None,
        min_quality=args.min_quality, max_risk=args.max_risk,
    )
    _print_json([r.to_dict() for r in results])
    return 0


def handle_registry_add(args: argparse.Namespace) -> int:
    from argus.registry import RegistryEntry
    idx = RegistryIndex.load(_paths(args).root / "registry" / "index.json")
    entry = RegistryEntry(
        entry_id=args.entry_id, name=args.name, entry_type=args.entry_type,
        source=args.source, version=args.version, description=args.description,
        quality_score=args.quality_score, risk_score=args.risk_score,
    )
    idx.add(entry)
    idx.save(_paths(args).root / "registry" / "index.json")
    _print_json(entry.to_dict())
    return 0


def handle_registry_list(args: argparse.Namespace) -> int:
    idx = RegistryIndex.load(_paths(args).root / "registry" / "index.json")
    _print_json([e.to_dict() for e in idx.entries])
    return 0


# ── feedback ─────────────────────────────────────────────────────────

def add_feedback_commands(subparsers: Any) -> None:
    """注册反馈子命令：record/list/recommend。"""
    record = subparsers.add_parser("record", help="Record a feedback signal.")
    record.add_argument("--source-type", required=True)
    record.add_argument("--source-id", required=True)
    record.add_argument("--signal-type", required=True)
    record.add_argument("--target-type", required=True)
    record.add_argument("--target-id", required=True)
    record.add_argument("--strength", type=float, required=True)
    record.add_argument("--store", default=".argus")

    list_cmd = subparsers.add_parser("list", help="List feedback signals.")
    list_cmd.add_argument("--target-type", default="")
    list_cmd.add_argument("--target-id", default="")
    list_cmd.add_argument("--signal-type", default="")
    list_cmd.add_argument("--store", default=".argus")

    recommend = subparsers.add_parser("recommend", help="Get recommendation for a target.")
    recommend.add_argument("--target-type", required=True)
    recommend.add_argument("--target-id", required=True)
    recommend.add_argument("--store", default=".argus")


def handle_feedback_record(args: argparse.Namespace) -> int:
    loop = FeedbackLoop(_paths(args).root / "feedback")
    signal = loop.record(
        source_type=args.source_type, source_id=args.source_id,
        signal_type=args.signal_type, target_type=args.target_type,
        target_id=args.target_id, strength=args.strength,
    )
    _print_json(signal.to_dict())
    return 0


def handle_feedback_list(args: argparse.Namespace) -> int:
    loop = FeedbackLoop(_paths(args).root / "feedback")
    signals = loop.list_signals(
        target_type=args.target_type, target_id=args.target_id,
        signal_type=args.signal_type,
    )
    _print_json([s.to_dict() for s in signals])
    return 0


def handle_feedback_recommend(args: argparse.Namespace) -> int:
    loop = FeedbackLoop(_paths(args).root / "feedback")
    rec = loop.compute_recommendation(args.target_type, args.target_id)
    _print_json(rec)
    return 0
