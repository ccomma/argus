# CLAUDE.md

## 入口

开始任何工作前，按顺序加载：

1. `docs/context/CURRENT_HANDOFF.md` — 当前阶段、分支、验证命令、下一步
2. 当前阶段 `docs/phases/phase-XX-*/HANDOFF.md` — 阶段入口

## 开发流程

本项目遵循 `docs/process/DEVELOPMENT_FLOW.md` 定义的 8 步流程。关键约束：

- **新阶段必须先写 PRD → 技术设计 → 测试计划，再写代码**（Step 4-6 在 Step 7 之前）
- 阶段结束必须复盘并更新 `CURRENT_HANDOFF.md`（Step 8）
- 文档模板在 `docs/templates/` 下

## 常用技能

| 场景 | 技能 |
|------|------|
| 代码审查 | `code-review` skill |
| 实现新功能 | 先读 DEVELOPMENT_FLOW.md，按阶段流程推进 |
| 架构决策 | 参考 `docs/adr/` 目录，模板在 `docs/templates/ADR_TEMPLATE.md` |

## 项目约束

- 零外部依赖，仅使用 Python 标准库
- 存储后端为 JSON/JSONL 文件系统
- 不可变数据模型（frozen dataclass）
- 追加写入（append-only）的审计日志
