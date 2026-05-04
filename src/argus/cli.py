from __future__ import annotations

import argparse
import json
import sys
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
from argus.analytics import DashboardReporter, ROICalculator
from argus.contracts import ContractSession, QuestionStrategy
from argus.core import ArgusCore
from argus.feedback import FeedbackLoop
from argus.handoff import HandoffManager
from argus.ledger import EventLedger, LearningLedger
from argus.lifecycle import LifecycleLedger, state_machine_for
from argus.maintenance import MaintenanceEngine, MaintenanceReporter
from argus.mcp import MCPServer
from argus.onboarding import OnboardingGenerator
from argus.paths import ArgusPaths
from argus.playbook import PlaybookRegistry
from argus.registry import RegistryIndex
from argus.security import SecurityScanner
from argus.storage import ContractStorage
from argus.strategy import PolicyEngine, StrategyConfig
from argus.team import Team, TeamCatalog, TeamCatalogManager, TeamMember, TeamPolicy
from argus.versioning import VersionLock
from argus.web import WebServer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="argus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    contract = subparsers.add_parser("contract", help="Work contract commands.")
    contract_subparsers = contract.add_subparsers(dest="contract_command", required=True)
    ledger = subparsers.add_parser("ledger", help="Event ledger commands.")
    ledger_subparsers = ledger.add_subparsers(dest="ledger_command", required=True)
    learning = subparsers.add_parser("learning", help="Candidate learning commands.")
    learning_subparsers = learning.add_subparsers(dest="learning_command", required=True)
    assets = subparsers.add_parser("assets", help="Capability asset inventory commands.")
    assets_subparsers = assets.add_subparsers(dest="assets_command", required=True)
    packs = subparsers.add_parser("packs", help="Capability pack commands.")
    packs_subparsers = packs.add_subparsers(dest="packs_command", required=True)
    roles = subparsers.add_parser("roles", help="Role capability pack commands.")
    roles_subparsers = roles.add_subparsers(dest="roles_command", required=True)
    governance = subparsers.add_parser("governance", help="Governance report commands.")
    governance_subparsers = governance.add_subparsers(dest="governance_command", required=True)
    resolve = subparsers.add_parser("resolve", help="Capability resolution commands.")
    resolve_subparsers = resolve.add_subparsers(dest="resolve_command", required=True)
    modify = subparsers.add_parser("modify", help="Controlled modification and rollback commands.")
    modify_subparsers = modify.add_subparsers(dest="modify_command", required=True)
    query = subparsers.add_parser("query", help="Cross-cutting lookup commands.")
    query_subparsers = query.add_subparsers(dest="query_command", required=True)
    mcp_serve = subparsers.add_parser("mcp-serve", help="Start the Argus MCP server on stdio.")
    dashboard = subparsers.add_parser("dashboard", help="Write a local dashboard report.")
    maintenance = subparsers.add_parser("maintenance", help="Run maintenance checks on the system.")
    maintenance_subparsers = maintenance.add_subparsers(dest="maintenance_command", required=True)

    _add_contract_commands(contract_subparsers)
    _add_ledger_commands(ledger_subparsers)
    _add_learning_commands(learning_subparsers)
    _add_asset_commands(assets_subparsers)
    _add_pack_commands(packs_subparsers)
    _add_role_commands(roles_subparsers)
    _add_governance_commands(governance_subparsers)
    _add_resolve_commands(resolve_subparsers)
    _add_modify_commands(modify_subparsers)
    _add_query_commands(query_subparsers)
    mcp_serve.add_argument("--store", default=".argus")
    dashboard.add_argument("--store", default=".argus")
    _add_maintenance_commands(maintenance_subparsers)

    web = subparsers.add_parser("web", help="Start the local Argus workbench web server.")
    web.add_argument("--store", default=".argus")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8765)

    strategy = subparsers.add_parser("strategy", help="Strategy and policy configuration.")
    strategy_subparsers = strategy.add_subparsers(dest="strategy_command", required=True)
    _add_strategy_commands(strategy_subparsers)

    playbook = subparsers.add_parser("playbook", help="Personal playbook commands.")
    playbook_subparsers = playbook.add_subparsers(dest="playbook_command", required=True)
    _add_playbook_commands(playbook_subparsers)

    version_lock = subparsers.add_parser("version-lock", help="Capability version lock commands.")
    version_lock_subparsers = version_lock.add_subparsers(dest="version_lock_command", required=True)
    _add_version_lock_commands(version_lock_subparsers)

    security = subparsers.add_parser("security", help="Security scanning commands.")
    security_subparsers = security.add_subparsers(dest="security_command", required=True)
    _add_security_commands(security_subparsers)

    team = subparsers.add_parser("team", help="Team management commands.")
    team_subparsers = team.add_subparsers(dest="team_command", required=True)
    _add_team_commands(team_subparsers)

    onboarding = subparsers.add_parser("onboarding", help="Repo onboarding pack commands.")
    onboarding_subparsers = onboarding.add_subparsers(dest="onboarding_command", required=True)
    _add_onboarding_commands(onboarding_subparsers)

    lifecycle = subparsers.add_parser("lifecycle", help="Asset lifecycle management commands.")
    lifecycle_subparsers = lifecycle.add_subparsers(dest="lifecycle_command", required=True)
    _add_lifecycle_commands(lifecycle_subparsers)

    registry = subparsers.add_parser("registry", help="Multi-registry capability discovery.")
    registry_subparsers = registry.add_subparsers(dest="registry_command", required=True)
    _add_registry_commands(registry_subparsers)

    feedback = subparsers.add_parser("feedback", help="Closed-loop learning feedback commands.")
    feedback_subparsers = feedback.add_subparsers(dest="feedback_command", required=True)
    _add_feedback_commands(feedback_subparsers)

    args = parser.parse_args(argv)
    return _dispatch(parser, args)


