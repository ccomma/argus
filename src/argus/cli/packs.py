"""能力包 + 角色 CLI - propose/create/inspect/check/advise 和 role pack 命令定义和 handler。"""

from __future__ import annotations

import argparse
from typing import Any

from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.cli._common import (
    _asset_inventory,
    _pack_application,
    _pack_result_dict,
    _paths,
    _print_json,
    _role_application,
)


def add_pack_commands(subparsers: Any) -> None:
    """注册能力包子命令：propose/create/inspect/check/advise/list。"""
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


def add_role_commands(subparsers: Any) -> None:
    """注册角色包子命令：create-pack/inspect-pack/check-pack/list。"""
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


def _add_pack_create_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--store", default=".argus")
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--required-asset", action="append", default=[])
    parser.add_argument("--optional-asset", action="append", default=[])
    parser.add_argument("--created-by", default="argus-cli")


def handle_packs_propose(args: argparse.Namespace) -> int:
    result = _pack_application(args).propose(
        pack_id=args.pack_id, display_name=args.display_name,
        description=args.description, required_asset_ids=args.required_asset,
        optional_asset_ids=args.optional_asset, created_by=args.created_by,
    )
    _print_json(_pack_result_dict(result))
    return 0


def handle_packs_create(args: argparse.Namespace) -> int:
    result = _pack_application(args).create(
        pack_id=args.pack_id, display_name=args.display_name,
        description=args.description, required_asset_ids=args.required_asset,
        optional_asset_ids=args.optional_asset, created_by=args.created_by,
    )
    _print_json(_pack_result_dict(result))
    return 0


def handle_packs_inspect(args: argparse.Namespace) -> int:
    manifest, hash_value = _pack_application(args).inspect(args.pack_id, args.version)
    _print_json({"content_hash": hash_value, "manifest": manifest.to_dict()})
    return 0


def handle_packs_check(args: argparse.Namespace) -> int:
    _print_json(_pack_application(args).check(args.pack_id, args.version).to_dict())
    return 0


def handle_packs_advise(args: argparse.Namespace) -> int:
    report = _pack_application(args).advise(args.required_capability)
    _print_json(report.to_dict())
    return 0


def handle_packs_list(args: argparse.Namespace) -> int:
    _print_json([p.to_dict() for p in CapabilityPackStore(_paths(args).capability_packs_dir).list_latest()])
    return 0


def handle_roles_create_pack(args: argparse.Namespace) -> int:
    role_pack = _role_application(args).create(
        role_id=args.role_id, display_name=args.display_name,
        required_pack_ids=args.required_pack, optional_pack_ids=args.optional_pack,
        created_by=args.created_by,
    )
    _print_json(role_pack.to_dict())
    return 0


def handle_roles_inspect_pack(args: argparse.Namespace) -> int:
    _print_json(_role_application(args).inspect(args.role_id, args.version).to_dict())
    return 0


def handle_roles_check_pack(args: argparse.Namespace) -> int:
    _print_json(_role_application(args).check(args.role_id, args.version).to_dict())
    return 0


def handle_roles_list(args: argparse.Namespace) -> int:
    pack_store = CapabilityPackStore(_paths(args).capability_packs_dir)
    _print_json([r.to_dict() for r in RolePackStore(_paths(args).role_packs_dir, pack_store).list_latest()])
    return 0
