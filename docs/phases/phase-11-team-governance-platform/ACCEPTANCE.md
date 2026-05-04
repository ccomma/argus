# Phase 11 Acceptance

> 本文件保存验收证据。它是检查历史阶段是否真正达到退出标准的首要参考。

## Acceptance Criteria

| Criterion | Status |
| --- | --- |
| 团队/成员模型支持四级角色和权限继承 | PASS — `MemberRole` (OWNER>ADMIN>MEMBER>VIEWER) + `ROLE_PERMISSIONS` 映射表 |
| Team 聚合根支持成员增删查操作 | PASS — `add_member`（重复 ID 更新）、`remove_member`（返回布尔）、`get_member` |
| TeamCatalog 编目聚合 5 类团队资产引用 | PASS — 合约/角色/能力包/能力/共享模板，支持 add 系列方法和持久化 |
| TeamCatalogManager 支持多编目统计 | PASS — `compute_stats` 跨合约/角色/包/资产/模板五维计数 |
| TeamPolicy 安装权限基于来源黑白名单和角色 | PASS — `can_install` 黑白名单优先，OWNER/ADMIN 始终可安装 |
| TeamPolicy 共享控制和例外规则 | PASS — `can_share_contract`/`can_share_role` + `add_exception`/`remove_exception` |
| OnboardingPack 入职包模型与 Markdown 渲染 | PASS — 不可变 dataclass，`render_markdown()` 输出完整入职文档 |
| OnboardingGenerator 聚合团队配置生成入职包 | PASS — 收集活跃规则/必需能力/推荐包/角色/合约模板，SHA1 生成 pack_id |
| 入职包生成器输出 .md + .json 双格式文件 | PASS — `save()` 方法写入双文件 |
| CLI `team` 命令族（8 个子命令） | PASS — `create/list/show/add-member/remove-member/catalog/policy/set-policy` |
| CLI `onboarding generate` 命令 | PASS — 返回 JSON 含 `markdown_path` 和 `pack` 数据 |
| 无回归 | PASS — 201 个测试通过 |

## Verification Evidence

Commands:

```bash
# 团队模型单元测试
python -m unittest tests.test_phase11_team.Phase11TeamModelTest -v

# 编目单元测试
python -m unittest tests.test_phase11_team.Phase11TeamCatalogTest -v

# 策略单元测试
python -m unittest tests.test_phase11_team.Phase11TeamPolicyTest -v

# 入职包单元测试
python -m unittest tests.test_phase11_team.Phase11OnboardingTest -v

# CLI 集成测试
python -m unittest tests.test_phase11_team.Phase11TeamCLITest -v

# 全量回归
python -m unittest discover tests/ -v
```

Result:

- 17 个阶段 11 测试全部通过。
- 201 个测试全部通过，无回归。

## Final Artifacts

- Code:
  - `src/argus/team/__init__.py` — 模块入口，导出 7 个公开符号
  - `src/argus/team/models.py` — `Team`、`TeamMember`、`MemberRole`、`Permission`
  - `src/argus/team/catalog.py` — `TeamCatalog`、`TeamCatalogManager`
  - `src/argus/team/policy.py` — `TeamPolicy`
  - `src/argus/onboarding/__init__.py` — 模块入口
  - `src/argus/onboarding/models.py` — `OnboardingPack`
  - `src/argus/onboarding/generator.py` — `OnboardingGenerator`
  - `src/argus/cli/workbench.py` — `add_team_commands`/`add_onboarding_commands` 及 9 个 handler
  - `src/argus/cli/handlers.py` — handler 注册表
  - `src/argus/cli/main.py` — `team`/`onboarding` 子命令注册
- Tests: `tests/test_phase11_team.py`（17 个测试）
- Reports: 入职包 Markdown 渲染输出
- Commit: `bcc300d`

## Remaining Risks

- 共享模板目前仅有存储占位，缺少模板引擎（如 Jinja2）进行参数化渲染——当前仅按名称做全量覆盖更新。
- 权限检查仅用于 `can_install`/`can_share` 方法，尚未在 CLI handler 层强制执行——所有 CLI 命令目前均可被任意调用。
- 入职包生成器的活跃能力列表硬编码上限为 20 条（`[:20]`），大型团队可能需要分页或评分排序。
