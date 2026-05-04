"""CLI 主入口 - 构建参数解析树和命令分发逻辑。"""

from __future__ import annotations

import argparse
import json
import sys

from argus.cli.assets import add_asset_commands
from argus.cli.contracts import add_contract_commands, add_ledger_commands, add_learning_commands
from argus.cli.dashboard import add_maintenance_commands
from argus.cli.governance import add_governance_commands, add_resolve_commands
from argus.cli.handlers import HANDLERS
from argus.cli.modification import add_modify_commands
from argus.cli.packs import add_pack_commands, add_role_commands
from argus.cli.query import add_query_commands
from argus.cli.workbench import (
    add_feedback_commands,
    add_lifecycle_commands,
    add_onboarding_commands,
    add_playbook_commands,
    add_registry_commands,
    add_security_commands,
    add_strategy_commands,
    add_team_commands,
    add_version_lock_commands,
)


def main(argv: list[str] | None = None) -> int:
    """构建 Argus CLI 的完整参数解析树，支持 16 个命令族。

    1. 创建主解析器和子命令解析器
    2. 各命令族注册自己的子命令（contract/ledger/learning 等）
    3. 调用 _dispatch 将解析结果分发给对应的 handler
    """
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

    add_contract_commands(contract_subparsers)
    add_ledger_commands(ledger_subparsers)
    add_learning_commands(learning_subparsers)
    add_asset_commands(assets_subparsers)
    add_pack_commands(packs_subparsers)
    add_role_commands(roles_subparsers)
    add_governance_commands(governance_subparsers)
    add_resolve_commands(resolve_subparsers)
    add_modify_commands(modify_subparsers)
    add_query_commands(query_subparsers)
    mcp_serve.add_argument("--store", default=".argus")
    dashboard.add_argument("--store", default=".argus")
    add_maintenance_commands(maintenance_subparsers)

    web = subparsers.add_parser("web", help="Start the local Argus workbench web server.")
    web.add_argument("--store", default=".argus")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8765)

    strategy = subparsers.add_parser("strategy", help="Strategy and policy configuration.")
    strategy_subparsers = strategy.add_subparsers(dest="strategy_command", required=True)
    add_strategy_commands(strategy_subparsers)

    playbook = subparsers.add_parser("playbook", help="Personal playbook commands.")
    playbook_subparsers = playbook.add_subparsers(dest="playbook_command", required=True)
    add_playbook_commands(playbook_subparsers)

    version_lock = subparsers.add_parser("version-lock", help="Capability version lock commands.")
    version_lock_subparsers = version_lock.add_subparsers(dest="version_lock_command", required=True)
    add_version_lock_commands(version_lock_subparsers)

    security = subparsers.add_parser("security", help="Security scanning commands.")
    security_subparsers = security.add_subparsers(dest="security_command", required=True)
    add_security_commands(security_subparsers)

    team = subparsers.add_parser("team", help="Team management commands.")
    team_subparsers = team.add_subparsers(dest="team_command", required=True)
    add_team_commands(team_subparsers)

    onboarding = subparsers.add_parser("onboarding", help="Repo onboarding pack commands.")
    onboarding_subparsers = onboarding.add_subparsers(dest="onboarding_command", required=True)
    add_onboarding_commands(onboarding_subparsers)

    lifecycle = subparsers.add_parser("lifecycle", help="Asset lifecycle management commands.")
    lifecycle_subparsers = lifecycle.add_subparsers(dest="lifecycle_command", required=True)
    add_lifecycle_commands(lifecycle_subparsers)

    registry = subparsers.add_parser("registry", help="Multi-registry capability discovery.")
    registry_subparsers = registry.add_subparsers(dest="registry_command", required=True)
    add_registry_commands(registry_subparsers)

    feedback = subparsers.add_parser("feedback", help="Closed-loop learning feedback commands.")
    feedback_subparsers = feedback.add_subparsers(dest="feedback_command", required=True)
    add_feedback_commands(feedback_subparsers)

    args = parser.parse_args(argv)
    return _dispatch(parser, args)


def _dispatch(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """将解析后的命名空间分发给对应的 handler 函数。

    1. 顶层命令（mcp-serve/dashboard/web）直接查询 HANDLERS
    2. 二级命令从 args 中提取子命令名，查找二维 HANDLERS 字典
    3. 未找到匹配时输出错误并返回非零码
    """
    if args.command == "mcp-serve":
        return HANDLERS["mcp_serve"](args)
    if args.command == "dashboard":
        return HANDLERS["dashboard"](args)
    if args.command == "web":
        return HANDLERS["web"](args)

    subcommand = getattr(args, f"{args.command.replace('-', '_')}_command")
    try:
        handler = HANDLERS.get((args.command, subcommand))
        if handler:
            return handler(args)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    parser.error("unknown command")
    return 2
