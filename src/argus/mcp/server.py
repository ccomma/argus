"""Minimal stdio JSON-RPC 2.0 MCP server for Argus.

Implements the Model Context Protocol (MCP) without third-party dependencies.
Tools delegate to QueryApplication for all read and write operations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

from argus.application.query import QueryApplication
from argus.assets import CapabilityInventory
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.handoff import HandoffManager
from argus.ledger import EventLedger, LearningLedger
from argus.paths import ArgusPaths
from argus.storage import ContractStorage

MCP_VERSION = "2024-11-05"
SERVER_NAME = "argus-mcp"
SERVER_VERSION = "0.1.0"

ToolFn = Callable[[dict[str, Any]], dict[str, Any]]


class MCPServer:
    def __init__(self, store: str | Path = ".argus") -> None:
        self._paths = ArgusPaths.from_store(store)
        self._query_app = self._build_query_app()
        self._tools: dict[str, tuple[str, str, ToolFn]] = {}
        self._register_tools()

    def _build_query_app(self) -> QueryApplication:
        storage = ContractStorage(self._paths.root)
        event_ledger = EventLedger(self._paths.events_ledger)
        learning_ledger = LearningLedger(self._paths.candidate_learnings)
        inventory = CapabilityInventory(self._paths.asset_inventory)
        pack_store = CapabilityPackStore(self._paths.capability_packs_dir)
        role_store = RolePackStore(self._paths.role_packs_dir, pack_store)
        handoff_mgr = HandoffManager(self._paths.root / "handoffs")
        return QueryApplication(
            storage, event_ledger, learning_ledger, inventory,
            pack_store, role_store, handoff_mgr,
        )

    def _register_tools(self) -> None:
        app = self._query_app
        self._tools["query_contracts"] = (
            "List work contracts, optionally filtered by status, workspace, or role.",
            """Filter by status (draft, ready, executing, done), workspace, or role_id.
Returns contracts with associated role handoff records.""",
            lambda args: _list_result(app.query_contracts(
                status=args.get("status", ""),
                role_id=args.get("role_id", ""),
                contract_id=args.get("contract_id", ""),
                workspace=args.get("workspace", ""),
            )),
        )
        self._tools["query_roles"] = (
            "List role capability packs.",
            """Filter by role_id. Returns role definitions with required and optional packs.""",
            lambda args: _list_result(app.query_roles(
                role_id=args.get("role_id", ""),
            )),
        )
        self._tools["query_packs"] = (
            "List capability packs.",
            "Filter by pack_id. Returns pack manifests with assets and risk tiers.",
            lambda args: _list_result(app.query_packs(
                pack_id=args.get("pack_id", ""),
            )),
        )
        self._tools["query_learnings"] = (
            "List candidate learning items.",
            """Filter by contract_id, type (correction, deliverable_gap, tool_pitfall),
scope (project, tool, domain), or min_confidence (0.0-1.0).""",
            lambda args: _list_result(app.query_learnings(
                contract_id=args.get("contract_id", ""),
                learning_type=args.get("type", ""),
                scope=args.get("scope", ""),
                min_confidence=float(args.get("min_confidence", 0)),
            )),
        )
        self._tools["query_assets"] = (
            "List capability assets.",
            """Filter by type (skill, mcp_server, plugin, script, rule, memory),
status (active, deprecated, archived), agent, or risk (low, medium, high).""",
            lambda args: _list_result(app.query_assets(
                asset_type=args.get("type", ""),
                status=args.get("status", ""),
                agent=args.get("agent", ""),
                risk=args.get("risk", ""),
                asset_id=args.get("asset_id", ""),
            )),
        )
        self._tools["check_role"] = (
            "Check a role pack against the current capability inventory.",
            "Returns which required packs are satisfied and which are missing.",
            lambda args: app.check_role(
                role_id=args["role_id"],
                version=args.get("version"),
            ),
        )
        self._tools["run_resolution"] = (
            "Run capability resolution for a named gap.",
            "Searches local assets for matches and returns reuse/install/create decisions.",
            lambda args: _list_result(app.run_resolution(
                gap_name=args["gap_name"],
                gap_description=args.get("gap_description", ""),
            )),
        )
        self._tools["handoff_role"] = (
            "Record a role handoff from one role to another.",
            "Creates a handoff record with context for role-to-role transitions.",
            lambda args: app.handoff_role(
                from_role_id=args["from_role_id"],
                to_role_id=args["to_role_id"],
                contract_id=args.get("contract_id", ""),
                context=args.get("context"),
                handoff_reason=args.get("handoff_reason", ""),
            ),
        )
        self._tools["submit_event"] = (
            "Submit an event to the Argus event ledger.",
            "Accepts source, agent, event_type, evidence, and optional contract/role/session fields.",
            lambda args: {"event_id": app.submit_event(args)},
        )
        self._tools["list_handoffs"] = (
            "List role handoff records.",
            "Filter by role_id or contract_id.",
            lambda args: _list_result(app.list_handoffs(
                role_id=args.get("role_id", ""),
                contract_id=args.get("contract_id", ""),
            )),
        )

    def serve(self) -> None:
        _log("MCP server starting on stdio")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue
            response = self._handle(request)
            if response is not None:
                sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
                sys.stdout.flush()

    def _handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method", "")
        req_id = request.get("id")

        if method == "initialize":
            return self._response(req_id, {
                "protocolVersion": MCP_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            })

        if method == "notifications/initialized":
            return None

        if method == "tools/list":
            tools = [
                {
                    "name": name,
                    "description": desc,
                    "inputSchema": {"type": "object", "properties": {}, "additionalProperties": True},
                }
                for name, (desc, _, _) in self._tools.items()
            ]
            return self._response(req_id, {"tools": tools})

        if method == "tools/call":
            tool_name = request.get("params", {}).get("name", "")
            tool_args = request.get("params", {}).get("arguments", {})
            if tool_name not in self._tools:
                return self._error(req_id, -32601, f"unknown tool: {tool_name}")
            try:
                _, _, fn = self._tools[tool_name]
                result = fn(tool_args)
                return self._response(req_id, {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]})
            except Exception as exc:
                return self._error(req_id, -32603, str(exc))

        return self._error(req_id, -32601, f"unknown method: {method}")

    def _response(self, req_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _error(self, req_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _list_result(items: list) -> dict[str, Any]:
    return {"items": items, "total": len(items)}


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)
