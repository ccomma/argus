from __future__ import annotations

"""追加式 JSONL 存储模块。

提供 AppendOnlyJsonlStore 类——一个通用的、类型参数化的追加式
JSONL 文件存储。每条记录以一行 JSON 的形式追加写入，不做修改和删除。
这种设计天然支持不可变事件日志的审计要求。
"""

import json
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar


T = TypeVar("T")


class AppendOnlyJsonlStore(Generic[T]):
    """通用的追加式 JSONL 本地存储。

    特性：
    - 追加写入（append-only）：永不覆盖已有记录，保证审计完整性
    - 幂等去重：基于 identity 函数自动过滤重复记录
    - 类型参数化：通过序列化/反序列化/标识函数适配任意数据类型

    类型参数 T 表示存储的条目类型，如 EventRecord 或 CandidateLearningItem。
    """

    def __init__(
        self,
        path: str | Path,
        *,
        serializer: Callable[[T], dict[str, Any]],
        deserializer: Callable[[dict[str, Any]], T],
        identity: Callable[[T], str],
    ) -> None:
        """初始化 JSONL 存储。

        Args:
            path: JSONL 文件路径
            serializer: 将条目 T 转换为字典的函数
            deserializer: 将字典还原为条目 T 的函数
            identity: 提取条目唯一标识的函数，用于去重
        """
        self.path = Path(path)
        self._serializer = serializer
        self._deserializer = deserializer
        self._identity = identity

    def append(self, item: T) -> bool:
        """追加单条记录。

        流程：
        1. 读取现有记录的全部 ID 集合
        2. 如果新记录的 ID 已存在，跳过并返回 False（幂等）
        3. 否则追加一行 JSON 并返回 True
        """
        existing_ids = {self._identity(existing) for existing in self.list_items()}
        if self._identity(item) in existing_ids:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(self._serializer(item), sort_keys=True) + "\n")
        return True

    def append_many(self, items: list[T]) -> int:
        """批量追加记录。

        流程：
        1. 加载已有 ID 集合
        2. 逐条检查，过滤掉已存在的记录（幂等去重）
        3. 将去重后的新记录一次性批量写入
        4. 返回实际写入的条数
        """
        existing_ids = {self._identity(existing) for existing in self.list_items()}
        pending: list[T] = []
        for item in items:
            item_id = self._identity(item)
            if item_id in existing_ids:
                continue
            existing_ids.add(item_id)
            pending.append(item)
        if not pending:
            return 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            for item in pending:
                handle.write(json.dumps(self._serializer(item), sort_keys=True) + "\n")
        return len(pending)

    def list_items(self) -> list[T]:
        """读取所有已存储的记录。

        逐行解析 JSONL 文件，跳过空行。不存在时返回空列表。
        """
        if not self.path.exists():
            return []
        return [
            self._deserializer(json.loads(line))
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
