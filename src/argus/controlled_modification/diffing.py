"""资产和合约的差异计算引擎，生成 Unified Diff 格式的结构化变更记录。

核心算法：将对象序列化为 JSON 后逐行比较，
生成类似 git diff 的 unified diff 输出，并统计变更字段。
"""

from __future__ import annotations

import json
from typing import Any

from argus.assets.models import CapabilityAsset
from argus.contracts.models import WorkContract

from .models import AssetDiff


def _unified_diff_lines(before: str, after: str, context: int = 3) -> list[str]:
    """生成两段文本的 Unified Diff 格式行列表。

    算法：
    1. 将前后文本按行分割
    2. 双指针扫描，相同时视为上下文行（前缀 " "）
    3. 检测到差异时，收集一组删除行（前缀 "-"）和插入行（前缀 "+"）
    4. 每块变更包裹在 @@ 标记中，指示行号范围
    """
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    result: list[str] = []
    i = j = 0
    while i < len(before_lines) or j < len(after_lines):
        # 相同行：保持为上下文
        if i < len(before_lines) and j < len(after_lines) and before_lines[i] == after_lines[j]:
            result.append(f" {before_lines[i].rstrip()}")
            i += 1
            j += 1
        else:
            # 检测差异块的起始位置
            start_i, start_j = i, j
            # 向前扫描找到差异结束位置
            while i < len(before_lines) and (j >= len(after_lines) or before_lines[i] != after_lines[j]):
                i += 1
            i = start_i
            while j < len(after_lines) and (i >= len(before_lines) or before_lines[i] != after_lines[j]):
                j += 1
            j = start_j
            # 收集删除行和插入行
            chunk_before: list[str] = []
            chunk_after: list[str] = []
            while i < len(before_lines) and (j >= len(after_lines) or before_lines[i] != after_lines[j]):
                chunk_before.append(before_lines[i].rstrip())
                i += 1
            while j < len(after_lines) and (i >= len(before_lines) or before_lines[i] != after_lines[j]):
                chunk_after.append(after_lines[j].rstrip())
                j += 1
            if chunk_before or chunk_after:
                result.append(f"@@ -{start_i + 1},{len(chunk_before)} +{start_j + 1},{len(chunk_after)} @@")
                for line in chunk_before:
                    result.append(f"-{line}")
                for line in chunk_after:
                    result.append(f"+{line}")
    return result


def _changed_fields_dict(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """对比两个字典，返回发生了值变更的字段名列表。"""
    changed: list[str] = []
    all_keys = set(before.keys()) | set(after.keys())
    for key in sorted(all_keys):
        bv = before.get(key)
        av = after.get(key)
        if bv != av:
            changed.append(key)
    return changed


class AssetDiffer:
    """资产和合约的差异计算器，生成结构化的变更记录。

    将前后对象序列化为稳定 JSON，通过逐行 diff 和字段级对比
    生成包含 Unified Diff 文本和字段变更列表的 AssetDiff。
    """

    def diff_capability_asset(
        self,
        before: CapabilityAsset,
        after: CapabilityAsset,
        version_before: str = "",
        version_after: str = "",
    ) -> AssetDiff:
        """计算两个能力资产对象之间的差异。

        1. 将前后对象序列化为排序后的 JSON（保证键序稳定）
        2. 生成 unified diff 行
        3. 统计新增/删除行数和变更字段
        """
        before_text = json.dumps(before.to_dict(), sort_keys=True, indent=2)
        after_text = json.dumps(after.to_dict(), sort_keys=True, indent=2)
        diff_lines = _unified_diff_lines(before_text + "\n", after_text + "\n")
        # 排除 diff 头部的 +++/--- 标记行
        added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))
        changed = _changed_fields_dict(before.to_dict(), after.to_dict())
        return AssetDiff.create(
            subject_type="capability_asset",
            subject_id=before.id,
            version_before=version_before,
            version_after=version_after,
            unified_diff_lines=diff_lines,
            added_lines=added,
            removed_lines=removed,
            changed_fields=changed,
        )

    def diff_work_contract(
        self,
        before: WorkContract,
        after: WorkContract,
        version_before: str = "",
        version_after: str = "",
    ) -> AssetDiff:
        """计算两个工作合约对象之间的差异。

        与 diff_capability_asset 流程相同，但 subject_type 标记为 work_contract。
        """
        before_text = json.dumps(before.to_dict(), sort_keys=True, indent=2)
        after_text = json.dumps(after.to_dict(), sort_keys=True, indent=2)
        diff_lines = _unified_diff_lines(before_text + "\n", after_text + "\n")
        added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))
        changed = _changed_fields_dict(before.to_dict(), after.to_dict())
        return AssetDiff.create(
            subject_type="work_contract",
            subject_id=before.id,
            version_before=version_before,
            version_after=version_after,
            unified_diff_lines=diff_lines,
            added_lines=added,
            removed_lines=removed,
            changed_fields=changed,
        )
