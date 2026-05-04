# Phase 7: Controlled Modification & Rollback Technical Design

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本技术设计。本文件回答模块、接口、数据和风险边界，不记录每日执行状态。

## 1. Overview

Phase 7 实现受控修改与回滚子系统，为所有资产和合约变更建立「快照-差异-审计-回滚」四步安全管线。每次变更前自动捕获完整状态快照，变更后生成结构化 unified diff，所有操作记录写入不可变审计账本，支持事后按审计记录回滚到快照状态。回滚本身也产生审计记录，形成闭环溯源。

## 2. Architecture

四步安全管线数据流：

```
CLI: modify preview ───→ [仅预览差异，无副作用]
CLI: modify apply ────→ ┌──────────────────────────────────────────────┐
                        │ 1. SnapshotManager.capture()                 │
                        │    └─→ .argus/modifications/snapshots/       │
                        │ 2. 应用变更 (inventory.write / save_contract) │
                        │ 3. AssetDiffer.diff_*()                      │
                        │    └─→ AssetDiff (unified diff + 字段变更)    │
                        │ 4. AuditLedger.append()                      │
                        │    └─→ .argus/modifications/audit.jsonl      │
                        └──────────────────────────────────────────────┘
CLI: modify rollback ──→ RollbackManager.rollback(audit_record, reason)
                           │
                           ├─→ SnapshotManager.load(snapshot_id)
                           ├─→ 恢复 inventory / contract_storage
                           └─→ AuditLedger.append(rollback_audit)

CLI: modify audit-log ─→ AuditLedger.list_records()
CLI: modify report ────→ ModificationReporter.write()
```

核心模块：
- `src/argus/controlled_modification/models.py` — 5 个 frozen dataclass 模型
- `src/argus/controlled_modification/snapshot.py` — `SnapshotManager`
- `src/argus/controlled_modification/diffing.py` — `AssetDiffer`，unified diff 引擎
- `src/argus/controlled_modification/audit.py` — `AuditLedger`，追加写入 JSONL
- `src/argus/controlled_modification/rollback.py` — `RollbackManager`
- `src/argus/controlled_modification/reporting.py` — `ModificationReporter`
- `src/argus/application/modification.py` — `ModificationApplication`，编排门面

## 3. Data Model

所有模型使用 frozen dataclass，ID 通过 SHA1(payload) 前 16 位生成，确保内容寻址。

```text
ModificationSnapshot (frozen dataclass)
  - id: str                     # snap-<sha1_16>，内容寻址
  - subject_type: str           # capability_asset / work_contract
  - subject_id: str             # 目标资产或合约的 ID
  - captured_at: int            # Unix 时间戳（秒）
  - content_json: str           # 变更前状态的完整 JSON
  - version_before: str = ""    # 快照前版本号
  - triggered_by: str = ""      # 触发者标识（用户/系统组件名）
  - trigger_reason: str = ""    # 触发原因描述
  工厂方法: ModificationSnapshot.capture(*, subject_type, subject_id, content, version_before, triggered_by, trigger_reason)

AssetDiff (frozen dataclass)
  - id: str                     # diff-<sha1_16>
  - subject_type: str           # capability_asset / work_contract
  - subject_id: str             # 目标 ID
  - version_before: str         # 变更前版本
  - version_after: str          # 变更后版本
  - unified_diff_lines: list[str]  # 类似 git diff 的行列表（含上下文）
  - added_lines: int            # 新增行数
  - removed_lines: int          # 删除行数
  - changed_fields: list[str]   # 发生变更的字段名列表
  - created_at: int             # Unix 时间戳
  工厂方法: AssetDiff.create(*, subject_type, subject_id, version_before, version_after, unified_diff_lines, added_lines, removed_lines, changed_fields)

ModificationAuditRecord (frozen dataclass)
  - id: str                     # audit-<sha1_16>
  - timestamp: int              # Unix 时间戳
  - triggered_by: str           # 触发者
  - trigger_reason: str         # 触发原因
  - subject_type: str           # capability_asset / work_contract
  - subject_id: str             # 目标 ID
  - action: str                 # modify / rollback
  - snapshot_id: str            # 关联快照 ID
  - diff_id: str = ""           # 关联差异 ID（rollback 时可为空）
  - rollback_instructions: str = ""  # 人工回滚 CLI 命令
  - outcome: str = "applied"    # applied / failed
  工厂方法: ModificationAuditRecord.create(*, triggered_by, trigger_reason, subject_type, subject_id, action, snapshot_id, diff_id, rollback_instructions, outcome)

ModificationResult (frozen dataclass)
  - snapshot_id: str
  - diff_id: str = ""
  - audit_record_id: str = ""
  - outcome: str = "applied"
  - warnings: list[str] = []    # 操作警告信息

ModificationReport (frozen dataclass)
  - markdown_path: Path
  - json_path: Path
```

