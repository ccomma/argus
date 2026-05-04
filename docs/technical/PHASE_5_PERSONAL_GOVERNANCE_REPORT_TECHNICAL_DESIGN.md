# Phase 5: 个人治理报告 技术设计

> 上下文加载：新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本技术设计。

## 1. 概述

Phase 5 增加只读的治理报告功能。它聚合本地 Argus 存储数据，并将报告产物写入 `.argus/governance/reports/` 目录。

## 2. 组件

- `GovernanceReporter`：构建并写入报告产物。
- `GovernanceFinding`：标准化的治理发现项。
- `PendingAction`：建议的后续操作，附有风险等级和确认要求。
- `GovernanceApplication`：应用层封装。
- CLI：`argus governance report`。

## 3. 输入

- `ContractStorage.list_contracts()`
- `ContractStorage.list_evaluations(contract_id)`
- `LearningLedger.list_items()`
- `CapabilityInventory.list_assets()`
- `CapabilityPackStore.list_latest()`
- `RolePackStore.list_latest()`

## 4. 输出

输出位于 `.argus/governance/reports/` 目录下：

- `governance-report.md`
- `governance-report.json`
- `low-risk-maintenance-log.json`
- `pending-actions.json`

## 5. 发现分类

- `dedupe`：重复的资产分组和重复的候选学习信号。
- `stale`：非活跃状态的能力资产。
- `risk`：高风险资产和高/严重级别能力包。
- `work_contract`：不完整的契约和失败的交付物评估。
- `role`：角色包质量或风险发现。

## 6. 待处理操作

待处理操作仅为报告层面的建议：

- `question_strategy_improvement`
- `deliverable_contract_improvement`
- `<category>_review`

中高级风险操作需要用户确认。低风险操作记录为仅报告的维护事项。

## 7. 安全性

治理报告不得修改以下内容：

- 源能力资产
- skill/plugin/MCP/rule/script/memory 文件
- 角色包清单
- 能力包清单
- 契约（除非未来显式命令要求修改）

Phase 5 仅写入 Argus 自有的报告文件。

## 8. 非目标

- 定时调度器
- 自动修复
- 治理审批流程
- 安装/更新/归档/删除/禁用操作
- 团队治理