def _add_contract_commands(subparsers: Any) -> None:
    draft = subparsers.add_parser("draft", help="Draft a work contract from an intent.")
    draft.add_argument("--intent", required=True)
    draft.add_argument("--mode", choices=("quick", "standard", "strict"), default="standard")
    draft.add_argument("--goal", default="")
    draft.add_argument("--context", default="")
    draft.add_argument("--inputs", default="")
    draft.add_argument("--outputs", default="")
    draft.add_argument("--constraints", default="")
    draft.add_argument("--risks", default="")
    draft.add_argument("--acceptance-criteria", default="")
    draft.add_argument("--store", default=".argus")

    start = subparsers.add_parser("start", help="Interactively draft a work contract.")
    start.add_argument("--intent", required=True)
    start.add_argument("--mode", choices=("quick", "standard", "strict"), default="standard")
    start.add_argument("--store", default=".argus")

    evaluate = subparsers.add_parser("evaluate", help="Evaluate a deliverable against a contract.")
    evaluate.add_argument("contract_id")
    evaluate.add_argument("deliverable_path")
    evaluate.add_argument("--type", choices=("prd", "roadmap", "research_plan"), default="prd")
    evaluate.add_argument("--store", default=".argus")

    show = subparsers.add_parser("show", help="Show a stored work contract.")
    show.add_argument("contract_id")
    show.add_argument("--store", default=".argus")

    score = subparsers.add_parser("score", help="Show a stored work contract completeness score.")
    score.add_argument("contract_id")
    score.add_argument("--store", default=".argus")

    render = subparsers.add_parser("render", help="Render a deliverable draft from a work contract.")
    render.add_argument("contract_id")
    render.add_argument("--type", choices=("prd", "roadmap", "research_plan"), default="prd")
    render.add_argument("--store", default=".argus")

    bind_pack = subparsers.add_parser("bind-pack", help="Bind a concrete capability pack version to a work contract.")
    bind_pack.add_argument("contract_id")
    bind_pack.add_argument("pack_id")
    bind_pack.add_argument("--version", type=int, default=None)
    bind_pack.add_argument("--rationale", required=True)
    bind_pack.add_argument("--store", default=".argus")

    contract_list = subparsers.add_parser("list", help="List all stored work contracts.")
    contract_list.add_argument("--store", default=".argus")


def _add_ledger_commands(subparsers: Any) -> None:
    ingest_contract = subparsers.add_parser("ingest-contract", help="Import contract evidence into the event ledger.")
    ingest_contract.add_argument("contract_id")
    ingest_contract.add_argument("--store", default=".argus")

    ingest_transcript = subparsers.add_parser("ingest-transcript", help="Import a transcript JSONL fixture.")
    ingest_transcript.add_argument("path")
    ingest_transcript.add_argument("--store", default=".argus")

    ledger_list = subparsers.add_parser("list", help="List event ledger records.")
    ledger_list.add_argument("--store", default=".argus")


def _add_learning_commands(subparsers: Any) -> None:
    learning_extract = subparsers.add_parser("extract", help="Extract candidate learnings from the event ledger.")
    learning_extract.add_argument("--store", default=".argus")

    learning_list = subparsers.add_parser("list", help="List candidate learnings.")
    learning_list.add_argument("--store", default=".argus")

    learning_report = subparsers.add_parser("report", help="Write a local learning report.")
    learning_report.add_argument("--store", default=".argus")


def _add_asset_commands(subparsers: Any) -> None:
    scan = subparsers.add_parser("scan", help="Scan local capability assets into an inventory.")
    _add_asset_scan_args(scan)

    list_assets = subparsers.add_parser("list", help="List scanned capability assets.")
    list_assets.add_argument("--store", default=".argus")

    report = subparsers.add_parser("report", help="Write a capability asset scan report.")
    report.add_argument("--store", default=".argus")

    link = subparsers.add_parser("link-learnings", help="Link candidate learnings to scanned capability assets.")
    link.add_argument("--store", default=".argus")


def _add_pack_commands(subparsers: Any) -> None:
    propose = subparsers.add_parser("propose", help="Propose a capability pack manifest from inventory assets.")
    _add_pack_create_args(propose)

    create = subparsers.add_parser("create", help="Create a versioned capability pack manifest.")
    _add_pack_create_args(create)

    inspect = subparsers.add_parser("inspect", help="Inspect a capability pack manifest.")
    inspect.add_argument("pack_id")
    inspect.add_argument("--version", type=int, default=None)
    inspect.add_argument("--store", default=".argus")

    check = subparsers.add_parser("check", help="Check a capability pack against the current inventory.")
    check.add_argument("pack_id")
    check.add_argument("--version", type=int, default=None)
    check.add_argument("--store", default=".argus")

    advise = subparsers.add_parser("advise", help="Report missing and duplicate capabilities for requested capability names.")
    advise.add_argument("--required-capability", action="append", default=[])
    advise.add_argument("--store", default=".argus")

    pack_list = subparsers.add_parser("list", help="List all stored capability packs.")
    pack_list.add_argument("--store", default=".argus")


