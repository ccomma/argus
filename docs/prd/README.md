# PRD 文档

本目录存放 Argus 各阶段 PRD。

PRD 负责说明"为什么做、给谁用、成功是什么、不做什么"。技术实现细节应放在 `docs/technical/`，测试细节应放在 `docs/testing/`。

从 Phase 0 起，PRD 就不是新会话的默认入口。新会话先读 `docs/context/CURRENT_HANDOFF.md` 和当前阶段 `HANDOFF.md`，只有需要产品需求、用户价值或成功标准细节时才读取当前阶段 PRD。

创建新 PRD 时，从 `docs/templates/PRD_TEMPLATE.md` 复制结构，并按阶段命名：

```text
PHASE_1_WORK_CONTRACT_MVP_PRD.md
```
