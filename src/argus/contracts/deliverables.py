from __future__ import annotations

"""交付物合约与评估模块。

定义了交付物的合约规范（DeliverableContract）和评估逻辑（DeliverableEvaluator）。
每种交付物类型（PRD、Roadmap、Research Plan）都有各自的必填章节和验收条件，
评估器通过检查交付物文本是否覆盖了所有必填章节来判断交付物质量。
"""

from dataclasses import asdict, dataclass
from typing import Any

from argus.contracts.models import WorkContract


@dataclass(frozen=True)
class DeliverableContract:
    """交付物合约定义。

    描述某类交付物应该包含哪些章节、遵循哪些验收标准。
    例如 PRD 必须包含 Background、Goals、Acceptance Criteria 等章节。

    Attributes:
        id: 交付物合约唯一标识
        deliverable_type: 交付物类型名（prd/roadmap/research_plan）
        required_sections: 必填章节列表
        acceptance_criteria: 验收条件列表
        missing_item_policy: 缺失章节时的处理策略（warn）
    """

    id: str
    deliverable_type: str
    required_sections: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    missing_item_policy: str = "warn"

    @classmethod
    def prd(cls) -> DeliverableContract:
        """PRD（产品需求文档）合约。

        必填章节：Background, Goals, Non-goals, User Flows,
        Success Criteria, Acceptance Criteria。
        验收条件：覆盖合同目标和验收标准。
        """
        return cls(
            id="prd",
            deliverable_type="prd",
            required_sections=(
                "Background",
                "Goals",
                "Non-goals",
                "User Flows",
                "Success Criteria",
                "Acceptance Criteria",
            ),
            acceptance_criteria=("covers_contract_goal", "includes_acceptance_criteria"),
            missing_item_policy="warn",
        )

    @classmethod
    def roadmap(cls) -> DeliverableContract:
        """路线图（Roadmap）合约。

        必填章节：Goals, Phases, Acceptance Criteria, Risks。
        验收条件：覆盖合同目标，包含各阶段的退出条件。
        """
        return cls(
            id="roadmap",
            deliverable_type="roadmap",
            required_sections=("Goals", "Phases", "Acceptance Criteria", "Risks"),
            acceptance_criteria=("covers_contract_goal", "includes_phase_exit_conditions"),
        )

    @classmethod
    def research_plan(cls) -> DeliverableContract:
        """研究计划（Research Plan）合约。

        必填章节：Questions, Sources, Deliverables。
        验收条件：定义了研究问题和交付物。
        """
        return cls(
            id="research_plan",
            deliverable_type="research_plan",
            required_sections=("Questions", "Sources", "Deliverables"),
            acceptance_criteria=("defines_questions", "defines_deliverables"),
        )

    @classmethod
    def for_type(cls, deliverable_type: str) -> DeliverableContract:
        """根据类型字符串返回对应的交付物合约。

        roadmap 和 research_plan 需精准匹配，其余默认返回 PRD。
        """
        if deliverable_type == "roadmap":
            return cls.roadmap()
        if deliverable_type == "research_plan":
            return cls.research_plan()
        return cls.prd()


@dataclass
class DeliverableEvaluation:
    """交付物评估结果。

    记录一次评估的完整结论，包括通过状态、已覆盖和缺失的章节、
    风险提示和后续建议。
    """

    contract_id: str
    deliverable_type: str
    status: str  # 'pass' / 'partial' / 'fail'
    covered_items: list[str]
    missing_items: list[str]
    risks: list[str]
    suggested_follow_ups: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeliverableEvaluation:
        return cls(**data)


class DeliverableEvaluator:
    """交付物评估器。

    检查交付物文本是否满足对应交付物合约的章节要求，
    并结合工作合同的验收标准进行交叉验证。
    """

    def evaluate(
        self,
        contract: WorkContract,
        deliverable_contract: DeliverableContract,
        text: str,
    ) -> DeliverableEvaluation:
        """评估交付物文本的完整性和合规性。

        流程：
        1. 扫描交付物文本，找出交付物合约中要求但缺失的章节
        2. 交叉检查工作合同的验收标准是否在交付物中体现
        3. 根据缺失情况判定状态：pass（全部通过）、partial（部分缺失）、fail（全部缺失）
        4. 生成缺失项的后续建议

        状态判定逻辑：
        - pass: 所有必填章节均存在
        - partial: 有缺失但仍有部分通过
        - fail: 所有必填章节均缺失
        """
        missing = [
            section
            for section in deliverable_contract.required_sections
            if not _has_heading(text, section)
        ]
        risks = []
        # 交叉验证：如果合同有验收标准但交付物中未提及"acceptance"
        if (
            contract.acceptance_criteria
            and "Acceptance Criteria" in deliverable_contract.required_sections
            and "acceptance" not in text.lower()
        ):
            if "Acceptance Criteria" not in missing:
                missing.append("Acceptance Criteria")
            risks.append("Deliverable does not visibly address the work contract acceptance criteria.")

        if not missing:
            status = "pass"
        elif len(missing) < len(deliverable_contract.required_sections):
            status = "partial"
        else:
            status = "fail"

        covered = [section for section in deliverable_contract.required_sections if section not in missing]
        follow_ups = [f"Add or clarify section: {item}" for item in missing]
        return DeliverableEvaluation(
            contract_id=contract.id,
            deliverable_type=deliverable_contract.deliverable_type,
            status=status,
            covered_items=covered,
            missing_items=missing,
            risks=risks,
            suggested_follow_ups=follow_ups,
        )


def _has_heading(text: str, section: str) -> bool:
    """检查交付物文本中是否存在指定的章节标题。

    采用宽松匹配策略：忽略大小写、前导 # 号、以及尾部的冒号，
    以提高章节识别率。例如 "## Background:" 可匹配 "Background"。
    """
    normalized = section.strip().lower()
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip().rstrip(":").lower()
        if stripped == normalized:
            return True
    return False