def _add_role_commands(subparsers: Any) -> None:
    create = subparsers.add_parser("create-pack", help="Create a role capability pack from existing capability packs.")
    create.add_argument("--store", default=".argus")
    create.add_argument("--role-id", required=True)
    create.add_argument("--display-name", required=True)
    create.add_argument("--required-pack", action="append", default=[])
    create.add_argument("--optional-pack", action="append", default=[])
    create.add_argument("--created-by", default="argus-cli")

    inspect = subparsers.add_parser("inspect-pack", help="Inspect a role capability pack.")
    inspect.add_argument("role_id")
    inspect.add_argument("--version", type=int, default=None)
    inspect.add_argument("--store", default=".argus")

    check = subparsers.add_parser("check-pack", help="Check a role capability pack.")
    check.add_argument("role_id")
    check.add_argument("--version", type=int, default=None)
    check.add_argument("--store", default=".argus")

    role_list = subparsers.add_parser("list", help="List all stored role packs.")
    role_list.add_argument("--store", default=".argus")


def _add_governance_commands(subparsers: Any) -> None:
    report = subparsers.add_parser("report", help="Write a local governance report.")
    report.add_argument("--store", default=".argus")


def _add_resolve_commands(subparsers: Any) -> None:
    run = subparsers.add_parser("run", help="Run capability resolution against all capability gaps.")
    run.add_argument("--store", default=".argus")

    report = subparsers.add_parser("report", help="Write a capability resolution report.")
    report.add_argument("--store", default=".argus")


def _add_modify_commands(subparsers: Any) -> None:
    preview = subparsers.add_parser("preview", help="Preview an asset modification without applying it.")
    preview.add_argument("--asset-id", required=True)
    preview.add_argument("--triggered-by", required=True)
    preview.add_argument("--trigger-reason", required=True)
    preview.add_argument("--new-status", default="")
    preview.add_argument("--store", default=".argus")

    apply_cmd = subparsers.add_parser("apply", help="Apply a controlled modification to an asset.")
    apply_cmd.add_argument("--asset-id", required=True)
    apply_cmd.add_argument("--triggered-by", required=True)
    apply_cmd.add_argument("--trigger-reason", required=True)
    apply_cmd.add_argument("--new-status", default="")
    apply_cmd.add_argument("--store", default=".argus")

    contract_preview = subparsers.add_parser("contract-preview", help="Preview a contract modification.")
    contract_preview.add_argument("--contract-id", required=True)
    contract_preview.add_argument("--triggered-by", required=True)
    contract_preview.add_argument("--trigger-reason", required=True)
    contract_preview.add_argument("--field", action="append", default=[], dest="fields")
    contract_preview.add_argument("--store", default=".argus")

    contract_apply = subparsers.add_parser("contract-apply", help="Apply a controlled modification to a contract.")
    contract_apply.add_argument("--contract-id", required=True)
    contract_apply.add_argument("--triggered-by", required=True)
    contract_apply.add_argument("--trigger-reason", required=True)
    contract_apply.add_argument("--field", action="append", default=[], dest="fields")
    contract_apply.add_argument("--store", default=".argus")

    rollback = subparsers.add_parser("rollback", help="Rollback a previous modification.")
    rollback.add_argument("--audit-id", required=True)
    rollback.add_argument("--reason", required=True)
    rollback.add_argument("--store", default=".argus")

    audit = subparsers.add_parser("audit-log", help="List all modification audit records.")
    audit.add_argument("--store", default=".argus")

    report = subparsers.add_parser("report", help="Write a modification report.")
    report.add_argument("--store", default=".argus")


def _add_maintenance_commands(subparsers: Any) -> None:
    run = subparsers.add_parser("run", help="Run maintenance checks (duplicates, conflicts, unused).")
    run.add_argument("--store", default=".argus")

    report = subparsers.add_parser("report", help="Write a maintenance report.")
    report.add_argument("--store", default=".argus")


def _add_strategy_commands(subparsers: Any) -> None:
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


def _add_playbook_commands(subparsers: Any) -> None:
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


def _add_version_lock_commands(subparsers: Any) -> None:
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


def _add_security_commands(subparsers: Any) -> None:
    scan = subparsers.add_parser("scan", help="Scan content for prompt-injection and supply-chain risks.")
    scan.add_argument("--content", default="")
    scan.add_argument("--file", default="")
    scan.add_argument("--source", default="")
    scan.add_argument("--store", default=".argus")


def _add_team_commands(subparsers: Any) -> None:
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


def _add_onboarding_commands(subparsers: Any) -> None:
    generate = subparsers.add_parser("generate", help="Generate an onboarding pack for a repo.")
    generate.add_argument("--repo-name", required=True)
    generate.add_argument("--team-id", default="")
    generate.add_argument("--store", default=".argus")


def _add_lifecycle_commands(subparsers: Any) -> None:
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


def _add_registry_commands(subparsers: Any) -> None:
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


def _add_feedback_commands(subparsers: Any) -> None:
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


def _add_query_commands(subparsers: Any) -> None:
    contract = subparsers.add_parser("contract", help="Query contracts with related objects.")
    contract.add_argument("contract_id")
    contract.add_argument("--store", default=".argus")

    role = subparsers.add_parser("role", help="Query a role with related packs and handoffs.")
    role.add_argument("role_id")
    role.add_argument("--store", default=".argus")