## 4. Interfaces

### 4.1 Python API

**SnapshotManager** (`src/argus/controlled_modification/snapshot.py`):
```python
class SnapshotManager:
    def __init__(self, snapshots_dir: Path) -> None
    def capture(self, *, subject_type, subject_id, content, version_before, triggered_by, trigger_reason) -> ModificationSnapshot
    def load(self, snapshot_id: str) -> ModificationSnapshot | None
```

**AssetDiffer** (`src/argus/controlled_modification/diffing.py`):
```python
class AssetDiffer:
    def diff_capability_asset(self, before: CapabilityAsset, after: CapabilityAsset, ...) -> AssetDiff
    def diff_work_contract(self, before: WorkContract, after: WorkContract, ...) -> AssetDiff
```

**AuditLedger** (`src/argus/controlled_modification/audit.py`):
```python
class AuditLedger:
    def __init__(self, path: Path) -> None
    def append(self, record: ModificationAuditRecord) -> bool
    def list_records(self) -> list[ModificationAuditRecord]
    def get_by_id(self, audit_id: str) -> ModificationAuditRecord | None
```

**RollbackManager** (`src/argus/controlled_modification/rollback.py`):
```python
class RollbackManager:
    def __init__(self, snapshot_manager, inventory, contract_storage, audit_ledger) -> None
    def rollback(self, audit_record: ModificationAuditRecord, reason: str) -> ModificationResult
```

**ModificationApplication** (`src/argus/application/modification.py`):
```python
class ModificationApplication:
    def preview_asset_modification(self, asset_id, triggered_by, trigger_reason, new_status="", new_metadata=None) -> AssetDiff | None
    def apply_asset_modification(self, asset_id, triggered_by, trigger_reason, new_status="", new_metadata=None) -> ModificationResult | None
    def preview_contract_modification(self, contract_id, triggered_by, trigger_reason, field_updates=None) -> AssetDiff | None
    def apply_contract_modification(self, contract_id, triggered_by, trigger_reason, field_updates=None) -> ModificationResult | None
    def rollback(self, audit_record_id: str, reason: str) -> ModificationResult
    def list_audit_log(self) -> list[ModificationAuditRecord]
    def write_report(self) -> ModificationReport
```

### 4.2 CLI

注册在 `modify` 子命令组（`src/argus/cli/modification.py`）：

```bash
# 资产修改预览（仅 diff，不应用）
argus modify preview --asset-id <id> --triggered-by <who> --trigger-reason <why> --new-status <s>

# 资产修改应用（快照-变更-差异-审计四步）
argus modify apply --asset-id <id> --triggered-by <who> --trigger-reason <why> --new-status <s>

# 合约修改预览
argus modify contract-preview --contract-id <id> --triggered-by <who> --trigger-reason <why> --field key=val

# 合约修改应用（含版本号递增和 change_history 追加）
argus modify contract-apply --contract-id <id> --triggered-by <who> --trigger-reason <why> --field key=val

# 回滚（按审计记录 ID 恢复到快照状态）
argus modify rollback --audit-id <id> --reason <why>

# 查看审计日志
argus modify audit-log

# 生成修改报告
argus modify report
```

## 5. Storage

