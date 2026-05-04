"""python -m argus.cli 入口 - 支持模块直接运行启动 CLI。"""

from __future__ import annotations

import sys

from argus.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
