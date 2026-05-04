from __future__ import annotations

"""证据事件工厂模块。

提供将交付物操作（渲染、评估）转换为标准化证据事件字典的函数。
这些事件被追加到合同的 evidence.jsonl 文件中，构成完整的审计追踪链。
"""

from pathlib import Path
from typing import Any

from argus.contracts.deliverables import DeliverableEvaluation


def deliverable_evaluated_event(evaluation: DeliverableEvaluation) -> dict[str, Any]:
    """生成交付物评估事件的证据记录。

    捕获评估的关键信息：交付物类型、通过状态和缺失项，
    为治理审查提供结构化证据。
    """
    return {
        "event_type": "deliverable_evaluated",
        "deliverable_type": evaluation.deliverable_type,
        "status": evaluation.status,
        "missing_items": evaluation.missing_items,
    }


def deliverable_rendered_event(deliverable_type: str, path: str | Path) -> dict[str, Any]:
    """生成交付物渲染事件的证据记录。

    记录渲染的交付物类型和文件路径，
    便于后续追溯交付物版本的来源。
    """
    return {
        "event_type": "deliverable_rendered",
        "deliverable_type": deliverable_type,
        "path": str(path),
    }
