from __future__ import annotations

"""治理报告生成模块。

提供 GovernanceReporter 类——从各方数据源（合同存储、学习账本、
资产清单、能力包、角色包）聚合信息，生成综合性的治理报告。

报告包含四大组成部分：
1. 治理发现（findings）：系统性地发现重复、过期、风险、合同和角色问题
2. 待处理操作（pending_actions）：从发现中提炼的可执行操作
3. 低风险维护日志（low_risk_log）：只读操作的审计记录
4. 汇总统计（summary）：各系统组件的计数概况
"""

import json
from pathlib import Path
from typing import Any

from argus.assets import ACTIVE, CapabilityAsset, CapabilityInventory, find_potential_duplicates
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.ledger import CandidateLearningItem, LearningLedger
from argus.storage import ContractStorage

from .models import GovernanceFinding, GovernanceReportResult, PendingAction


class GovernanceReporter:
    """治理报告生成器。

    作为 Argus 系统治理层的核心组件，定期（或按需）生成
    全面的系统健康度报告。报告覆盖合同的完整性、资产的健康状态、
    能力包的合理性以及学习项的重复情况。
    """

    def __init__(self, reports_dir: str | Path) -> None:
        """初始化治理报告器。

        Args:
            reports_dir: 报告输出目录
        """
        self.reports_dir = Path(reports_dir)

    def write(
        self,
        *,
        contract_storage: ContractStorage,
        learning_ledger: LearningLedger,
        inventory: CapabilityInventory,
        pack_store: CapabilityPackStore,
        role_store: RolePackStore,
    ) -> GovernanceReportResult:
        """生成完整的治理报告。

        流程：
        1. 从各数据源加载数据（资产、学习项、合同、能力包、角色包）
        2. 运行五类发现检查：
           a. _dedupe_findings: 检测重复资产和学习项
           b. _stale_asset_findings: 检测过期资产
           c. _risk_findings: 检测高风险资产和能力包
           d. _contract_findings: 检测合同完整性问题和评估缺口
           e. _role_findings: 检测角色包配置问题
        3. 从发现中提炼待处理操作
        4. 生成低风险维护日志
        5. 输出四份文件（Markdown 报告、JSON 报告、低风险日志、待处理操作）

        这种分层发现机制确保每类问题由专用的检查函数处理，
        便于单独测试和扩展。
        """
        assets = inventory.list_assets()
        learnings = learning_ledger.list_items()
        contracts = contract_storage.list_contracts()
        findings = _findings(contract_storage, contracts, learnings, assets, pack_store, role_store)
        pending_actions = _pending_actions(findings)
        low_risk_log = _low_risk_log(findings, learnings, assets)
        payload = {
            "summary": {
                "work_contracts": len(contracts),
                "candidate_learnings": len(learnings),
                "assets": len(assets),
                "capability_packs": len(pack_store.list_latest()),
                "role_packs": len(role_store.list_latest()),
            },
            "findings": [finding.to_dict() for finding in findings],
            "low_risk_maintenance_log": low_risk_log,
            "pending_actions": [action.to_dict() for action in pending_actions],
        }
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = self.reports_dir / "governance-report.md"
        json_path = self.reports_dir / "governance-report.json"
        low_risk_log_path = self.reports_dir / "low-risk-maintenance-log.json"
        pending_actions_path = self.reports_dir / "pending-actions.json"
        markdown_path.write_text(_markdown_report(payload), encoding="utf-8")
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        low_risk_log_path.write_text(json.dumps(low_risk_log, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        pending_actions_path.write_text(
            json.dumps([action.to_dict() for action in pending_actions], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return GovernanceReportResult(
            markdown_path=markdown_path,
            json_path=json_path,
            low_risk_log_path=low_risk_log_path,
            pending_actions_path=pending_actions_path,
        )


def _findings(
    contract_storage: ContractStorage,
    contracts: list[Any],
    learnings: list[CandidateLearningItem],
    assets: list[CapabilityAsset],
    pack_store: CapabilityPackStore,
    role_store: RolePackStore,
) -> list[GovernanceFinding]:
    """汇总所有治理发现。

    依次执行五类检查并汇总结果。每类检查相互独立，
    可以单独扩展或禁用某一类而不影响其他。
    """
    findings: list[GovernanceFinding] = []
    findings.extend(_dedupe_findings(assets, learnings))
    findings.extend(_stale_asset_findings(assets))
    findings.extend(_risk_findings(assets, pack_store))
    findings.extend(_contract_findings(contract_storage, contracts))
    findings.extend(_role_findings(role_store))
    return findings


def _dedupe_findings(assets: list[CapabilityAsset], learnings: list[CandidateLearningItem]) -> list[GovernanceFinding]:
    """检测重复的资产和学习项。

    资产重复：通过 find_potential_duplicates 发现同名但不同 ID 的资产。
    学习项重复：通过 (summary, type, reverse_learning_target) 三元组去重检测。
    """
    findings: list[GovernanceFinding] = []
    for group in find_potential_duplicates(assets):
        findings.append(
            GovernanceFinding(
                category="dedupe",
                severity="low",
                subject_id=",".join(asset.id for asset in group),
                summary="Potential duplicate capability assets: " + ", ".join(asset.name for asset in group),
                recommended_action="Review duplicate assets before any merge or archive action.",
            )
        )
    seen = set()
    for item in learnings:
        key = (item.summary, item.type, item.reverse_learning_target)
        if key in seen:
            findings.append(
                GovernanceFinding(
                    category="dedupe",
                    severity="low",
                    subject_id=item.id,
                    summary="Duplicate candidate learning detected.",
                    recommended_action="Keep as report-only until a governed dedupe action exists.",
                )
            )
        seen.add(key)
    return findings


def _stale_asset_findings(assets: list[CapabilityAsset]) -> list[GovernanceFinding]:
    """检测过期资产（状态非 ACTIVE）。

    任何标记为 archived/disabled/isolated/deprecated 的资产
    都会被报告，建议审查依赖这些资产的包是否需要更新。
    """
    return [
        GovernanceFinding(
            category="stale",
            severity="medium",
            subject_id=asset.id,
            summary=f"Capability asset is marked {asset.status}.",
            recommended_action="Review whether dependent packs should keep using this asset.",
        )
        for asset in assets
        if asset.status != ACTIVE
    ]


def _risk_findings(assets: list[CapabilityAsset], pack_store: CapabilityPackStore) -> list[GovernanceFinding]:
    """检测高风险资产和能力包。

    资产风险：risk_score >= 0.5 的标记为 medium，>= 0.7 的标记为 high。
    能力包风险：aggregate_risk_tier_snapshot 为 high 或 critical 的包。
    """
    findings = [
        GovernanceFinding(
            category="risk",
            severity="high" if asset.risk_score >= 0.7 else "medium",
            subject_id=asset.id,
            summary=f"Capability asset has elevated risk score {asset.risk_score}.",
            recommended_action="Require human review before expanding use of this asset.",
        )
        for asset in assets
        if asset.risk_score >= 0.5
    ]
    for pack in pack_store.list_latest():
        if pack.aggregate_risk_tier_snapshot in {"high", "critical"}:
            findings.append(
                GovernanceFinding(
                    category="risk",
                    severity=pack.aggregate_risk_tier_snapshot,
                    subject_id=pack.pack_id,
                    summary=f"Capability pack aggregate risk is {pack.aggregate_risk_tier_snapshot}.",
                    recommended_action="Review pack risk before execution.",
                )
            )
    return findings


def _contract_findings(contract_storage: ContractStorage, contracts: list[Any]) -> list[GovernanceFinding]:
    """检测合同相关的问题。

    两类检查：
    1. 合同完整性不足（completeness_score < 0.85）
    2. 交付物评估发现缺失项
    """
    findings: list[GovernanceFinding] = []
    for contract in contracts:
        if contract.completeness_score.overall_score < 0.85:
            findings.append(
                GovernanceFinding(
                    category="work_contract",
                    severity="medium",
                    subject_id=contract.id,
                    summary=contract.completeness_score.rationale,
                    recommended_action="Ask missing question strategy fields before execution.",
                )
            )
        for evaluation in contract_storage.list_evaluations(contract.id):
            if evaluation.missing_items:
                findings.append(
                    GovernanceFinding(
                        category="work_contract",
                        severity="medium",
                        subject_id=contract.id,
                        summary="Deliverable evaluation found missing items: " + ", ".join(evaluation.missing_items),
                        recommended_action="Tighten deliverable contract or regenerate the deliverable.",
                    )
                )
    return findings


def _role_findings(role_store: RolePackStore) -> list[GovernanceFinding]:
    """检测角色包配置问题。

    三类检查：
    1. 没有必选能力包的角色（可能是未完成配置）
    2. 高风险角色（risk_level 为 high 或 critical）
    3. 正常的角色（记录为低优先级观察）
    """
    findings: list[GovernanceFinding] = []
    for role_pack in role_store.list_latest():
        if not role_pack.required_pack_refs:
            findings.append(
                GovernanceFinding(
                    category="role",
                    severity="medium",
                    subject_id=role_pack.role_id,
                    summary="Role pack has no required capability packs.",
                    recommended_action="Attach at least one required pack or mark the role as exploratory.",
                )
            )
        elif role_pack.risk_level in {"high", "critical"}:
            findings.append(
                GovernanceFinding(
                    category="role",
                    severity=role_pack.risk_level,
                    subject_id=role_pack.role_id,
                    summary=f"Role pack risk level is {role_pack.risk_level}.",
                    recommended_action="Review role activation policy before use.",
                )
            )
        else:
            findings.append(
                GovernanceFinding(
                    category="role",
                    severity="low",
                    subject_id=role_pack.role_id,
                    summary="Role pack has reusable capability pack references.",
                    recommended_action="Track role use and revisit after execution evidence exists.",
                )
            )
    return findings


def _pending_actions(findings: list[GovernanceFinding]) -> list[PendingAction]:
    """从治理发现中提炼待处理操作。

    三类操作映射：
    1. 合同问题 → question_strategy_improvement 或 deliverable_contract_improvement
    2. 去重/过期/风险/角色问题 → {category}_review
    3. 低严重度操作不需要人工确认（requires_confirmation=False）
    """
    actions = [
        PendingAction(
            type="question_strategy_improvement",
            risk_level="medium",
            subject_id=finding.subject_id,
            summary=finding.recommended_action,
            requires_confirmation=True,
        )
        for finding in findings
        if finding.category == "work_contract" and "question strategy" in finding.recommended_action
    ]
    actions.extend(
        PendingAction(
            type="deliverable_contract_improvement",
            risk_level="medium",
            subject_id=finding.subject_id,
            summary=finding.recommended_action,
            requires_confirmation=True,
        )
        for finding in findings
        if "deliverable contract" in finding.recommended_action
    )
    actions.extend(
        PendingAction(
            type=f"{finding.category}_review",
            risk_level=finding.severity,
            subject_id=finding.subject_id,
            summary=finding.recommended_action,
            requires_confirmation=finding.severity != "low",
        )
        for finding in findings
        if finding.category in {"dedupe", "stale", "risk", "role"}
    )
    return actions


def _low_risk_log(
    findings: list[GovernanceFinding],
    learnings: list[CandidateLearningItem],
    assets: list[CapabilityAsset],
) -> list[dict[str, Any]]:
    """生成低风险维护日志。

    记录只读性质的操作（如生成报告、扫描信号），
    这些操作不产生副作用但提供了审计透明度。
    """
    return [
        {
            "action": "generated_governance_report",
            "risk_level": "low",
            "details": "Read-only governance report generated.",
        },
        {
            "action": "scanned_for_duplicate_signals",
            "risk_level": "low",
            "details": f"Checked {len(assets)} assets, {len(learnings)} learnings, {len(findings)} findings.",
        },
    ]


def _markdown_report(payload: dict[str, Any]) -> str:
    """将治理报告 payload 渲染为 Markdown 格式。

    包含四个章节：Summary、Findings、Pending Actions、Low-Risk Maintenance Log。
    """
    lines = [
        "# Argus Governance Report",
        "",
        "## Summary",
        "",
    ]
    for key, value in payload["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Findings", ""])
    if not payload["findings"]:
        lines.append("No governance findings.")
    for finding in payload["findings"]:
        lines.append(
            f"- [{finding['severity']}] {finding['category']} {finding['subject_id']}: {finding['summary']}"
        )
    lines.extend(["", "## Pending Actions", ""])
    if not payload["pending_actions"]:
        lines.append("No pending actions.")
    for action in payload["pending_actions"]:
        lines.append(f"- {action['type']} ({action['risk_level']}): {action['summary']}")
    lines.extend(["", "## Low-Risk Maintenance Log", ""])
    for entry in payload["low_risk_maintenance_log"]:
        lines.append(f"- {entry['action']}: {entry['details']}")
    return "\n".join(lines) + "\n"
