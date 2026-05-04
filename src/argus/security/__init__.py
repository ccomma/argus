"""安全模块：提供 AI Agent 能力资产的安全扫描能力。

SecurityScanner 检测提示注入攻击和供应链风险模式，
为每个能力资产生成 ScanReport，包含风险评分和通过/失败判定。
"""

from __future__ import annotations

from argus.security.scanner import SecurityScanner

__all__ = ["SecurityScanner"]
