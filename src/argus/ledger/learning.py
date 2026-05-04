from __future__ import annotations

"""学习提取与报告模块。

提供从事件流中自动提取候选学习项（CandidateLearningItem）的能力。
通过可配置的规则引擎，从用户修正、交付物缺口和工具故障等事件中
识别可复用的经验，并生成结构化的学习报告。

这是 Argus 系统的"自我改进"层——将执行过程中积累的经验
转化为可持久化和可引用的知识资产。
"""

import json
from dataclasses import asdict, dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any, Callable

from argus.ledger.jsonl import AppendOnlyJsonlStore
from argus.ledger.models import EventRecord


@dataclass(frozen=True)
class CandidateLearningItem:
    """候选学习项。

    从事件账本中自动提取的一条可复用经验。每条学习项包含学习摘要、
    类型、范围、置信度以及逆向学习目标（reverse_learning_target），
    后者指示该学习可以改进系统中的哪个组件。

    Attributes:
        id: 基于内容 SHA1 的唯一标识
        summary: 学习摘要
        type: 学习类型（correction / deliverable_gap / tool_pitfall）
        scope: 适用范围（project / tool）
        confidence: 置信度（0-1）
        evidence_refs: 引用的证据事件 ID 列表
        reverse_learning_target: 该学习可改进的组件目标
        status: 状态（默认 pending）
    """

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
        """工厂方法：基于内容摘要创建学习项。

        使用 SHA1 摘要生成确定性 ID，确保相同内容的学习项不会重复存储。
        """
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
    """候选学习项提取器。

    基于可配置的规则集从事件列表中提取学习项。
    默认规则集覆盖三种场景：
    - 用户修正事件 → "用户偏好"类学习
    - 交付物评估缺口 → "交付物合约改进"类学习
    - 命令失败事件 → "工具陷阱"类学习
    """

    def __init__(self, rules: list[Callable[[list[EventRecord]], list[CandidateLearningItem]]] | None = None) -> None:
        """初始化提取器。

        Args:
            rules: 自定义规则列表，每项规则接收事件列表返回学习项列表。
                   未提供时使用默认规则集。
        """
        self.rules = rules or [
            _user_correction_learnings,
            _deliverable_gap_learnings,
            _tool_pitfall_learnings,
        ]

    def extract(self, events: list[EventRecord]) -> list[CandidateLearningItem]:
        """从事件列表中提取所有候选学习项。

        流程：
        1. 依次执行每条提取规则
        2. 合并所有规则产出的学习项
        3. 按 ID 去重后返回

        这样设计使得规则可以独立添加和组合，而不相互干扰。
        """
        candidates: list[CandidateLearningItem] = []
        for rule in self.rules:
            candidates.extend(rule(events))
        return _deduplicate(candidates)


class LearningLedger:
    """候选学习项账本。

    基于 AppendOnlyJsonlStore 的持久化存储层，
    负责学习项的追加和查询。
    """

    def __init__(self, path: str | Path) -> None:
        """初始化学习账本。

        Args:
            path: 学习项 JSONL 文件路径
        """
        self.path = Path(path)
        self._store = AppendOnlyJsonlStore(
            self.path,
            serializer=lambda item: item.to_dict(),
            deserializer=CandidateLearningItem.from_dict,
            identity=lambda item: item.id,
        )

    def append(self, item: CandidateLearningItem) -> bool:
        """追加单条学习项。"""
        return self._store.append(item)

    def append_many(self, items: list[CandidateLearningItem]) -> int:
        """批量追加学习项。"""
        return self._store.append_many(items)

    def list_items(self) -> list[CandidateLearningItem]:
        """列出所有已存储的学习项。"""
        return self._store.list_items()


@dataclass(frozen=True)
class LearningReport:
    """学习报告的产物路径。

    包含 Markdown 格式的可读报告和 JSON 格式的结构化数据。
    """

    markdown_path: Path
    json_path: Path


class LearningReporter:
    """学习报告生成器。

    将事件和候选学习项整理为可读的 Markdown 报告和结构化的 JSON 报告。
    """

    def __init__(self, reports_dir: str | Path) -> None:
        """初始化报告器。

        Args:
            reports_dir: 报告输出目录
        """
        self.reports_dir = Path(reports_dir)

    def write(self, events: list[EventRecord], items: list[CandidateLearningItem]) -> LearningReport:
        """生成学习报告。

        流程：
        1. 创建报告目录
        2. 生成 learning-report.md（人类可读格式）
        3. 生成 learning-report.json（机器可读格式）
        4. 返回包含两个路径的 LearningReport 对象
        """
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
    """从事件的 evidence 中提取可读摘要。

    优先使用 evidence 中的 message 字段，其次 summary，最后使用 fallback。
    """
    evidence = event.evidence or {}
    return evidence.get("message") or evidence.get("summary") or fallback


def _user_correction_learnings(events: list[EventRecord]) -> list[CandidateLearningItem]:
    """从用户修正事件中提取学习项。

    用户修正可能反映了稳定的项目偏好或用户习惯模式，
    可用来优化后续的提问策略。
    """
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
    """从交付物评估缺口事件中提取学习项。

    当交付物评估返回 partial 或 fail 状态时，
    说明交付物合约可能需要补充更多必填章节。
    """
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
    """从命令失败事件中提取学习项。

    流程：
    1. 收集所有 command_failed 事件
    2. 如果没有失败事件，直接返回空列表（快速退出）
    3. 查找对应的 command_recovered 事件作为恢复证据
    4. 置信度取决于是否有恢复记录（有恢复 → 0.8，无恢复 → 0.55）

    设计意图：有恢复记录说明已有解决方案，置信度更高；
    无恢复记录则是值得关注但尚未解决的陷阱。
    """
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
    """按 ID 去重学习项列表，保持原始顺序。"""
    seen = set()
    result = []
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        result.append(item)
    return result


def _markdown_report(events: list[EventRecord], items: list[CandidateLearningItem]) -> str:
    """生成学习报告的 Markdown 内容。

    包含事件统计和每条候选学习项的详细信息。
    """
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
