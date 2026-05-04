# Phase 7: 受控修改 Test Plan

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本测试计划。当前验收状态写入阶段目录的 `ACCEPTANCE.md`。

## 1. Scope

本测试计划覆盖：

- 快照（SnapshotManager）的捕获、持久化和按 ID 加载
- 快照 ID 的确定性（相同内容 -> 相同 ID，通过 SHA1 内容寻址）
- 差异计算（AssetDiffer）的资产级和合约级变更检测
- 审计账本（AuditLedger）的追加写入、列表和按 ID 去重
- ModificationApplication 的 apply/preview 操作
- 回滚（RollbackManager）的资产恢复和审计记录生成
- ModificationReporter 双格式（Markdown + JSON）报告
- CLI `modify apply` 和 `modify rollback` 命令

不覆盖：

- 并发修改冲突解决
- 跨快照差异合并
- 外部触发器调度

## 2. Fixtures

固定样例：

- 单个 CapabilityAsset（name="test", type="skill"）：用于快照捕获、差异检测、修改应用和回滚测试
- WorkContract（通过 WorkContractBuilder 构建）：用于合约级修改和回滚测试

## 3. Unit Tests

- `test_snapshot_creates_deterministic_id`：相同内容的 ModificationSnapshot.capture 产生相同 ID
- `test_asset_diff_detects_status_change`：AssetDiffer.diff_capability_asset 正确检测 status 字段变更
- `test_asset_diff_detects_no_change`：无变更时 changed_fields 为空，added_lines/removed_lines 均为 0
- `test_contract_diff_detects_field_update`：AssetDiffer.diff_work_contract 正确检测 goal 字段变更
- `test_audit_ledger_append_and_list`：AuditLedger 追加两条记录后可列出全部
- `test_audit_ledger_deduplicates_by_id`：重复 ID 的 ModificationAuditRecord.append 返回 False

## 4. Fixture Tests

- `test_snapshot_manager_captures_and_loads_asset`：SnapshotManager 捕获资产写入 JSON 文件，load 可反序列化恢复 content_json
- `test_snapshot_manager_captures_and_loads_contract`：SnapshotManager 对 WorkContract 的捕获和加载

## 5. Integration Tests

- `test_apply_asset_modification_produces_snapshot_diff_and_audit`：ModificationApplication.apply_asset_modification 产生 snapshot_id/diff_id/audit_record_id，资产状态变更落地，snapshot JSON 和 audit JSONL 文件均存在
- `test_preview_asset_modification_does_not_modify_disk`：preview 操作返回包含 changed_fields 的 diff，磁盘资产清单不变化
- `test_apply_contract_modification_produces_snapshot_diff_and_audit`：合约修改后版本号递增、字段更新、change_history 追加，审计记录写入
- `test_rollback_restores_previous_asset_version`：回滚将资产从 deprecated 恢复到 active，产生 rollback 审计记录且含 rollback_instructions
- `test_rollback_fails_for_nonexistent_audit_record`：不存在的审计 ID 回滚返回 outcome="failed" 且 warnings 非空
- `test_modification_reporter_writes_markdown_and_json`：ModificationReporter 写出包含 "Controlled Modification Report" 和 "modify" 的 Markdown，JSON 含正确的 summary 统计
- `test_cli_modify_apply_and_rollback_commands`：CLI apply 输出 outcome="applied" 和 audit_record_id；CLI rollback 输出 outcome="applied"

## 6. Acceptance Tests

- 完整"快照 -> 差异 -> 审计 -> 报告"管线在资产和合约两种 subject_type 下均通过
- 回滚操作自身也生成审计记录，保证闭环溯源

## 7. Regression Risks

- 回滚后资产清单未正确恢复：rollback 测试验证前后 status 值一致
- 预览操作产生副作用：preview 测试验证磁盘状态不变化
- 审计账本内容被覆盖：去重测试验证 append 拒绝重复 ID

## 8. Test Commands

```bash
PYTHONPATH=src python -m pytest tests/test_phase7_controlled_modification.py -v
PYTHONPATH=src python -m unittest tests.test_phase7_controlled_modification.Phase7ControlledModificationTest
```