def _add_pack_create_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--store", default=".argus")
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--required-asset", action="append", default=[])
    parser.add_argument("--optional-asset", action="append", default=[])
    parser.add_argument("--created-by", default="argus-cli")


def _add_asset_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--store", default=".argus")
    parser.add_argument("--profile", choices=("local-codex",), action="append", default=[])
    parser.add_argument("--profile-home", default=None)
    parser.add_argument("--skill-dir", action="append", default=[])
    parser.add_argument("--plugin-dir", action="append", default=[])
    parser.add_argument("--mcp-config", action="append", default=[])
    parser.add_argument("--rule-file", action="append", default=[])
    parser.add_argument("--script-dir", action="append", default=[])
    parser.add_argument("--memory-dir", action="append", default=[])


def _dispatch(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    if args.command == "mcp-serve":
        return _mcp_serve(args)
    if args.command == "dashboard":
        return _dashboard(args)
    if args.command == "web":
        return _web_serve(args)

    handlers = {
        ("contract", "draft"): _draft,
        ("contract", "start"): _start,
        ("contract", "evaluate"): _evaluate,
        ("contract", "show"): _show,
        ("contract", "score"): _score,
        ("contract", "render"): _render,
        ("contract", "bind-pack"): _contract_bind_pack,
        ("contract", "list"): _contract_list,
        ("ledger", "ingest-contract"): _ledger_ingest_contract,
        ("ledger", "ingest-transcript"): _ledger_ingest_transcript,
        ("ledger", "list"): _ledger_list,
        ("learning", "extract"): _learning_extract,
        ("learning", "list"): _learning_list,
        ("learning", "report"): _learning_report,
        ("assets", "scan"): _assets_scan,
        ("assets", "list"): _assets_list,
        ("assets", "report"): _assets_report,
        ("assets", "link-learnings"): _assets_link_learnings,
        ("packs", "propose"): _packs_propose,
        ("packs", "create"): _packs_create,
        ("packs", "inspect"): _packs_inspect,
        ("packs", "check"): _packs_check,
        ("packs", "advise"): _packs_advise,
        ("packs", "list"): _packs_list,
        ("roles", "create-pack"): _roles_create_pack,
        ("roles", "inspect-pack"): _roles_inspect_pack,
        ("roles", "check-pack"): _roles_check_pack,
        ("roles", "list"): _roles_list,
        ("governance", "report"): _governance_report,
        ("resolve", "run"): _resolve_run,
        ("resolve", "report"): _resolve_report,
        ("modify", "preview"): _modify_preview,
        ("modify", "apply"): _modify_apply,
        ("modify", "contract-preview"): _modify_contract_preview,
        ("modify", "contract-apply"): _modify_contract_apply,
        ("modify", "rollback"): _modify_rollback,
        ("modify", "audit-log"): _modify_audit_log,
        ("modify", "report"): _modify_report,
        ("query", "contract"): _query_contract,
        ("query", "role"): _query_role,
        ("maintenance", "run"): _maintenance_run,
        ("maintenance", "report"): _maintenance_report,
        ("strategy", "show"): _strategy_show,
        ("strategy", "set-rule"): _strategy_set_rule,
        ("strategy", "reset"): _strategy_reset,
        ("playbook", "create"): _playbook_create,
        ("playbook", "list"): _playbook_list,
        ("playbook", "show"): _playbook_show,
        ("playbook", "delete"): _playbook_delete,
        ("version-lock", "lock"): _version_lock_lock,
        ("version-lock", "unlock"): _version_lock_unlock,
        ("version-lock", "list"): _version_lock_list,
        ("security", "scan"): _security_scan,
        ("team", "create"): _team_create,
        ("team", "add-member"): _team_add_member,
        ("team", "remove-member"): _team_remove_member,
        ("team", "show"): _team_show,
        ("team", "list"): _team_list,
        ("team", "catalog"): _team_catalog,
        ("team", "policy"): _team_policy_show,
        ("team", "set-policy"): _team_policy_set,
        ("onboarding", "generate"): _onboarding_generate,
        ("lifecycle", "show"): _lifecycle_show,
        ("lifecycle", "apply"): _lifecycle_apply,
        ("lifecycle", "history"): _lifecycle_history,
        ("registry", "search"): _registry_search,
        ("registry", "add"): _registry_add,
        ("registry", "list"): _registry_list,
        ("feedback", "record"): _feedback_record,
        ("feedback", "list"): _feedback_list,
        ("feedback", "recommend"): _feedback_recommend,
    }
    subcommand = getattr(args, f"{args.command.replace('-', '_')}_command")
    try:
        handler = handlers.get((args.command, subcommand))
        if handler:
            return handler(args)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    parser.error("unknown command")
    return 2


def _draft(args: argparse.Namespace) -> int:
    contract = _core(args).draft_contract(
        intent=args.intent,
        mode=args.mode,
        answers=_answers_from_args(args),
    )
    _print_json(contract.to_dict())
    return 0


def _start(args: argparse.Namespace) -> int:
    strategy = QuestionStrategy.for_mode(args.mode)
    session = ContractSession.start(args.intent, strategy)
    for question in session.next_questions():
        print(f"{question.question} [{question.field}]", file=sys.stderr)
        print("> ", end="", file=sys.stderr, flush=True)
        answer = sys.stdin.readline().strip()
        if answer:
            session.answer(**{question.field: answer})
    contract = _core(args).draft_contract(intent=session.intent, mode=args.mode, answers=session.answers)
    _print_json(contract.to_dict())
    return 0


def _evaluate(args: argparse.Namespace) -> int:
    text = Path(args.deliverable_path).read_text(encoding="utf-8")
    result = _core(args).evaluate_deliverable(
        contract_id=args.contract_id,
        deliverable_type=args.type,
        text=text,
    )
    _print_json(result.to_dict())
    return 0


def _show(args: argparse.Namespace) -> int:
    contract = _core(args).load_contract(args.contract_id)
    _print_json(contract.to_dict())
    return 0


def _score(args: argparse.Namespace) -> int:
    contract = _core(args).load_contract(args.contract_id)
    _print_json(contract.completeness_score.to_dict())
    return 0


def _render(args: argparse.Namespace) -> int:
    rendered = _core(args).render_deliverable(args.contract_id, args.type)
    print(rendered, end="")
    return 0


def _contract_bind_pack(args: argparse.Namespace) -> int:
    binding = _pack_application(args).bind_contract(args.contract_id, args.pack_id, args.rationale, args.version)
    _print_json(binding.to_dict())
    return 0


def _ledger_ingest_contract(args: argparse.Namespace) -> int:
    imported = _ledger_application(args).ingest_contract(args.contract_id)
    _print_json({"imported": imported})
    return 0


def _ledger_ingest_transcript(args: argparse.Namespace) -> int:
    imported = _ledger_application(args).ingest_transcript(args.path)
    _print_json({"imported": imported})
    return 0


def _ledger_list(args: argparse.Namespace) -> int:
    _print_json([event.to_dict() for event in _ledger_application(args).list_events()])
    return 0


def _learning_extract(args: argparse.Namespace) -> int:
    created = _learning_application(args).extract()
    _print_json({"created": created})
    return 0


def _learning_list(args: argparse.Namespace) -> int:
    _print_json([item.to_dict() for item in _learning_application(args).list_items()])
    return 0


def _learning_report(args: argparse.Namespace) -> int:
    report = _learning_application(args).write_report()
    _print_json({"markdown_path": str(report.markdown_path), "json_path": str(report.json_path)})
    return 0


def _assets_scan(args: argparse.Namespace) -> int:
    profile = _asset_scan_profile(args)
    result, report = _asset_application(args).scan(profile)
    _print_json(
        {
            "assets": len(result.assets),
            "profiles": args.profile,
            "warnings": result.warnings,
            "inventory_path": str(_paths(args).asset_inventory),
            "report_path": str(report.report_path),
        }
    )
    return 0


def _assets_list(args: argparse.Namespace) -> int:
    _print_json([asset.to_dict() for asset in _asset_application(args).list_assets()])
    return 0


def _assets_report(args: argparse.Namespace) -> int:
    report = _asset_application(args).write_report()
    _print_json({"report_path": str(report.report_path)})
    return 0


def _assets_link_learnings(args: argparse.Namespace) -> int:
    links, report = _asset_application(args).link_learnings()
    _print_json(
        {
            "links": len(links),
            "link_report_path": str(report.link_report_path),
        }
    )
    return 0


def _packs_propose(args: argparse.Namespace) -> int:
    result = _pack_application(args).propose(
        pack_id=args.pack_id,
        display_name=args.display_name,
        description=args.description,
        required_asset_ids=args.required_asset,
        optional_asset_ids=args.optional_asset,
        created_by=args.created_by,
    )
    _print_json(_pack_result_dict(result))
    return 0


def _packs_create(args: argparse.Namespace) -> int:
    result = _pack_application(args).create(
        pack_id=args.pack_id,
        display_name=args.display_name,
        description=args.description,
        required_asset_ids=args.required_asset,
        optional_asset_ids=args.optional_asset,
        created_by=args.created_by,
    )
    _print_json(_pack_result_dict(result))
    return 0


def _packs_inspect(args: argparse.Namespace) -> int:
    manifest, hash_value = _pack_application(args).inspect(args.pack_id, args.version)
    _print_json({"content_hash": hash_value, "manifest": manifest.to_dict()})
    return 0


def _packs_check(args: argparse.Namespace) -> int:
    _print_json(_pack_application(args).check(args.pack_id, args.version).to_dict())
    return 0


def _packs_advise(args: argparse.Namespace) -> int:
    report = _pack_application(args).advise(args.required_capability)
    _print_json(report.to_dict())
    return 0


def _roles_create_pack(args: argparse.Namespace) -> int:
    role_pack = _role_application(args).create(
        role_id=args.role_id,
        display_name=args.display_name,
        required_pack_ids=args.required_pack,
        optional_pack_ids=args.optional_pack,
        created_by=args.created_by,
    )
    _print_json(role_pack.to_dict())
    return 0


def _roles_inspect_pack(args: argparse.Namespace) -> int:
    _print_json(_role_application(args).inspect(args.role_id, args.version).to_dict())
    return 0


def _roles_check_pack(args: argparse.Namespace) -> int:
    _print_json(_role_application(args).check(args.role_id, args.version).to_dict())
    return 0


def _governance_report(args: argparse.Namespace) -> int:
    report = _governance_application(args).write_report()
    _print_json(
        {
            "markdown_path": str(report.markdown_path),
            "json_path": str(report.json_path),
            "low_risk_log_path": str(report.low_risk_log_path),
            "pending_actions_path": str(report.pending_actions_path),
        }
    )
    return 0


def _resolve_run(args: argparse.Namespace) -> int:
    resolutions = _resolution_application(args).resolve_all()
    _print_json([r.to_dict() for r in resolutions])
    return 0


def _resolve_report(args: argparse.Namespace) -> int:
    report = _resolution_application(args).write_report()
    _print_json(
        {
            "markdown_path": str(report.markdown_path),
            "json_path": str(report.json_path),
        }
    )
    return 0


def _modify_preview(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    diff = app.preview_asset_modification(
        asset_id=args.asset_id,
        triggered_by=args.triggered_by,
        trigger_reason=args.trigger_reason,
        new_status=args.new_status,
    )
    if diff is None:
        _print_json({"error": f"Asset {args.asset_id} not found."})
        return 1
    _print_json(diff.to_dict())
    return 0


def _modify_apply(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    result = app.apply_asset_modification(
        asset_id=args.asset_id,
        triggered_by=args.triggered_by,
        trigger_reason=args.trigger_reason,
        new_status=args.new_status,
    )
    if result is None:
        _print_json({"error": f"Asset {args.asset_id} not found."})
        return 1
    _print_json(result.to_dict())
    return 0


def _modify_contract_preview(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    updates = _parse_field_updates(args.fields)
    diff = app.preview_contract_modification(
        contract_id=args.contract_id,
        triggered_by=args.triggered_by,
        trigger_reason=args.trigger_reason,
        field_updates=updates,
    )
    if diff is None:
        _print_json({"error": f"Contract {args.contract_id} not found."})
        return 1
    _print_json(diff.to_dict())
    return 0


def _modify_contract_apply(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    updates = _parse_field_updates(args.fields)
    result = app.apply_contract_modification(
        contract_id=args.contract_id,
        triggered_by=args.triggered_by,
        trigger_reason=args.trigger_reason,
        field_updates=updates,
    )
    if result is None:
        _print_json({"error": f"Contract {args.contract_id} not found."})
        return 1
    _print_json(result.to_dict())
    return 0


def _modify_rollback(args: argparse.Namespace) -> int:
    app = _modification_application(args)
    result = app.rollback(args.audit_id, args.reason)
    _print_json(result.to_dict())
    return 0 if result.outcome == "applied" else 1


def _modify_audit_log(args: argparse.Namespace) -> int:
    records = _modification_application(args).list_audit_log()
    _print_json([r.to_dict() for r in records])
    return 0


def _modify_report(args: argparse.Namespace) -> int:
    report = _modification_application(args).write_report()
    _print_json(
        {
            "markdown_path": str(report.markdown_path),
            "json_path": str(report.json_path),
        }
    )
    return 0


def _contract_list(args: argparse.Namespace) -> int:
    _print_json([c.to_dict() for c in _storage(args).list_contracts()])
    return 0


def _packs_list(args: argparse.Namespace) -> int:
    _print_json([p.to_dict() for p in CapabilityPackStore(_paths(args).capability_packs_dir).list_latest()])
    return 0


def _roles_list(args: argparse.Namespace) -> int:
    pack_store = CapabilityPackStore(_paths(args).capability_packs_dir)
    _print_json([r.to_dict() for r in RolePackStore(_paths(args).role_packs_dir, pack_store).list_latest()])
    return 0


def _query_contract(args: argparse.Namespace) -> int:
    results = _query_application(args).query_contracts(contract_id=args.contract_id)
    _print_json(results)
    return 0


def _query_role(args: argparse.Namespace) -> int:
    results = _query_application(args).query_roles(role_id=args.role_id)
    _print_json(results)
    return 0


def _mcp_serve(args: argparse.Namespace) -> int:
    MCPServer(store=args.store).serve()
    return 0


def _dashboard(args: argparse.Namespace) -> int:
    calculator = _roi_calculator(args)
    p = _paths(args)
    report = DashboardReporter(p.root / "reports").write(calculator)
    _print_json({
        "markdown_path": str(report.markdown_path),
        "json_path": str(report.json_path),
        "contract_roi": report.contract_roi.to_dict(),
        "learning_roi": report.learning_roi.to_dict(),
        "role_roi": report.role_roi.to_dict(),
    })
    return 0


def _maintenance_run(args: argparse.Namespace) -> int:
    engine = _maintenance_engine(args)
    report = engine.run()
    _print_json(report.to_dict())
    return 0


def _maintenance_report(args: argparse.Namespace) -> int:
    engine = _maintenance_engine(args)
    p = _paths(args)
    paths = MaintenanceReporter(p.root / "maintenance").write(engine)
    _print_json({
        "markdown_path": str(paths.markdown_path),
        "json_path": str(paths.json_path),
    })
    return 0


def _web_serve(args: argparse.Namespace) -> int:
    WebServer(store=args.store, host=args.host, port=args.port).serve()
    return 0


def _strategy_show(args: argparse.Namespace) -> int:
    engine = _policy_engine(args)
    _print_json(engine.config.to_dict())
    return 0


def _strategy_set_rule(args: argparse.Namespace) -> int:
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


def _strategy_reset(args: argparse.Namespace) -> int:
    engine = PolicyEngine(StrategyConfig.default())
    strategy_path = _paths(args).root / "strategy.json"
    engine.save(strategy_path)
    _print_json({"status": "ok", "message": "Strategy reset to defaults"})
    return 0


def _playbook_create(args: argparse.Namespace) -> int:
    from argus.playbook import Playbook
    p = _paths(args)
    registry = PlaybookRegistry(p.root / "playbooks")
    pb = Playbook.create(
        name=args.name,
        description=args.description,
        roles=args.roles,
        tags=args.tags,
    )
    registry.save(pb)
    _print_json(pb.to_dict())
    return 0


def _playbook_list(args: argparse.Namespace) -> int:
    p = _paths(args)
    registry = PlaybookRegistry(p.root / "playbooks")
    _print_json([pb.to_dict() for pb in registry.list_all()])
    return 0


def _playbook_show(args: argparse.Namespace) -> int:
    p = _paths(args)
    registry = PlaybookRegistry(p.root / "playbooks")
    pb = registry.load(args.playbook_id)
    if pb is None:
        _print_json({"error": f"Playbook {args.playbook_id} not found"})
        return 1
    _print_json(pb.to_dict())
    return 0


def _playbook_delete(args: argparse.Namespace) -> int:
    p = _paths(args)
    registry = PlaybookRegistry(p.root / "playbooks")
    ok = registry.delete(args.playbook_id)
    _print_json({"deleted": ok})
    return 0 if ok else 1


def _version_lock_lock(args: argparse.Namespace) -> int:
    lock = _version_lock(args)
    entry = lock.lock(
        asset_id=args.asset_id,
        asset_type=args.asset_type,
        source=args.source,
        version=args.version,
        reason=args.reason,
    )
    lock.save()
    _print_json(entry.to_dict())
    return 0


def _version_lock_unlock(args: argparse.Namespace) -> int:
    lock = _version_lock(args)
    ok = lock.unlock(args.asset_id)
    lock.save()
    _print_json({"deleted": ok})
    return 0 if ok else 1


def _version_lock_list(args: argparse.Namespace) -> int:
    lock = _version_lock(args)
    _print_json([e.to_dict() for e in lock.list_locked()])
    return 0


def _security_scan(args: argparse.Namespace) -> int:
    scanner = SecurityScanner()
    content = args.content
    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
    report = scanner.scan_capability(content=content, source=args.source, location=args.file or "cli")
    _print_json(report.to_dict())
    return 0


def _team_create(args: argparse.Namespace) -> int:
    team = Team.create(args.team_id, args.name, args.description)
    _team_store(args).mkdir(parents=True, exist_ok=True)
    _save_team(args, team)
    _print_json(team.to_dict())
    return 0


def _team_add_member(args: argparse.Namespace) -> int:
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


def _team_remove_member(args: argparse.Namespace) -> int:
    team = _load_team(args, args.team_id)
    if team is None:
        _print_json({"error": f"Team {args.team_id} not found"})
        return 1
    ok = team.remove_member(args.member_id)
    _save_team(args, team)
    _print_json({"removed": ok})
    return 0 if ok else 1


def _team_show(args: argparse.Namespace) -> int:
    team = _load_team(args, args.team_id)
    if team is None:
        _print_json({"error": f"Team {args.team_id} not found"})
        return 1
    _print_json(team.to_dict())
    return 0


def _team_list(args: argparse.Namespace) -> int:
    store = _team_store(args)
    teams = []
    if store.exists():
        for f in sorted(store.glob("*.json")):
            teams.append(Team.from_dict(json.loads(f.read_text(encoding="utf-8"))).to_dict())
    _print_json(teams)
    return 0


def _team_catalog(args: argparse.Namespace) -> int:
    p = _paths(args)
    catalog_mgr = TeamCatalogManager(p.root / "teams" / "catalogs")
    pack_store = CapabilityPackStore(p.capability_packs_dir)
    role_store = RolePackStore(p.role_packs_dir, pack_store)
    stats = catalog_mgr.compute_stats(
        args.team_id, _storage(args), _asset_inventory(args), pack_store, role_store,
    )
    _print_json(stats)
    return 0


def _team_policy_show(args: argparse.Namespace) -> int:
    policy = _load_team_policy(args, args.team_id)
    _print_json(policy.to_dict())
    return 0


def _team_policy_set(args: argparse.Namespace) -> int:
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


def _onboarding_generate(args: argparse.Namespace) -> int:
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


def _lifecycle_show(args: argparse.Namespace) -> int:
    sm = state_machine_for(args.current_state)
    _print_json({
        "asset_id": args.asset_id,
        "current_state": sm.current.value,
        "available_actions": [a.value for a in sm.available_actions()],
    })
    return 0


def _lifecycle_apply(args: argparse.Namespace) -> int:
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
        asset_id=args.asset_id,
        asset_type=args.asset_type,
        action=action,
        from_state=from_state,
        to_state=to_state,
        triggered_by=args.triggered_by,
        reason=args.reason,
    )
    ledger = LifecycleLedger(_paths(args).root / "lifecycle" / "ledger.jsonl")
    ledger.append(record)
    _print_json(record.to_dict())
    return 0


def _lifecycle_history(args: argparse.Namespace) -> int:
    ledger = LifecycleLedger(_paths(args).root / "lifecycle" / "ledger.jsonl")
    records = ledger.for_asset(args.asset_id)
    _print_json([r.to_dict() for r in records])
    return 0


def _registry_search(args: argparse.Namespace) -> int:
    idx = RegistryIndex.load(_paths(args).root / "registry" / "index.json")
    results = idx.search(
        name=args.name,
        entry_type=args.entry_type,
        tags=args.tags if args.tags else None,
        min_quality=args.min_quality,
        max_risk=args.max_risk,
    )
    _print_json([r.to_dict() for r in results])
    return 0


def _registry_add(args: argparse.Namespace) -> int:
    from argus.registry import RegistryEntry
    idx = RegistryIndex.load(_paths(args).root / "registry" / "index.json")
    entry = RegistryEntry(
        entry_id=args.entry_id,
        name=args.name,
        entry_type=args.entry_type,
        source=args.source,
        version=args.version,
        description=args.description,
        quality_score=args.quality_score,
        risk_score=args.risk_score,
    )
    idx.add(entry)
    idx.save(_paths(args).root / "registry" / "index.json")
    _print_json(entry.to_dict())
    return 0


def _registry_list(args: argparse.Namespace) -> int:
    idx = RegistryIndex.load(_paths(args).root / "registry" / "index.json")
    _print_json([e.to_dict() for e in idx.entries])
    return 0


def _feedback_record(args: argparse.Namespace) -> int:
    loop = FeedbackLoop(_paths(args).root / "feedback")
    signal = loop.record(
        source_type=args.source_type,
        source_id=args.source_id,
        signal_type=args.signal_type,
        target_type=args.target_type,
        target_id=args.target_id,
        strength=args.strength,
    )
    _print_json(signal.to_dict())
    return 0


def _feedback_list(args: argparse.Namespace) -> int:
    loop = FeedbackLoop(_paths(args).root / "feedback")
    signals = loop.list_signals(
        target_type=args.target_type,
        target_id=args.target_id,
        signal_type=args.signal_type,
    )
    _print_json([s.to_dict() for s in signals])
    return 0


def _feedback_recommend(args: argparse.Namespace) -> int:
    loop = FeedbackLoop(_paths(args).root / "feedback")
    rec = loop.compute_recommendation(args.target_type, args.target_id)
    _print_json(rec)
    return 0


def _parse_field_updates(fields: list[str]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for f in fields:
        if "=" in f:
            key, value = f.split("=", 1)
            updates[key] = value
    return updates


def _core(args: argparse.Namespace) -> ArgusCore:
    return ArgusCore(_storage(args))


def _storage(args: argparse.Namespace) -> ContractStorage:
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
        _storage(args),
        _learning_ledger(args),
        _asset_inventory(args),
        pack_store,
        role_store,
        _paths(args).governance_reports_dir,
    )


def _resolution_application(args: argparse.Namespace) -> ResolutionApplication:
    pack_store = CapabilityPackStore(_paths(args).capability_packs_dir)
    role_store = RolePackStore(_paths(args).role_packs_dir, pack_store)
    return ResolutionApplication(
        _asset_inventory(args),
        _learning_ledger(args),
        pack_store,
        role_store,
        _storage(args),
        _paths(args).resolution_reports_dir,
    )


def _query_application(args: argparse.Namespace) -> QueryApplication:
    p = _paths(args)
    pack_store = CapabilityPackStore(p.capability_packs_dir)
    role_store = RolePackStore(p.role_packs_dir, pack_store)
    return QueryApplication(
        _storage(args),
        _event_ledger(args),
        _learning_ledger(args),
        _asset_inventory(args),
        pack_store,
        role_store,
        HandoffManager(p.handoffs_dir),
    )


def _roi_calculator(args: argparse.Namespace) -> ROICalculator:
    p = _paths(args)
    pack_store = CapabilityPackStore(p.capability_packs_dir)
    role_store = RolePackStore(p.role_packs_dir, pack_store)
    return ROICalculator(
        _storage(args),
        _event_ledger(args),
        _learning_ledger(args),
        _asset_inventory(args),
        pack_store,
        role_store,
        HandoffManager(p.handoffs_dir),
    )


def _maintenance_engine(args: argparse.Namespace) -> MaintenanceEngine:
    p = _paths(args)
    pack_store = CapabilityPackStore(p.capability_packs_dir)
    role_store = RolePackStore(p.role_packs_dir, pack_store)
    return MaintenanceEngine(
        _asset_inventory(args),
        pack_store,
        role_store,
        _storage(args),
    )


def _policy_engine(args: argparse.Namespace) -> PolicyEngine:
    return PolicyEngine.load(_paths(args).root / "strategy.json")


def _version_lock(args: argparse.Namespace) -> VersionLock:
    return VersionLock.load(_paths(args).root / "locks" / "versions.json")


def _modification_application(args: argparse.Namespace) -> ModificationApplication:
    p = _paths(args)
    inventory = _asset_inventory(args)
    contract_storage = _storage(args)
    snapshot_mgr = SnapshotManager(p.modifications_snapshots_dir)
    differ = AssetDiffer()
    audit_ledger = AuditLedger(p.modifications_audit_log)
    rollback_mgr = RollbackManager(snapshot_mgr, inventory, contract_storage, audit_ledger)
    return ModificationApplication(
        inventory,
        contract_storage,
        snapshot_mgr,
        differ,
        rollback_mgr,
        audit_ledger,
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


def _answers_from_args(args: argparse.Namespace) -> dict[str, str]:
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
    print(json.dumps(data, indent=2, sort_keys=True))


def _pack_result_dict(result: Any) -> dict[str, Any]:
    return {
        "content_hash": result.content_hash,
        "manifest": result.manifest.to_dict(),
        "pack_id": result.manifest.pack_id,
        "path": str(result.path) if result.path else None,
        "version": result.manifest.version,
    }


if __name__ == "__main__":
    raise SystemExit(main())
