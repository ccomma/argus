"""MCP 服务入口：支持 ``python -m argus.mcp`` 和 ``argus-mcp`` 控制台命令。

接收 --store 参数指定 Argus 数据存储目录，启动 MCPServer 并进入 stdio 事件循环。
"""

from __future__ import annotations

import argparse

from argus.mcp.server import MCPServer


def main(argv: list[str] | None = None) -> int:
    """MCP 服务主入口函数。

    1. 解析命令行参数（--store 指定数据目录，默认 .argus）
    2. 创建 MCPServer 实例并调用 serve() 进入 stdio 循环
    3. 正常退出返回 0
    """
    parser = argparse.ArgumentParser(prog="argus-mcp")
    parser.add_argument("--store", default=".argus")
    args = parser.parse_args(argv)
    MCPServer(store=args.store).serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
