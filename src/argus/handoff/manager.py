"""交接管理器：负责交接记录的创建、持久化和查询。

HandoffManager 以文件系统为存储后端，每条交接记录保存为一个 JSON 文件。
通过名称约定（{handoff_id}.json）实现按 ID 快速查找。
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import HandoffRecord


class HandoffManager:
    """角色交接管理器。

    职责：管理 Agent 角色间上下文交接的生命周期——
    创建交接记录、按 ID 加载、按合同/角色筛选列表。
    存储策略：每条记录一个 JSON 文件，目录扁平化，文件名 = record.id。
    """
    def __init__(self, handoffs_dir: Path) -> None:
        self.handoffs_dir = handoffs_dir

    def create(
        self,
        *,
        from_role_id: str,
        to_role_id: str,
        contract_id: str = "",
        context: dict | None = None,
        handoff_reason: str = "",
    ) -> HandoffRecord:
        """创建并持久化一条交接记录。

        1. 通过 HandoffRecord.create 构造记录对象（含内容哈希 ID）
        2. 确保存储目录存在
        3. 序列化为 JSON 写入磁盘
        4. 返回创建的记录对象
        """
        record = HandoffRecord.create(
            from_role_id=from_role_id,
            to_role_id=to_role_id,
            contract_id=contract_id,
            context=context,
            handoff_reason=handoff_reason,
        )
        self.handoffs_dir.mkdir(parents=True, exist_ok=True)
        (self.handoffs_dir / f"{record.id}.json").write_text(
            json.dumps(record.to_dict(), sort_keys=True, indent=2), encoding="utf-8"
        )
        return record

    def load(self, handoff_id: str) -> HandoffRecord | None:
        """按 ID 加载单条交接记录，不存在时返回 None。"""
        path = self.handoffs_dir / f"{handoff_id}.json"
        if not path.exists():
            return None
        return HandoffRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_by_contract(self, contract_id: str) -> list[HandoffRecord]:
        """列出指定合同下的所有交接记录。"""
        return self._list_filtered(lambda r: r.contract_id == contract_id)

    def list_by_role(self, role_id: str) -> list[HandoffRecord]:
        """列出涉及指定角色的所有交接记录（无论作为来源还是目标）。"""
        return self._list_filtered(lambda r: r.from_role_id == role_id or r.to_role_id == role_id)

    def list_all(self) -> list[HandoffRecord]:
        """列出所有交接记录。"""
        return self._list_filtered(lambda _: True)

    def _list_filtered(self, predicate) -> list[HandoffRecord]:
        """通用筛选方法：遍历目录下所有 JSON 文件，按谓词过滤。

        1. 目录不存在时直接返回空列表
        2. 按文件名排序遍历所有 .json 文件
        3. 每个文件反序列化后交由 predicate 判断
        4. 命中则加入结果列表
        """
        if not self.handoffs_dir.exists():
            return []
        records: list[HandoffRecord] = []
        for path in sorted(self.handoffs_dir.glob("*.json")):
            record = HandoffRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if predicate(record):
                records.append(record)
        return records
