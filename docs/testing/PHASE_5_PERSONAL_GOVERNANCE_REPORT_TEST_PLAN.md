# Phase 5: 个人治理报告 测试计划

> 上下文加载：新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本测试计划。

## 1. 范围

本测试计划覆盖：

- 治理报告生成。
- 低风险维护日志。
- 待处理操作列表。
- 只读行为。
- CLI report 命令。

不覆盖：

- 自动修复。
- 定时调度。
- 外部安装。
- 团队治理。

## 2. 单元测试

- 报告包含去重（dedupe）、过期（stale）、风险（risk）、工作契约（work_contract）和角色（role）发现项。
- 报告包含追问策略改进（question_strategy_improvement）。
- 报告包含交付物契约改进（deliverable_contract_improvement）。
- 报告输出 Markdown、JSON、低风险日志和待处理操作。
- 报告不修改资产清单。

## 3. 集成测试

- CLI `governance report` 写入所有预期输出路径。
- 完整项目验证通过 `./scripts/check.sh` 运行。

## 4. 验收冒烟测试

运行：

```bash
PYTHONPATH=src python3 -m argus.cli assets scan --store /private/tmp/argus-phase5-closeout/.argus --profile local-codex
PYTHONPATH=src python3 -m argus.cli governance report --store /private/tmp/argus-phase5-closeout/.argus
```

预期结果：

- 本地扫描完成，不修改源文件。
- 治理报告产物写入 `.argus/governance/reports/` 目录下。
- JSON 报告包含摘要（summary）、发现项（findings）、低风险维护日志（low-risk maintenance log）和待处理操作（pending actions）。

## 5. 回归风险

- 治理报告变为修改性维护命令。
- 报告遗漏中/高风险操作的确认要求。
- CLI 输出不再是 JSON。
- 空存储导致崩溃。
