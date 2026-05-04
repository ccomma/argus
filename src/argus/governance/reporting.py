from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from argus.assets import ACTIVE, CapabilityAsset, CapabilityInventory, find_potential_duplicates
from argus.capability_packs import CapabilityPackStore, RolePackStore
from argus.ledger import CandidateLearningItem, LearningLedger
from argus.storage import ContractStorage

from .models import GovernanceFinding, GovernanceReportResult, PendingAction


class GovernanceReporter:
    def __init__(self, reports_dir: str | Path) -> None:
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
    findings: list[GovernanceFinding] = []
    findings.extend(_dedupe_findings(assets, learnings))
    findings.extend(_stale_asset_findings(assets))
    findings.extend(_risk_findings(assets, pack_store))
    findings.extend(_contract_findings(contract_storage, contracts))
    findings.extend(_role_findings(role_store))
    return findings


def _dedupe_findings(assets: list[CapabilityAsset], learnings: list[CandidateLearningItem]) -> list[GovernanceFinding]:
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
