# Phase 11 Handoff: 团队治理平台

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

- Phase: 11 — 团队治理平台
- Goal: 构建团队管理基础设施，包括团队成员/角色/权限模型、团队能力编目、治理策略引擎，以及仓库入职包自动生成能力。
- In scope:
  - Team/TeamMember 数据模型与四级角色（OWNER/ADMIN/MEMBER/VIEWER）权限矩阵
  - TeamCatalog 编目聚合（合约/角色/能力包/资产/模板引用）
  - TeamPolicy 策略引擎（安装审批、共享开关、来源黑白名单、例外规则）
  - 内置策略安装函数 `can_install`、共享控制 `can_share_contract`/`can_share_role`
  - OnboardingPack 入职包模型与 Markdown 渲染
  - OnboardingGenerator 入职包生成器（聚合活跃规则、能力、推荐包/角色、初始化步骤）
  - CLI 命令：`team create/list/show/add-member/remove-member/catalog/policy/set-policy`、`onboarding generate`
- Out of scope:
  - 身份认证与单点登录
  - 实时协作/在线编辑
  - 第三方通知集成
  - 复杂度评分算法

## Key Artifacts

| Artifact | Path |
| --- | --- |
| 产品文档 | `docs/phases/phase-11-team-governance-platform/PRD.md` |
| 技术设计 | `docs/phases/phase-11-team-governance-platform/TECHNICAL_DESIGN.md` |
| 测试计划 | `docs/phases/phase-11-team-governance-platform/TEST_PLAN.md` |
| 团队模型 | `src/argus/team/models.py` |
| 团队编目 | `src/argus/team/catalog.py` |
| 团队策略 | `src/argus/team/policy.py` |
| 入职包模型 | `src/argus/onboarding/models.py` |
| 入职包生成器 | `src/argus/onboarding/generator.py` |
| CLI 命令注册 | `src/argus/cli/workbench.py`（`add_team_commands`/`add_onboarding_commands`） |
| CLI handler 注册 | `src/argus/cli/handlers.py`（team/onboarding handler） |
| 主测试 | `tests/test_phase11_team.py` |

## Working Tree Notes

- Files owned by current work:
  - `src/argus/team/`（models.py, catalog.py, policy.py, __init__.py）
  - `src/argus/onboarding/`（models.py, generator.py, __init__.py）
  - `tests/test_phase11_team.py`
- Files to avoid: 所有 `src/argus/lifecycle/`、`src/argus/registry/`、`src/argus/feedback/`（属于 Phase 12）。
- Shared docs rule: 链接拥有所有权的工件路径而非将内容复制到本 handoff 中。

## Verification Commands

```bash
# 运行团队相关测试（17 个）
python -m unittest tests.test_phase11_team -v

# 团队创建与列表
python -m argus team create --store .argus --team-id test-team --name "测试团队"
python -m argus team list --store .argus

# 成员管理
python -m argus team add-member --store .argus --team-id test-team --member-id u1 --name "张三" --role admin
python -m argus team show --store .argus --team-id test-team
python -m argus team remove-member --store .argus --team-id test-team --member-id u1

# 编目与策略
python -m argus team catalog --store .argus --team-id test-team
python -m argus team policy --store .argus --team-id test-team

# 入职包生成
python -m argus onboarding generate --store .argus --repo-name my-project

# 全量回归（201 个测试）
python -m unittest discover tests/ -v
```

## Next Work

- Phase 12: AI 工作合约与能力操作系统（生命周期状态机、多注册中心发现、闭环反馈引擎）

## Evidence To Preserve

- 提交 `bcc300d` — 团队治理平台与入职包的完整实现。
- 测试文件 `tests/test_phase11_team.py` 包含 17 个测试（Team 模型 6 个、TeamCatalog 3 个、TeamPolicy 5 个、Onboarding 3 个、CLI 4 个子测试）。
- 201 个测试全部通过，无回归。

## Context Budget Rule

不要默认加载所有历史文档。以本 handoff 作为阶段入口点。
