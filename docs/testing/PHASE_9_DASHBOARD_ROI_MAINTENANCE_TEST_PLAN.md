# Phase 9: 仪表盘 ROI 与维护 Test Plan

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本测试计划。当前验收状态写入阶段目录的 `ACCEPTANCE.md`。

## 1. Scope

本测试计划覆盖：

- ROICalculator 三维度指标：ContractROI、LearningROI、RoleROI
- ContractROI 计算：合约总量、状态分布、平均完整性、问询轮次、变更条目数、交付物通过率
- LearningROI 计算：学习项总量、类型/作用域分布、平均置信度、pending/promoted 统计
- RoleROI 计算：角色总量、交接次数、活跃角色列表、每角色平均能力包数
- DashboardReporter 双格式（Markdown + JSON）仪表盘报告
- MaintenanceEngine 六类健康检查：重复资产、冲突资产、废弃/归档资产、未使用能力包/角色包
- MaintenanceReporter 双格式维护报告
- CLI `dashboard`、`maintenance run`、`maintenance report` 命令

不覆盖：

- 趋势计算和时序对比
- 告警阈值触发
- 自动清理废弃/归档资产

## 2. Fixtures

固定样例：

- 空系统（无合约/无学习项/无角色/无交接）：用于空库边界测试
- 单个 WorkContract（intent="test"）：用于 contract_roi 基本指标验证
- 多交接记录链（a->b, b->c）：用于 role_roi 交接活跃度计算
- 重复资产对（同名同类型）：用于 maintenance 重复检测
- deprecated 状态资产对：用于 maintenance 废弃资产检测

## 3. Unit Tests

- `test_contract_roi_empty_system`：空系统 total_contracts=0, avg_completeness=0.0
- `test_contract_roi_with_contracts`：单合约 total_contracts=1, by_status 含 "clarifying"
- `test_learning_roi_empty_system`：空系统 total_learnings=0
- `test_role_roi_with_handoffs`：两个交接记录 total_handoffs=2
- `test_maintenance_empty_system`：空系统 summary["total_assets"]=0, duplicates=0
- `test_maintenance_detects_duplicates`：两个同名同类型资产 -> duplicates >= 1
- `test_maintenance_detects_deprecated_assets`：两个 deprecated 资产 -> summary["deprecated"]=2

## 4. Fixture Tests

- `test_dashboard_reporter_writes_markdown_and_json`：DashboardReporter 写出包含 "Argus Dashboard" 的 Markdown，JSON 含 contract_roi/learning_roi/role_roi 三大维度
- `test_maintenance_reporter_writes_files`：MaintenanceReporter 写出包含 "Maintenance Report" 的 Markdown 和 JSON，summary 字段完整

## 5. Integration Tests

- `test_dashboard_cli_writes_report`：`argus.cli dashboard --store` 输出含 markdown_path 和 contract_roi 的 JSON
- `test_maintenance_run_cli`：`argus.cli maintenance run --store` 输出含 summary 和 total_assets 的 JSON
- `test_maintenance_report_cli`：`argus.cli maintenance report --store` 输出含 markdown_path 的 JSON

## 6. Acceptance Tests

- 仪表盘对空系统不崩溃，返回全部零值的有效 ROI 指标
- 维护引擎对空系统返回空问题清单，summary 所有计数为 0
- 三类 CLI 命令（dashboard/maintenance run/maintenance report）均输出合法 JSON

## 7. Regression Risks

- ROI 计算中 division by zero：空系统测试覆盖所有分母为零的边界
- 维护 Markdown 渲染引用不存在的字段（如 duplicates 的 reason）：已通过 fixture 测试验证渲染输出
- maintenance run 和 maintenance report CLI 输出格式不一致：两者均通过 JSON 解析验证
- 仪表盘未合并维护摘要数据（可选 maintenance_summary 参数缺失时）不崩溃：dashboard_cli 测试覆盖

## 8. Test Commands

```bash
PYTHONPATH=src python -m pytest tests/test_phase9_dashboard_maintenance.py -v
PYTHONPATH=src python -m unittest tests.test_phase9_dashboard_maintenance.Phase9DashboardTest tests.test_phase9_dashboard_maintenance.Phase9MaintenanceTest tests.test_phase9_dashboard_maintenance.Phase9CLITest
```
