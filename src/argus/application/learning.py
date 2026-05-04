from __future__ import annotations

from pathlib import Path

from argus.ledger import (
    CandidateLearningItem,
    EventLedger,
    LearningExtractor,
    LearningLedger,
    LearningReport,
    LearningReporter,
)


class LearningApplication:
    def __init__(
        self,
        event_ledger: EventLedger,
        learning_ledger: LearningLedger,
        reports_dir: str | Path,
    ) -> None:
        self.event_ledger = event_ledger
        self.learning_ledger = learning_ledger
        self.reports_dir = Path(reports_dir)

    def extract(self) -> int:
        items = LearningExtractor().extract(self.event_ledger.list_events())
        return self.learning_ledger.append_many(items)

    def list_items(self) -> list[CandidateLearningItem]:
        return self.learning_ledger.list_items()

    def write_report(self) -> LearningReport:
        return LearningReporter(self.reports_dir).write(
            self.event_ledger.list_events(),
            self.learning_ledger.list_items(),
        )
