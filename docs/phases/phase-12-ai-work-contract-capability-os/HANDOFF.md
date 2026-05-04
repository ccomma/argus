# Phase 12 Handoff: AI 工作合约与能力操作系统

## Load Order

1. 阅读本文件。
2. 仅当项目级状态不明确时，阅读 `docs/context/CURRENT_HANDOFF.md`。
3. 阅读当前任务代码和测试。
4. 仅当需要领域语言或历史决策上下文时，阅读 `CONTEXT.md` 或特定 ADR。
5. 仅在必要时阅读本阶段 PRD / 技术设计 / 测试计划。
6. 仅当方向或阶段边界不明确时，阅读长期设计文档。

## Branch And Policy

- Branch: `codex/argus-structure-cleanup`
- Base: `main`
- Commit policy: 最小提交、每条提交涵盖一个逻辑单元、通过所有相关测试。

## Current Phase

- Phase: 12 — AI 工作合约与能力操作系统
- Goal: 构建能力操作系统核心基础设施：资产全生命周期状态机、多注册中心能力发现和闭环反馈自优化引擎。
- In scope:
  - 资产生命周期状态机：7 个状态（DRAFT/ACTIVE/DISABLED/ISOLATED/DEPRECATED/ARCHIVED/DELETED），9 种操作（CREATE/ACTIVATE/DISABLE/ISOLATE/RELEASE/DEPRECATE/ARCHIVE/DELETE/ROLLBACK）
  - `StateMachine` 类：基于 TRANSITIONS 转换表执行合法状态转换，非法操作抛出 ValueError
  - `LifecycleRecord` 不可变记录（SHA1 生成 record_id）和 `LifecycleLedger` JSONL 追加写入审计账本
  - 多注册中心能力发现：`RegistryEntry`（条目元信息）和 `RegistryIndex`（多维度搜索：名称/类型/标签/质量/风险）
  - 闭环反馈引擎：`FeedbackSignal`（success/failure/correction 三类信号）、`FeedbackLoop`（信号记录/列表/聚合/推荐）
  - 基于净评分的治理推荐：`compute_recommendation` 通过 `net_score = promote - demote - revise*0.5` 产生 promote/revise/review_or_deprecate/observe 决策
  - CLI 命令：`lifecycle show/apply/history`、`registry search/add/list`、`feedback record/list/recommend`
- Out of scope:
  - 外部注册中心（Skillsmith/SkillHub）的实际 HTTP 集成
  - 数据库/消息队列替代后端
  - 多区域/数据中心同步

## Key Artifacts

| Artifact | Path |
| --- | --- |
| 产品文档 | `docs/phases/phase-12-ai-work-contract-capability-os/PRD.md` |
| 技术设计 | `docs/phases/phase-12-ai-work-contract-capability-os/TECHNICAL_DESIGN.md` |
| 测试计划 | `docs/phases/phase-12-ai-work-contract-capability-os/TEST_PLAN.md` |
| 生命周期模型 | `src/argus/lifecycle/models.py` |
| 注册中心模型 | `src/argus/registry/models.py` |
| 反馈闭环引擎 | `src/argus/feedback/loop.py` |
| CLI 命令注册 | `src/argus/cli/workbench.py`（`add_lifecycle_commands`/`add_registry_commands`/`add_feedback_commands`） |
| CLI handler 注册 | `src/argus/cli/handlers.py`（lifecycle/registry/feedback handler） |
| 主测试 | `tests/test_phase12_operating_system.py` |

## Working Tree Notes

- Files owned by current work:
  - `src/argus/lifecycle/`（models.py, __init__.py）
  - `src/argus/registry/`（models.py, __init__.py）
  - `src/argus/feedback/`（__init__.py, loop.py）
  - `tests/test_phase12_operating_system.py`
- Files to avoid: 所有 `src/argus/team/`、`src/argus/onboarding/`（属于 Phase 11）。
- Shared docs rule: 链接拥有所有权的工件路径而非将内容复制到本 handoff 中。

## Verification Commands

```bash
# 运行 Phase 12 相关测试（30 个）
python -m unittest tests.test_phase12_operating_system -v

# 生命周期状态机
python -m argus lifecycle show --store .argus --asset-id a1 --current-state draft
python -m argus lifecycle apply --store .argus --asset-id a1 --asset-type skill --action activate --from-state draft
python -m argus lifecycle history --store .argus --asset-id a1

# 多注册中心发现
python -m argus registry add --store .argus --entry-id e1 --name "测试能力" --type skill --source local
python -m argus registry search --store .argus --name "测试能力"
python -m argus registry list --store .argus

# 闭环反馈
python -m argus feedback record --store .argus --source-type contract --source-id c1 --signal-type success --target-type role --target-id r1 --strength 0.8
python -m argus feedback list --store .argus
python -m argus feedback recommend --store .argus --target-type role --target-id r1

# 全量回归（201 个测试）
python -m unittest discover tests/ -v
```

## Next Work

- Phase 12 为计划的最后一个阶段。后续可选工作：
  - 桌面应用打包（Electron/Tauri wrapper）
  - 带认证的 SaaS 部署
  - 社区集成适配器 SDK
  - 外部注册中心实际集成

## Evidence To Preserve

- 提交 `d9cc185` — 生命周期管理、多注册中心发现和闭环反馈的完整实现。
- 测试文件 `tests/test_phase12_operating_system.py` 包含 30 个测试（Lifecycle 8 个、Registry 4 个、Feedback 5 个、CLI 5 个、子测试共覆盖 6 个子方法）。
- 201 个测试全部通过，无回归。

## Context Budget Rule

不要默认加载所有历史文档。以本 handoff 作为阶段入口点。
