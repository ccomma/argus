# Phase 9: Dashboard, ROI & Maintenance Technical Design

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本技术设计。本文件回答模块、接口、数据和风险边界，不记录每日执行状态。

## 1. Overview

Phase 9 为 Argus 系统新增两大子系统：(1) ROI 分析与仪表盘报告，从合约、学习、角色三个维度量化治理投资回报；(2) 维护健康检查引擎，对资产和能力包进行六类问题扫描。两类报告均输出 Markdown + JSON 双格式文件，供人工审阅和程序消费。

## 2. Architecture

```
analytics/                     maintenance/
  ROICalculator                  MaintenanceEngine
  ├─ ContractROI                 ├─ duplicates / conflicts
  ├─ LearningROI                 ├─ deprecated / archived
  └─ RoleROI                     ├─ unused packs / roles
  DashboardReporter              └─ MaintenanceReport
  └─ DashboardReport           MaintenanceReporter
                              └─ MaintenanceReportPaths

CLI: dashboard → ROI 报告 | maintenance run → 检查输出 | maintenance report → 文件报告
```

数据流：7 个数据源注入 ROICalculator → 三大 ROI 产出 → DashboardReporter 写入 `reports/dashboard.{md,json}`。4 个数据源注入 MaintenanceEngine → MaintenanceReport → MaintenanceReporter 写入 `maintenance/maintenance.{md,json}`。两者互不耦合，但 dashboard 命令可选合并维护摘要。

## 3. Data Model

```text
ContractROI (frozen dataclass)
- total_contracts: int              # 合约总量
- by_status: dict[str, int]         # 按状态分组计数
- avg_completeness: float           # 平均完整性分数
- avg_question_rounds: int          # 平均问询轮次
- total_change_history_entries: int # 变更历史条目总数
- deliverable_pass_rate: float      # 交付物通过率
- deliverable_total: int            # 交付物评估事件总数

LearningROI (frozen dataclass)
- total_learnings: int              # 学习项总量
- by_type: dict[str, int]           # 按类型分组计数
- by_scope: dict[str, int]          # 按作用域分组计数
- avg_confidence: float             # 平均置信度
- pending_count: int                # 待审核学习项数
- promoted_count: int               # 已提升学习项数

RoleROI (frozen dataclass)
- total_roles: int                  # 角色总量
- total_handoffs: int               # 交接记录总数
- roles_used_in_handoffs: list[str] # 参与过交接的活跃角色 ID
- avg_packs_per_role: float         # 每角色平均能力包数

DashboardReport (frozen dataclass)
- markdown_path: Path               # dashboard.md 路径
- json_path: Path                   # dashboard.json 路径
- contract_roi: ContractROI
- learning_roi: LearningROI
- role_roi: RoleROI

MaintenanceReport (frozen dataclass)
- duplicates: list[dict]            # 重复资产组 [{asset_ids, names}]
- conflicts: list[dict]             # 冲突资产组 [{asset_ids, names}]
- deprecated_assets: list[str]      # 废弃资产 ID 列表
- archived_assets: list[str]        # 归档资产 ID 列表
- unused_capability_packs: list[str] # 未绑定合约的能力包 ID
- unused_role_packs: list[str]      # 未使用的角色包 ID
- summary: dict[str, int]           # 各类计数摘要
```

## 4. Interfaces

### CLI

```text
argus dashboard
  --store <.argus>                # 数据目录，默认 .argus
  输出: JSON { markdown_path, json_path, contract_roi, learning_roi, role_roi }

argus maintenance run
  --store <.argus>                # 执行健康检查并输出 JSON 到 stdout

argus maintenance report
  --store <.argus>                # 执行检查并写入 maintenance.md/json 文件
  输出: JSON { markdown_path, json_path }
```

### Python API

```python
from argus.analytics import ROICalculator, DashboardReporter

calculator = ROICalculator(storage, event_ledger, learning_ledger,
                           inventory, pack_store, role_store, handoff_mgr)
report = DashboardReporter(reports_dir).write(calculator, maintenance_summary=None)
# 产出: reports/dashboard.json + reports/dashboard.md

from argus.maintenance import MaintenanceEngine, MaintenanceReporter

engine = MaintenanceEngine(inventory, pack_store, role_store, storage)
report = engine.run()                         # 返回 MaintenanceReport
paths = MaintenanceReporter(dir).write(engine) # 返回 MaintenanceReportPaths
```