- 快照目录：`.argus/modifications/snapshots/{snapshot_id}.json` — 每个快照一个 JSON 文件
- 审计日志：`.argus/modifications/audit.jsonl` — AppendOnlyJsonlStore 追加写入，不可删除
- 修改报告：`.argus/modifications/reports/` — `modifications-report.md` + `modifications-report.json`
- 所有依赖路径通过 `ArgusPaths.from_store()` 解析，目录在首次写入时自动创建（`mkdir(parents=True, exist_ok=True)`）
- 无迁移需求

## 6. Governance and Security

- **不可变审计**：`AuditLedger` 底层为 `AppendOnlyJsonlStore`，仅追加写入，无删除/修改接口
- **内容寻址 ID**：所有快照/差异/审计记录的 ID 基于内容 SHA1 哈希生成，防止 ID 篡改和冲突
- **回滚审计闭环**：回滚操作生成独立的 `ModificationAuditRecord`（action="rollback"），引用原始快照，保证完整溯源
- **预览隔离**：`preview_*` 方法仅构造内存副本并计算差异，不持久化任何状态
- **合约版本递增**：合约修改时 `version += 1`，且 `change_history` 追加变更元数据（version, reason, triggered_by, snapshot_id）
- **资产恢复保护**：回滚时检查目标资产是否存在于当前清单，不存在则返回 outcome="failed"

## 7. Failure Modes

- 目标资产/合约不存在：`preview_*` 和 `apply_*` 返回 None，CLI 输出 `{"error": "Asset/Contract <id> not found."}` 并返回退出码 1
- 对应快照不存在于磁盘：`RollbackManager.rollback()` 返回 `outcome="failed"`，携带 `warnings=["Snapshot <id> not found."]`
- 审计记录未找到：回滚时 `get_by_id()` 返回 None，返回 `outcome="failed"`
- 受限 subject_type：不支持的回滚类型（非 capability_asset 或 work_contract）返回失败
- 磁盘写入权限不足：`SnapshotManager.capture()` 或 `AuditLedger.append()` 在文件系统写入失败时抛出 OSError，由上层捕获
- 合约序列化不一致：`from_dict` 通过 `type(contract).from_dict` 保持多态一致性，但如果原始类型丢失，反序列化将失败

## 8. Test Strategy

- Unit Tests：
  - `_make_id` 内容寻址的确定性（相同 payload 产生相同 ID）
  - 所有模型 `to_dict()` / `from_dict()` 序列化往返
  - `_unified_diff_lines` 对相同文本、新增、删除、修改四种场景的正确性
  - `_changed_fields_dict` 字段变更检测（新增字段、删除字段、值变更）
- Fixture Tests：用预构造的 `CapabilityAsset` / `WorkContract` 实例验证 `AssetDiffer` 的输出
- Integration Tests：
  - 完整 modify 管线：`preview → apply → audit_log → rollback → audit_log` 闭环
  - 回滚后状态验证：资产/合约恢复后的字段值与快照一致
  - `AuditLedger` 追加顺序与 `list_records` 返回顺序一致
- Acceptance Tests：
  - 对不存在的 asset_id 执行 preview/apply 返回 None
  - 回滚后审计日志中出现 action="rollback" 记录
  - `modify report` 输出文件包含正确的 summary 和 audit 条目

## 9. Compatibility

- `CapabilityInventory.write()` 和 `ContractStorage.save_contract()` 接口被直接调用，需确保这些方法的行为不变
- `AppendOnlyJsonlStore` 接口需保持稳定（`append`、`list_items`）
- CLI 命令通过 `ModificationApplication` 封装，上层 handler 不变时向后兼容
- 无破坏性变更——所有写入仅发生在 `.argus/modifications/` 子目录

## 10. Open Questions

- 是否需要实现 24 小时冷静期策略（当前仅文档中提及，代码中未强制执行）？
- 是否需要保留多版本快照链（当前每次修改覆盖清单，但每次产生新快照文件）？
- `MERGE` 和 `IGNORE` 决策枚举已在 Phase 6 定义但未在 Phase 7 的修改流程中使用——将来是否需要支持合并操作？
