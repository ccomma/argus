# Phase 11 Implementation Plan

> 这是阶段任务跟踪表，应保持简短和可操作；产品推理属于 PRD，架构决策属于技术设计，证明属于 `ACCEPTANCE.md`。

## Goal

构建团队治理平台：包括团队/成员模型与四级角色权限矩阵、团队能力编目聚合、安装/共享策略引擎，以及基于团队配置的仓库入职包自动生成器。

## Milestones

### 1. 团队核心模型

Status: done

Tasks:

- 实现 `MemberRole` 枚举（OWNER > ADMIN > MEMBER > VIEWER）和 `Permission` 枚举（READ/WRITE/ADMIN/DELETE）
- 实现 `ROLE_PERMISSIONS` 权限映射表（上级自动继承下级权限）
- 实现 `TeamMember` 不可变数据类，含 `has_permission()` 权限检查方法
- 实现 `Team` 聚合根数据类，含 `add_member`（支持重复 ID 更新）、`remove_member`、`get_member` 操作
- 实现 `Team.create()` 工厂方法（自动填入创建时间戳）
- 支持 `to_dict`/`from_dict` 序列化往返

### 2. 团队能力编目

Status: done

Tasks:

- 实现 `TeamCatalog` 数据类，聚合合约/角色/能力包/资产/模板五类引用
- 实现 `add_contract/add_role/add_pack/add_template` 增删方法（模板支持同名覆盖更新）
- 实现 `save/load` 持久化到 JSON 文件
- 实现 `TeamCatalogManager` 管理器：`save/load/list_all` 多编目文件管理
- 实现 `compute_stats` 统计方法：跨合约/角色/包/资产/模板的五维计数

### 3. 团队策略引擎

Status: done

Tasks:

- 实现 `TeamPolicy` 数据类，包含 7 个配置开关：默认角色、自注册、安装审批、共享开关、自动安装、来源黑白名单、例外规则
- 实现 `can_install(source, role)` — 来源黑白名单优先，OWNER/ADMIN 始终可安装
- 实现 `can_share_contract/can_share_role` — 基于共享开关和角色判断
- 实现 `add_exception/remove_exception` 例外规则管理
- 实现 `save/load` JSON 持久化

### 4. 入职包生成器

Status: done

Tasks:

- 实现 `OnboardingPack` 不可变数据类，含规则列表、必需能力、推荐包/角色、合约模板、初始化步骤
- 实现 `render_markdown()` 输出可读 Markdown 入职文档
- 实现 `OnboardingGenerator` 生成器，注入 Storage/Inventory/PackStore/RoleStore/CatalogMgr 依赖
- 实现 `generate(repo_name, team_id, policy)` 主流程：SHA1 生成 pack_id、收集五维信息后组装
- 实现 `_gather_rules`（活跃规则 + 关联合约）、`_gather_required_capabilities`（活跃资产列表）
- 实现 `_gather_recommended_packs/_roles`（团队编目优先，全局库存补充）
- 实现 `save(pack, out_dir)` 输出 .md 和 .json 双格式文件

### 5. CLI 命令

Status: done

Tasks:

- 实现 `team create/list/show/add-member/remove-member` — 团队与成员管理命令
- 实现 `team catalog` — 编目快照命令
- 实现 `team policy/set-policy` — 策略查看与设置命令
- 实现 `onboarding generate` — 入职包生成命令（返回 JSON 含 markdown_path 和 pack 数据）
- 在 `main.py` 注册 `team` 和 `onboarding` 子命令解析器
- 在 `handlers.py` 注册 9 个 handler 函数

### 6. 测试

Status: done

Tasks:

- `Phase11TeamModelTest` — 6 个测试：创建团队、添加成员、重复成员更新、移除成员、序列化往返、权限矩阵
- `Phase11TeamCatalogTest` — 3 个测试：编目持久化、模板更新、管理器列表
- `Phase11TeamPolicyTest` — 5 个测试：默认策略、安装判断、共享判断、例外规则、策略持久化
- `Phase11OnboardingTest` — 3 个测试：Markdown 渲染、空生成器、文件保存
- `Phase11TeamCLITest` — 4 个测试：创建与列表、成员增删、策略展示、入职包生成 CLI
- 全量回归：201 个测试通过

## Verification Commands

```bash
# 团队测试
python -m unittest tests.test_phase11_team -v

# 全量回归
python -m unittest discover tests/ -v

# CLI 冒烟测试
python -m argus team create --store /tmp/.argus --team-id smoke --name "冒烟测试"
python -m argus team list --store /tmp/.argus
python -m argus onboarding generate --store /tmp/.argus --repo-name smoke-repo
```

## Closeout Checklist

- [x] Implementation matches PRD and technical design.
- [x] Relevant tests pass（17 个团队测试全部通过）。
- [x] Smoke commands pass or documented as not applicable.
- [x] `ACCEPTANCE.md` records actual evidence.
- [x] Phase `HANDOFF.md` is updated for future readers.
- [x] `docs/context/CURRENT_HANDOFF.md` points to the next phase or next task.
