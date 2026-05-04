from __future__ import annotations

"""事件摄取模块。

提供将外部数据源转换为事件账本记录的能力。
支持两种数据源：
1. 合同证据（ContractEvidenceIngestor）：从 ContractStorage 读取证据
2. 转录数据（TranscriptIngestor）：从外部 JSONL 转录文件导入
"""

import json
from pathlib import Path

from argus.ledger.models import EventRecord
from argus.ledger.store import EventLedger
from argus.storage import ContractStorage


class ContractEvidenceIngestor:
    """合同证据摄取器。

    将合同存储中的证据链（evidence.jsonl）批量导入事件账本，
    使分散的合同证据集中到统一的账本中进行学习提取和分析。
    """

    def __init__(self, storage: ContractStorage, ledger: EventLedger) -> None:
        """初始化摄取器。

        Args:
            storage: 合同存储实例，用于读取证据
            ledger: 目标事件账本
        """
        self.storage = storage
        self.ledger = ledger

    def ingest(self, contract_id: str) -> int:
        """将指定合同的全部证据导入事件账本。

        流程：
        1. 加载合同对象（获取合同 ID 和版本号）
        2. 逐条读取合同的证据链条目
        3. 将每条证据转换为 EventRecord
        4. 批量写入事件账本（自动去重）
        5. 返回实际写入的条数
        """
        contract = self.storage.load_contract(contract_id)
        events = [
            EventRecord.create(
                source="contract_evidence",
                agent="argus",
                contract_id=contract.id,
                contract_version=contract.version,
                event_type=entry.get("event_type", "unknown"),
                evidence=entry,
                execution_evidence=_execution_evidence(entry),
            )
            for entry in self.storage.list_evidence(contract_id)
        ]
        return self.ledger.append_many(events)


class TranscriptIngestor:
    """转录数据摄取器。

    从外部的 JSONL 转录文件（如 Codex 会话记录）导入事件到账本。
    每一行是一个 JSON 对象，包含 agent、session、timestamp 等字段。
    """

    def __init__(self, ledger: EventLedger) -> None:
        """初始化转录摄取器。

        Args:
            ledger: 目标事件账本
        """
        self.ledger = ledger

    def ingest(self, path: str | Path) -> int:
        """从 JSONL 转录文件批量导入事件。

        流程：
        1. 逐行读取 JSONL 文件
        2. 跳过空行
        3. 解析 JSON 行，对格式错误抛出明确异常（附带行号）
        4. 转换为 EventRecord 并批量写入账本

        行号信息的附带对于调试转录格式问题非常重要。
        """
        events = []
        for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid transcript JSONL at line {line_number}: {exc.msg}") from exc
            events.append(
                EventRecord.create(
                    source="codex_transcript",
                    agent=raw.get("agent", "codex"),
                    session=raw.get("session", ""),
                    timestamp=raw.get("timestamp", ""),
                    event_type=raw.get("event_type", "unknown"),
                    evidence=raw.get("evidence", raw),
                )
            )
        return self.ledger.append_many(events)


def _execution_evidence(entry: dict) -> dict:
    """从证据条目中提取执行相关的字段子集。

    只保留 deliverable_type、status、path、missing_items 等
    与执行结果直接相关的字段，避免噪音信息进入执行证据。
    """
    return {
        key: entry[key]
        for key in ("deliverable_type", "status", "path", "missing_items")
        if key in entry
    }
