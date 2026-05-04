# 技术设计文档

本目录存放 Argus 各阶段技术设计。

技术设计负责说明模块边界、数据模型、接口、存储、安全治理、失败模式和测试策略。产品背景和成功标准应放在 `docs/prd/`。

从 Phase 0 起，技术设计就是当前阶段执行包的支撑材料，不是每次开发都必须完整加载的文档。新会话先读 `docs/context/CURRENT_HANDOFF.md` 和当前阶段 `HANDOFF.md`，只有需要模块、接口、数据或风险边界细节时才读取当前阶段技术设计。

创建新技术设计时，从 `docs/templates/TECHNICAL_DESIGN_TEMPLATE.md` 复制结构，并按阶段命名：

```text
PHASE_1_WORK_CONTRACT_MVP_TECHNICAL_DESIGN.md
```
