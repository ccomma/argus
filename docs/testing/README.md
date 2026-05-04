# 测试文档

本目录存放 Argus 各阶段测试计划、验收清单和回归记录。

从 Phase 0 起，测试计划负责阶段测试策略，当前执行状态和验收结果写入 `docs/phases/<phase>/ACCEPTANCE.md`。新会话先读 `docs/context/CURRENT_HANDOFF.md` 和当前阶段 `HANDOFF.md`，只有需要验证范围、fixture 意图或补测试时才读取完整测试计划。

每个阶段至少覆盖：

- 单元测试（Unit Tests）
- 固定样本测试（Fixture Tests）
- 集成测试（Integration Tests）
- 验收测试（Acceptance Tests）

创建新测试计划时，从 `docs/templates/TEST_PLAN_TEMPLATE.md` 复制结构，并按阶段命名：

```text
PHASE_1_WORK_CONTRACT_MVP_TEST_PLAN.md
```
