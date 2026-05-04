"""查询 + MCP CLI - 跨组件查询和 MCP JSON-RPC 服务的命令定义和 handler。"""

from __future__ import annotations

import argparse
from typing import Any

from argus.cli._common import _print_json, _query_application
from argus.mcp import MCPServer


def add_query_commands(subparsers: Any) -> None:
    """注册查询子命令：contract/role。"""
    contract = subparsers.add_parser("contract", help="Query contracts with related objects.")
    contract.add_argument("contract_id")
    contract.add_argument("--store", default=".argus")

    role = subparsers.add_parser("role", help="Query a role with related packs and handoffs.")
    role.add_argument("role_id")
    role.add_argument("--store", default=".argus")


def handle_query_contract(args: argparse.Namespace) -> int:
    results = _query_application(args).query_contracts(contract_id=args.contract_id)
    _print_json(results)
    return 0


def handle_query_role(args: argparse.Namespace) -> int:
    results = _query_application(args).query_roles(role_id=args.role_id)
    _print_json(results)
    return 0


def handle_mcp_serve(args: argparse.Namespace) -> int:
    MCPServer(store=args.store).serve()
    return 0
