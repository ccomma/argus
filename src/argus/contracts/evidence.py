from __future__ import annotations

from pathlib import Path
from typing import Any

from argus.contracts.deliverables import DeliverableEvaluation


def deliverable_evaluated_event(evaluation: DeliverableEvaluation) -> dict[str, Any]:
    return {
        "event_type": "deliverable_evaluated",
        "deliverable_type": evaluation.deliverable_type,
        "status": evaluation.status,
        "missing_items": evaluation.missing_items,
    }


def deliverable_rendered_event(deliverable_type: str, path: str | Path) -> dict[str, Any]:
    return {
        "event_type": "deliverable_rendered",
        "deliverable_type": deliverable_type,
        "path": str(path),
    }
