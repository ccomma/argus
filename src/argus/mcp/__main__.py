"""Entry point for ``python -m argus.mcp`` and ``argus-mcp`` console script."""
from __future__ import annotations

import argparse

from argus.mcp.server import MCPServer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="argus-mcp")
    parser.add_argument("--store", default=".argus")
    args = parser.parse_args(argv)
    MCPServer(store=args.store).serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
