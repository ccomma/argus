"""安全扫描器：检测 AI Agent 能力资产中的提示注入和供应链风险。

SecurityScanner 维护两组模式列表（提示注入模式 + 供应链风险模式），
通过模式匹配扫描文本内容，生成 SecurityFinding 列表和 ScanReport。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SecurityFinding:
    """单个安全发现（不可变数据类）。

    记录检测到的威胁信息：严重等级、类别、描述、位置和证据。
    """
    severity: str
    category: str
    description: str
    location: str = ""
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "location": self.location,
            "evidence": self.evidence,
        }


@dataclass
class ScanReport:
    """安全扫描报告。

    汇总单次扫描的结果，包括目标标识、发现列表、风险评分和通过/失败判定。
    风险评分 = min(1.0, 发现数量 * 0.15)，存在 high 级别发现时 passed = False。
    """
    target: str
    findings: list[SecurityFinding] = field(default_factory=list)
    risk_score: float = 0.0
    passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        """序列化报告为字典。"""
        return {
            "target": self.target,
            "findings": [f.to_dict() for f in self.findings],
            "risk_score": self.risk_score,
            "passed": self.passed,
        }


class SecurityScanner:
    """安全扫描器。

    职责：检测 AI Agent 能力资产中的安全威胁，包括两类攻击模式：
    1. 提示注入：检测试图覆盖/绕过系统指令的文本模式
    2. 供应链风险：检测嵌入恶意代码的模式（shell 管道、eval、subprocess 等）
    """

    # 提示注入检测模式：匹配常见的 prompt injection 攻击文本
    PROMPT_INJECTION_PATTERNS = [
        "ignore previous instructions",
        "ignore all previous",
        "disregard prior",
        "override system prompt",
        "you are now",
        "forget all rules",
        "pretend you are",
        "act as if",
        "do not follow",
        "bypass restrictions",
        "system: override",
        "<system>",
        "[system]",
        "new instructions:",
    ]

    # 供应链风险模式：检测代码中的危险调用模式
    SUPPLY_CHAIN_RISK_PATTERNS = [
        "| bash",
        "| sh",
        "eval(",
        "exec(",
        "__import__",
        "os.system",
        "subprocess.call",
        "subprocess.Popen",
        "rm -rf /",
        "chmod 777",
    ]

    def scan_prompt_injection(self, content: str, location: str = "") -> list[SecurityFinding]:
        """扫描文本中的提示注入模式。

        1. 将内容转为小写后逐模式匹配
        2. 每命中一个模式生成一条 high 级别 SecurityFinding
        3. 对 content 和 pattern 均做大小写不敏感比较
        """
        findings: list[SecurityFinding] = []
        content_lower = content.lower()
        for pattern in self.PROMPT_INJECTION_PATTERNS:
            if pattern.lower() in content_lower:
                findings.append(SecurityFinding(
                    severity="high",
                    category="prompt_injection",
                    description=f"Potential prompt injection pattern detected: '{pattern}'",
                    location=location,
                    evidence=pattern,
                ))
        return findings

    def scan_supply_chain(self, content: str, location: str = "") -> list[SecurityFinding]:
        """扫描文本中的供应链风险模式。

        1. 将内容与 SUPPLY_CHAIN_RISK_PATTERNS 中的模式逐条比对
        2. 每命中一个模式生成一条 high 级别 SecurityFinding
        3. 大小写不敏感匹配
        """
        findings: list[SecurityFinding] = []
        for pattern in self.SUPPLY_CHAIN_RISK_PATTERNS:
            if pattern.lower() in content.lower():
                findings.append(SecurityFinding(
                    severity="high",
                    category="supply_chain",
                    description=f"Potentially unsafe pattern detected: '{pattern}'",
                    location=location,
                    evidence=pattern,
                ))
        return findings

    def scan_capability(self, content: str, source: str = "", location: str = "") -> ScanReport:
        """对能力资产执行完整安全扫描。

        1. 依次执行提示注入扫描和供应链风险扫描
        2. 若能力来源于外部 URL，追加一条 low 级别的 external_source 发现
        3. 风险评分 = min(1.0, 发现数量 * 0.15)，上限 1.0
        4. 存在任何 high 严重度发现则 passed = False
        5. 汇总生成 ScanReport
        """
        findings: list[SecurityFinding] = []

        findings.extend(self.scan_prompt_injection(content, location))
        findings.extend(self.scan_supply_chain(content, location))

        # 外部来源的能力资产标记为低风险（透明度问题）
        if source and source.startswith("http"):
            findings.append(SecurityFinding(
                severity="low",
                category="external_source",
                description=f"Capability from external URL source: {source}",
                location=location,
            ))

        # 线性风险评分：每条发现贡献 0.15，上限 1.0
        risk_score = min(1.0, len(findings) * 0.15)
        high_findings = [f for f in findings if f.severity == "high"]
        passed = len(high_findings) == 0

        return ScanReport(
            target=location or source or "unknown",
            findings=findings,
            risk_score=risk_score,
            passed=passed,
        )

    def scan_text_block(self, text: str, location: str = "") -> ScanReport:
        """对纯文本块执行快速安全扫描（仅提示注入检测）。"""
        return ScanReport(
            target=location or "text_block",
            findings=self.scan_prompt_injection(text, location),
            risk_score=0.0,
            passed=True,
        )
