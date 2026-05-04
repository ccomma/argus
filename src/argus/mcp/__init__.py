"""MCP 服务模块：通过 Model Context Protocol 对外暴露 Argus 的查询与操作能力。

本模块导出 MCPServer，支持以 JSON-RPC 2.0 over stdio 的方式与外部 MCP 客户端通信。
"""

from __future__ import annotations

from argus.mcp.server import MCPServer

__all__ = ["MCPServer"]
