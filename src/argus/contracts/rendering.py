from __future__ import annotations

"""交付物渲染模块。

提供 DeliverableRenderer 类，将工作合同的内容填充到交付物模板中，
生成可阅读的 Markdown 格式交付物文档。支持的交付物类型包括：
PRD（产品需求文档）、Roadmap（路线图）和 Research Plan（研究计划）。
"""

from argus.contracts.models import WorkContract
from argus.contracts.deliverables import DeliverableContract


class DeliverableRenderer:
    """交付物渲染器。

    将 WorkContract 中的结构化字段映射到交付物模板的各个章节，
    生成标准化的 Markdown 交付物文档。

    渲染结果中的"未指定"占位符显式标记信息缺失，有助于
    后续评估步骤（DeliverableEvaluator）检测缺失章节。
    """

    def render(self, contract: WorkContract, deliverable_contract: DeliverableContract) -> str:
        """根据交付物类型将合同内容渲染为对应格式的 Markdown。

        流程：
        1. 根据 deliverable_contract.deliverable_type 判断类型
        2. 调用对应的私有渲染函数进行模板填充
        3. 返回渲染后的 Markdown 字符串
        """
        if deliverable_contract.deliverable_type == "roadmap":
            return _render_roadmap(contract)
        if deliverable_contract.deliverable_type == "research_plan":
            return _render_research_plan(contract)
        return _render_prd(contract)


def _render_prd(contract: WorkContract) -> str:
    """将合同渲染为 PRD（产品需求文档）。

    字段映射：
    - Background ← contract.context 或 contract.intent
    - Goals ← contract.goal
    - Non-goals ← contract.non_goals
    - User Flows ← 模板化的流程描述
    - Success Criteria ← contract.completion_definition
    - Acceptance Criteria ← contract.acceptance_criteria
    """
    return "\n".join(
        [
            "# PRD",
            "",
            "## Background",
            contract.context or contract.intent,
            "",
            "## Goals",
            contract.goal,
            "",
            "## Non-goals",
            contract.non_goals or "Not specified.",
            "",
            "## User Flows",
            f"1. User starts from intent: {contract.intent}",
            "2. Argus clarifies the work contract.",
            "3. Argus produces and evaluates the deliverable.",
            "",
            "## Success Criteria",
            contract.completion_definition,
            "",
            "## Acceptance Criteria",
            contract.acceptance_criteria,
            "",
        ]
    )


def _render_roadmap(contract: WorkContract) -> str:
    """将合同渲染为路线图（Roadmap）。

    包含三个标准阶段：
    1. 澄清工作合同
    2. 产出交付物
    3. 按验收标准评估
    """
    return "\n".join(
        [
            "# Roadmap",
            "",
            "## Goals",
            contract.goal,
            "",
            "## Phases",
            "1. Clarify the work contract.",
            "2. Produce the requested deliverable.",
            "3. Evaluate the deliverable against acceptance criteria.",
            "",
            "## Acceptance Criteria",
            contract.acceptance_criteria,
            "",
            "## Risks",
            contract.risks or "No explicit risks captured.",
            "",
        ]
    )


def _render_research_plan(contract: WorkContract) -> str:
    """将合同渲染为研究计划（Research Plan）。

    字段映射：
    - Questions ← contract.goal 或 contract.intent
    - Sources ← contract.inputs
    - Deliverables ← contract.outputs
    """
    return "\n".join(
        [
            "# Research Plan",
            "",
            "## Questions",
            contract.goal or contract.intent,
            "",
            "## Sources",
            contract.inputs or "Sources to be identified.",
            "",
            "## Deliverables",
            contract.outputs,
            "",
        ]
    )
