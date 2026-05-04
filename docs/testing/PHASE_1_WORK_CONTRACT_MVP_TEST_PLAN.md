# Phase 1: 追问模式工作契约 MVP 测试计划

> 上下文加载：新会话默认先读 `docs/context/CURRENT_HANDOFF.md` 和阶段 `HANDOFF.md`。本文件仅回答 Phase 1 的测试策略；实际验收证据记录在阶段 `ACCEPTANCE.md`。

## 1. 范围

本测试计划覆盖：

- 模糊意图到追问问题的转换。
- 用户回答到工作契约的生成。
- 完整度评分。
- 问题预算与退出条件。
- 工作契约版本与变更历史。
- 交付物契约。
- 交付物评估器。
- 本地 `.argus/` 存储。

不覆盖：

- 外部 skill、MCP、plugin 安装。
- 能力清单（capability inventory）。
- 团队权限与共享策略。
- 仪表盘（dashboard）。
- 跨 agent 适配器。

## 2. 固定样例

固定样例：

- `ambiguous_product_idea`：用户仅表达一个模糊产品想法。
- `argus_phase_plan_request`：用户要求把 Argus 从设计推进到开发阶段。
- `skipped_answers`：用户跳过部分关键问题，用于验证完整度评分不足。
- `prd_missing_acceptance`：PRD 缺少验收标准，用于验证评估器缺失项。
- `contract_change_scope`：用户修改目标或约束，用于验证版本和变更历史。

## 3. 单元测试

- `WorkContract`：必填字段缺失时校验失败。
- `QuestionStrategy`：不同模式对应不同问题预算。
- `CompletenessScorer`：缺少目标、输出或验收标准时整体评分降低。
- `ContractSession`：状态按 `draft -> clarifying -> ready` 流转。
- `DeliverableEvaluator`：能识别必需章节的缺失。
- `ContractStorage`：能写入、读取、追加版本和证据。

## 4. 样例测试

- `ambiguous_product_idea`：稳定生成关键追问，不直接进入执行。
- `argus_phase_plan_request`：生成包含目标、约束、阶段和验收标准的工作契约。
- `skipped_answers`：输出 `partial` 或继续追问建议。
- `prd_missing_acceptance`：评估器输出缺失验收标准。
- `contract_change_scope`：生成新版本并记录变更摘要。

## 5. 集成测试

- 从意图出发，生成追问、接收回答、生成工作契约、计算评分、生成 PRD 草案、运行评估器。
- 从已有契约读取并重新生成交付物评估。
- 修改契约后，验证旧版本仍可读取，新版本有变更历史。

## 6. 验收测试

- 用户能明显感受到"不用知道流程，Argus 会问到足够清楚为止"：用真实 Argus Phase 1 场景手动确认。
- 工作契约字段完整：检查契约是否包含目标、背景、输入、输出、约束、风险、确认点、验收标准和完成定义。
- 完整度评分可解释：检查评分是否包含缺失项和理由说明。
- 评估器有实际约束力：检查它能指出交付物缺失项。
- 没有高风险持久变更：检查运行后仅写入 `.argus/` 或测试临时目录。

## 7. 回归风险

- 追问退化成泛泛聊天：用固定样例验证问题必须映射到必需事实。
- 评分虚高：用缺失字段样例验证分数下降。
- 评估器只做总结不做验收：用缺失章节样例验证 fail / partial。
- 契约 schema 变化破坏旧文件：用旧 schema 样例验证兼容或明确报错。
- 存储误写外部目录：用临时目录和路径断言验证。

## 8. 测试命令

当前 Phase 1 使用 Python 标准库 `unittest`，不需要安装 pytest。

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall -q src tests
git diff --check
```

CLI 冒烟测试：

```bash
PYTHONPATH=src python3 -m argus.cli contract --help
```