### Web API（Phase 10 集成）

Web 工作台通过 `/api/dashboard` 和 `/api/maintenance` 端点消费这些模块，详情见 Phase 10 技术设计。

## 5. Storage

| 输出文件 | 格式 | 位置 |
|---------|------|------|
| `dashboard.json` | JSON | `<store>/reports/dashboard.json` |
| `dashboard.md` | Markdown | `<store>/reports/dashboard.md` |
| `maintenance.json` | JSON | `<store>/maintenance/maintenance.json` |
| `maintenance.md` | Markdown | `<store>/maintenance/maintenance.md` |

两类报告均仅写入 Argus 自有目录，不修改任何上游数据（资产、账本、合约等）。DashboardReporter.write() 可选接收 `maintenance_summary` 字典参数，合并到 dashboard.json 和 dashboard.md 中。

## 6. Governance and Security

- **只读安全**：ROICalculator 和 MaintenanceEngine 均只读上游数据，不产生任何写操作。报告写入仅发生在 `DashboardReporter.write()` 和 `MaintenanceReporter.write()` 调用时，且写入目标为独立的 `reports/` 和 `maintenance/` 子目录。
- **风险等级**：维护报告中 `unused_role_packs` 当前将所有角色包列为待审查项（非自动清理），避免误删。废弃/归档资产仅做标记输出，不触发任何自动操作。
- **数据快照一致性**：MaintenanceEngine.run() 在单次调用中完成所有检测，保证同一快照下的数据一致性（不会出现中途数据变更导致前后不一致）。

## 7. Failure Modes

- **空数据集**：合约/学习/角色数为 0 时，avg_completeness/avg_confidence 等均值返回 0.0（除零保护），deliverable_pass_rate 返回 0.0。
- **存储目录不存在**：DashboardReporter 和 MaintenanceReporter 自动创建目标目录（mkdir parents=True），不会因目录缺失而失败。
- **旧合约模型兼容**：contract_roi() 的 avg_question_rounds 计算兼容新旧合约模型，优先使用 `answers` 属性，缺则回退到 `question_history`。
- **partial 数据**：find_potential_duplicates / find_potential_conflicts 来自 `argus.assets.analysis`，若返回空列表则报告相应章节为空。

## 8. Test Strategy

- **Unit Tests**：ROICalculator 三个 getter 方法的独立单测（mock 数据源注入各边界情况：空列表、单条目、多种状态混合）。MaintenanceEngine.run() 的六类检测分别单测。
- **Fixture Tests**：使用固定 fixtures 目录的完整数据集，验证报告 JSON/MD 输出的结构和关键数值。
- **Integration Tests**：通过 CLI 子命令调用 `argus dashboard` 和 `argus maintenance run/report`，验证从数据源到输出的完整链路。
- **Acceptance Tests**：在真实 `.argus` store 上运行命令，确认双格式文件正确生成且内容合理。

## 9. Compatibility

- **不修改任何上游数据**：不写合约、不写资产、不写账本、不写能力包。
- **与 Phase 5 治理报告独立**：两种报告存储在不同目录（`reports/` vs `governance/reports/`），互不冲突。
- **Phase 10 Web 集成兼容**：WebServer 直接复用 ROICalculator 和 MaintenanceEngine 实例，报告生成逻辑保持 CLi 与 Web 一致。
- **向后兼容**：contract_roi() 已处理无 `answers` 属性旧合约的情况。

## 10. Open Questions

- 当前 maintenance 示例报告引用 `d['reason']` 字段渲染 Markdown，但 find_potential_duplicates/conflicts 返回的结构为 `{asset_ids, names}` 不含 `reason`，此处 Markdown 渲染需确认是否要更改为展示 names 列表。
- Dashboard JSON 中 `maintenance` 合并字段是否应包含完整的 MaintenanceReport.to_dict() 还是仅 summary 子集。
- 是否需要在未来版本增加 Dashboard 的趋势追踪能力（保留历史报告快照并按时间索引）。
