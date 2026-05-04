from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any, Callable

from argus.ledger.jsonl import AppendOnlyJsonlStore
from argus.ledger.models import EventRecord


@dataclass(frozen=True)
class CandidateLearningItem:
    id: str
    summary: str
    type: str
    scope: str
    confidence: float
    evidence_refs: list[str]
    reverse_learning_target: str
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CandidateLearningItem:
        return cls(**data)

    @classmethod
    def create(
        cls,
        *,
        summary: str,
        type: str,
        evidence_refs: list[str],
        scope: str = "project",
        confidence: float = 0.6,
        reverse_learning_target: str = "none",
    ) -> CandidateLearningItem:
        payload = {
            "summary": summary,
            "type": type,
            "evidence_refs": evidence_refs,
            "scope": scope,
            "reverse_learning_target": reverse_learning_target,
        }
        digest = sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        return cls(
            id=f"learning-{digest}",
            summary=summary,
            type=type,
            scope=scope,
            confidence=confidence,
            evidence_refs=evidence_refs,
            reverse_learning_target=reverse_learning_target,
        )


class LearningExtractor:
    def __init__(self, rules: list[Callable[[list[EventRecord]], list[CandidateLearningItem]]] | None = None) -> None:
        self.rules = rules or [
            _user_correction_learnings,
            _deliverable_gap_learnings,
            _tool_pitfall_learnings,
        ]

    def extract(self, events: list[EventRecord]) -> list[CandidateLearningItem]:
        candidates: list[CandidateLearningItem] = []
        for rule in self.rules:
            candidates.extend(rule(events))
        return _deduplicate(candidates)


class LearningLedger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._store = AppendOnlyJsonlStore(
            self.path,
            serializer=lambda item: item.to_dict(),
            deserializer=CandidateLearningItem.from_dict,
            identity=lambda item: item.id,
        )

    def append(self, item: CandidateLearningItem) -> bool:
        return self._store.append(item)

    def append_many(self, items: list[CandidateLearningItem]) -> int:
        return self._store.append_many(items)

    def list_items(self) -> list[CandidateLearningItem]:
        return self._store.list_items()


@dataclass(frozen=True)
class LearningReport:
    markdown_path: Path
    json_path: Path


class LearningReporter:
    def __init__(self, reports_dir: str | Path) -> None:
        self.reports_dir = Path(reports_dir)

    def write(self, events: list[EventRecord], items: list[CandidateLearningItem]) -> LearningReport:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = self.reports_dir / "learning-report.md"
        json_path = self.reports_dir / "learning-report.json"
        markdown_path.write_text(_markdown_report(events, items), encoding="utf-8")
        json_path.write_text(
            json.dumps(
                {
                    "event_count": len(events),
                    "candidate_learning_count": len(items),
                    "candidate_learnings": [item.to_dict() for item in items],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return LearningReport(markdown_path=markdown_path, json_path=json_path)


def _summary(event: EventRecord, fallback: str) -> str:
    evidence = event.evidence or {}
    return evidence.get("message") or evidence.get("summary") or fallback


def _user_correction_learnings(events: list[EventRecord]) -> list[CandidateLearningItem]:
    return [
        CandidateLearningItem.create(
            summary=_summary(event, "User correction may indicate a stable project or user preference."),
            type="correction",
            scope="project",
            confidence=0.75,
            evidence_refs=[event.id],
            reverse_learning_target="question_strategy",
        )
        for event in events
        if event.event_type == "user_correction"
    ]


def _deliverable_gap_learnings(events: list[EventRecord]) -> list[CandidateLearningItem]:
    return [
        CandidateLearningItem.create(
            summary="Deliverable evaluation found missing required items.",
            type="deliverable_gap",
            scope="project",
            confidence=0.7,
            evidence_refs=[event.id],
            reverse_learning_target="deliverable_contract",
        )
        for event in events
        if event.event_type == "deliverable_evaluated" and event.execution_evidence.get("status") in {"partial", "fail"}
    ]


def _tool_pitfall_learnings(events: list[EventRecord]) -> list[CandidateLearningItem]:
    command_failures = [event for event in events if event.event_type == "command_failed"]
    if not command_failures:
        return []
    recoveries = [event for event in events if event.event_type == "command_recovered"]
    refs = [event.id for event in command_failures + recoveries]
    return [
        CandidateLearningItem.create(
            summary="A command failed and may need a documented recovery path.",
            type="tool_pitfall",
            scope="tool",
            confidence=0.8 if recoveries else 0.55,
            evidence_refs=refs,
            reverse_learning_target="capability_pack",
        )
    ]


def _deduplicate(items: list[CandidateLearningItem]) -> list[CandidateLearningItem]:
    seen = set()
    result = []
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        result.append(item)
    return result


def _markdown_report(events: list[EventRecord], items: list[CandidateLearningItem]) -> str:
    lines = [
        "# Argus Learning Report",
        "",
        f"- Events: {len(events)}",
        f"- Candidate Learnings: {len(items)}",
        "",
        "## Candidate Learnings",
        "",
    ]
    if not items:
        lines.append("No candidate learnings yet.")
    for item in items:
        lines.extend(
            [
                f"### {item.summary}",
                "",
                f"- Type: {item.type}",
                f"- Scope: {item.scope}",
                f"- Confidence: {item.confidence}",
                f"- Evidence: {', '.join(item.evidence_refs)}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"
