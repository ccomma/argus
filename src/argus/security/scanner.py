from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SecurityFinding:
    severity: str
    category: str
    description: str
    location: str = ""
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "location": self.location,
            "evidence": self.evidence,
        }


@dataclass
class ScanReport:
    target: str
    findings: list[SecurityFinding] = field(default_factory=list)
    risk_score: float = 0.0
    passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "findings": [f.to_dict() for f in self.findings],
            "risk_score": self.risk_score,
            "passed": self.passed,
        }


class SecurityScanner:
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
        findings: list[SecurityFinding] = []

        findings.extend(self.scan_prompt_injection(content, location))
        findings.extend(self.scan_supply_chain(content, location))

        if source and source.startswith("http"):
            findings.append(SecurityFinding(
                severity="low",
                category="external_source",
                description=f"Capability from external URL source: {source}",
                location=location,
            ))

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
        return ScanReport(
            target=location or "text_block",
            findings=self.scan_prompt_injection(text, location),
            risk_score=0.0,
            passed=True,
        )
