# Phase 11: 团队治理平台 Test Plan

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本测试计划。当前验收状态写入阶段目录的 `ACCEPTANCE.md`。

## 1. Scope

本测试计划覆盖：

- 团队模型：Team/TeamMember 的创建、成员增删、角色权限检查、序列化往返
- 团队编目：TeamCatalog 的合约/角色/包引用管理和模板共享
- 团队策略：TeamPolicy 的安装审批、来源黑白名单、例外规则、共享权限
- 入职包：OnboardingPack 模型渲染和 OnboardingGenerator 的生成与保存流程
- CLI 命令：team create/list/show/add-member/remove-member/policy、onboarding generate

不覆盖：

- 多团队并发操作
- 外部认证系统集成
- 入职包的自动推荐算法调优
- 团队间数据迁移

## 2. Fixtures

固定样例：

- 空临时目录：所有文件系统操作在 `tempfile.TemporaryDirectory()` 中执行
- 测试团队：`Team.create("t1", "Test Team", "A test team")` 创建空成员团队
- 测试成员：`TeamMember(member_id="u1", name="Alice", role=MemberRole.ADMIN)`
- 角色权限矩阵：OWNER 拥有全部 4 项权限，ADMIN 拥有 READ/WRITE/ADMIN，MEMBER 拥有 READ/WRITE，VIEWER 仅 READ
- 测试编目参数：`contract_ids=["c1"]`, `role_ids=["r1"]`, `pack_ids=["p1"]`

## 3. Unit Tests

测试文件: `tests/test_phase11_team.py`

- `Phase11TeamModelTest.test_team_create`：创建后 team_id/name 匹配，成员列表为空
- `Phase11TeamModelTest.test_team_add_member`：添加 ADMIN 角色成员后 has_permission(Permission.WRITE) 为 True
- `Phase11TeamModelTest.test_team_add_duplicate_member_updates`：同 ID 成员重复添加时角色更新为 ADMIN
- `Phase11TeamModelTest.test_team_remove_member`：移除后 get_member 返回 None，再次移除返回 False
- `Phase11TeamModelTest.test_team_roundtrip`：含 1 名 OWNER 成员的团队 to_dict/from_dict 往返后成员数一致
- `Phase11TeamModelTest.test_member_permissions`：OWNER 有 DELETE/ADMIN 权限，VIEWER 有 READ 无 WRITE 权限
- `Phase11TeamModelTest.test_team_save_and_load_file`：JSON 文件保存后加载 name 和成员数正确
- `Phase11TeamCatalogTest.test_catalog_save_and_load`：编目添加合约/角色/包后保存，加载后引用一致
- `Phase11TeamCatalogTest.test_catalog_add_template`：同名模板重复添加时内容原地更新，总数保持 1
- `Phase11TeamCatalogTest.test_catalog_manager_list_all`：保存 2 个团队编目后 list_all 返回 2 条
- `Phase11TeamPolicyTest.test_policy_defaults`：默认 require_approval_for_install=True，shared_contract_templates=True，auto_install_trusted=False
- `Phase11TeamPolicyTest.test_policy_can_install`：阻止源拒绝所有角色，允许源放行所有角色，ADMIN 对未知源可安装
- `Phase11TeamPolicyTest.test_policy_can_share`：ADMIN/MEMBER 可共享合约，VIEWER 不可
- `Phase11TeamPolicyTest.test_policy_exceptions`：add_exception 后规则数 +1，remove_exception 后恢复
- `Phase11TeamPolicyTest.test_policy_save_and_load`：auto_install_trusted=True 的策略保存后加载一致
- `Phase11OnboardingTest.test_onboarding_pack_render`：render_markdown 输出包含 repo_name、规则和能力引用
- `Phase11OnboardingTest.test_onboarding_generator_empty`：空存储生成入职包后 repo_name 匹配、pack_id 非空
- `Phase11OnboardingTest.test_onboarding_generator_save`：保存后 .md 和 .json 文件均存在

## 4. Fixture Tests

- VIEWER 角色调用 has_permission(Permission.READ) 返回 True，has_permission(Permission.WRITE) 返回 False
- TeamPolicy 在 blocked_sources=["evil.com"]、allowed_sources=["github.com/trusted"] 时，evil.com 不可安装、trusted 可安装
- OnboardingPack 渲染输出包含 "## Rules"、"## Required Capabilities"、"## Setup Instructions" 等段落标题
- 空存储的 OnboardingGenerator.generate("my-repo") 返回 pack 的 required_capabilities 和 roles 初始为空列表

## 5. Integration Tests

测试文件: `tests/test_phase11_team.py`（Phase11TeamCLITest 类）

- `test_team_create_and_list_cli`：CLI team create + list 返回 1 条团队，name 为 "CLI Team"
- `test_team_add_and_remove_member_cli`：CLI add-member 后 show 输出含 1 名成员，remove-member 后成员数为 0
- `test_team_policy_cli`：CLI team policy 返回 JSON 含 team_id 字段
- `test_onboarding_generate_cli`：CLI onboarding generate 返回 JSON 含 markdown_path、pack 和 repo_name

## 6. Acceptance Tests

验收方式：运行完整测试套件

```bash
PYTHONPATH=src python3 -m pytest tests/test_phase11_team.py -v
```

预期：全部 22 条测试通过（Phase11TeamModelTest: 7, Phase11TeamCatalogTest: 3, Phase11TeamPolicyTest: 5, Phase11OnboardingTest: 3, Phase11TeamCLITest: 4）。

## 7. Regression Risks

- MemberRole/Permission 枚举值变更导致权限矩阵异常：运行模型测试和权限检查测试
- TeamMember 从可变迁移为不可变（frozen dataclass）时 add_member 更新逻辑未同步：运行重复添加测试验证
- OnboardingGenerator 依赖 ContractStorage/CapabilityInventory/PackStore/RoleStore 外部组件变更：运行生成器单元测试 + CLI 集成测试
- team_id 字段在 TeamPolicy 中重复定义（dataclass 字段两次声明）导致实例化异常：运行策略全套测试验证首字段取值正确
- 入职包格式变更导致外部工具解析失败：运行 render_markdown 和 save 测试验证输出一致性

## 8. Test Commands

```bash
# 运行 Phase 11 全部测试
PYTHONPATH=src python3 -m pytest tests/test_phase11_team.py -v

# 仅运行单元测试（跳过 CLI 集成测试）
PYTHONPATH=src python3 -m pytest tests/test_phase11_team.py -v -k "not CLITest"

# 仅运行团队模型测试
PYTHONPATH=src python3 -m pytest tests/test_phase11_team.py -v -k "TeamModelTest"

# 仅运行团队策略测试
PYTHONPATH=src python3 -m pytest tests/test_phase11_team.py -v -k "TeamPolicyTest"

# 仅运行入职包测试
PYTHONPATH=src python3 -m pytest tests/test_phase11_team.py -v -k "OnboardingTest"

# 运行完整检查脚本
./scripts/check.sh
```
