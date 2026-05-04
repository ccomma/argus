"""学习应用服务，从事件中提取候选学习项并生成报告。

将事件账本中的证据转化为结构化的候选学习项（CandidateLearningItem），
驱动 Argus 的持续改进循环。
"""

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
    """学习子系统应用门面，编排事件提取、学习项存储和报告生成。"""

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
        """从事件账本中提取候选学习项并持久化，返回新增的条目数量。

        1. 从事件账本获取全部事件记录
        2. 使用 LearningExtractor 从中提取结构化学习项
        3. 将提取结果批量写入学习账本
        """
        items = LearningExtractor().extract(self.event_ledger.list_events())
        return self.learning_ledger.append_many(items)

    def list_items(self) -> list[CandidateLearningItem]:
        """列出当前所有候选学习项。"""
        return self.learning_ledger.list_items()

    def write_report(self) -> LearningReport:
        """生成学习报告，包含事件摘要与提取的学习项。"""
        return LearningReporter(self.reports_dir).write(
            self.event_ledger.list_events(),
            self.learning_ledger.list_items(),
        )
