"""精简的 stdio JSON-RPC 2.0 MCP 服务器，为 Argus 提供外部查询接口。

基于 Model Context Protocol (MCP) 规范，无第三方依赖，通过标准输入输出与 MCP 客户端通信。
所有工具调用最终委托给 QueryApplication 执行读写操作。
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
    """基于 stdio 的 JSON-RPC 2.0 MCP 服务器。

    职责：
    1. 通过标准输入接收 MCP 客户端请求，处理后通过标准输出返回 JSON-RPC 响应
    2. 管理所有工具注册表（tools/list、tools/call）
    3. 处理 MCP 协议握手（initialize/notifications/initialized）
    4. 所有业务逻辑委托给 QueryApplication 执行

    支持的工具包括：查询合同/角色/包/学习项/资产、角色检查、能力解析、
    角色交接记录、事件提交等。
    """

    def __init__(self, store: str | Path = ".argus") -> None:
        """初始化 MCP 服务器。

        1. 从存储目录构建 ArgusPaths
        2. 创建 QueryApplication 及其所有依赖（存储、账本、清单等）
        3. 注册所有 MCP 工具方法
        """
        self._paths = ArgusPaths.from_store(store)
        self._query_app = self._build_query_app()
        self._tools: dict[str, tuple[str, str, ToolFn]] = {}
        self._register_tools()

    def _build_query_app(self) -> QueryApplication:
        """构建 QueryApplication 及其全部依赖组件。

        1. 初始化 ContractStorage（合同存储）
        2. 创建 EventLedger（事件账本）和 LearningLedger（学习账本）
        3. 创建 CapabilityInventory（能力清单）
        4. 创建 CapabilityPackStore 和 RolePackStore（包存储）
        5. 创建 HandoffManager（交接管理器）
        6. 将所有组件注入 QueryApplication
        """
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
        """注册所有 MCP 工具到内部工具表。

        每个工具由一个三元组 (描述, 详细说明, 处理函数) 组成。
        工具列表以字典方式存储，key 为工具名称，便于 O(1) 查找。
        """
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
        """启动 MCP 服务主循环，阻塞读取 stdio 直到输入流关闭。

        1. 逐行读取标准输入
        2. 跳过空行，尝试解析为 JSON-RPC 请求
        3. 非法的 JSON 行静默跳过（保持服务健壮性）
        4. 合法请求通过 _handle 分发处理
        5. 非空响应写入标准输出并立即刷新（确保客户端及时收到）
        """
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
        """分发 JSON-RPC 请求到对应的处理方法。

        1. 提取 method 和 id 字段
        2. 按 method 路由：initialize -> 协议握手、tools/list -> 工具列表、tools/call -> 工具调用
        3. notifications/initialized 返回 None（通知无需响应）
        4. 未知 method 返回 -32601 错误码
        5. 工具执行异常返回 -32603 错误码
        """
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
    """将列表包装为标准结果字典，附带总数便于客户端分页。"""
    return {"items": items, "total": len(items)}


def _log(msg: str) -> None:
    """向 stderr 输出日志（避免污染 stdout 上的 JSON-RPC 通信信道）。"""
    print(msg, file=sys.stderr, flush=True)
