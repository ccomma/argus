from __future__ import annotations

import json
from typing import Any

from argus.assets.models import CapabilityAsset
from argus.contracts.models import WorkContract

from .models import AssetDiff


def _unified_diff_lines(before: str, after: str, context: int = 3) -> list[str]:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    result: list[str] = []
    i = j = 0
    while i < len(before_lines) or j < len(after_lines):
        if i < len(before_lines) and j < len(after_lines) and before_lines[i] == after_lines[j]:
            result.append(f" {before_lines[i].rstrip()}")
            i += 1
            j += 1
        else:
            start_i, start_j = i, j
            while i < len(before_lines) and (j >= len(after_lines) or before_lines[i] != after_lines[j]):
                i += 1
            i = start_i
            while j < len(after_lines) and (i >= len(before_lines) or before_lines[i] != after_lines[j]):
                j += 1
            j = start_j
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
    changed: list[str] = []
    all_keys = set(before.keys()) | set(after.keys())
    for key in sorted(all_keys):
        bv = before.get(key)
        av = after.get(key)
        if bv != av:
            changed.append(key)
    return changed


class AssetDiffer:
    def diff_capability_asset(
        self,
        before: CapabilityAsset,
        after: CapabilityAsset,
        version_before: str = "",
        version_after: str = "",
    ) -> AssetDiff:
        before_text = json.dumps(before.to_dict(), sort_keys=True, indent=2)
        after_text = json.dumps(after.to_dict(), sort_keys=True, indent=2)
        diff_lines = _unified_diff_lines(before_text + "\n", after_text + "\n")
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
