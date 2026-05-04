# Phase 11: Team Governance Platform Technical Design

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本技术设计。本文件回答模块、接口、数据和风险边界，不记录每日执行状态。

## 1. Overview

Phase 11 将 Argus 从单用户治理扩展为团队协作平台，新增三大模块：(1) 团队模型与策略，定义成员角色权限体系、团队聚合和安装/共享策略；(2) 能力编目管理，为团队聚合共享的合约、角色、能力包引用和模板；(3) 仓库入职包生成器，为新仓库自动生成包含规则、能力需求、角色推荐和初始化步骤的入职指南。

## 2. Architecture

```
team/                         onboarding/
  Team (aggregate)              OnboardingGenerator
  ├─ members: TeamMember[]        ├─ _gather_rules()
  ├─ repositories: str[]          ├─ _gather_required_capabilities()
  └─ tags: str[]                  ├─ _gather_recommended_packs()
  TeamCatalog                     ├─ _gather_roles()
    ├─ contract_ids[]             ├─ _gather_contract_templates()
    ├─ role_ids[]                 ├─ _build_setup_instructions()
    ├─ pack_ids[]                 └─ save() → .md + .json
    ├─ capability_ids[]
    └─ shared_templates[]       OnboardingPack (frozen)
  TeamCatalogManager              ├─ rules, required_capabilities
    ├─ save/load/list_all         ├─ recommended_packs, roles
    └─ compute_stats()            ├─ contract_templates
  TeamPolicy                      └─ setup_instructions
    ├─ can_install()
    ├─ can_share_contract()
    └─ can_share_role()
```

数据流：Team 作为聚合根持有成员列表，TeamPolicy 控制团队治理行为。TeamCatalog 存储团队维度的引用集合（不实际复制数据）。OnboardingGenerator 聚合 inventory、storage、pack_store、role_store 和 catalog_mgr 五个数据源，为新仓库生成 OnboardingPack。

## 3. Data Model

```text
# ---- Team Models ----
MemberRole (enum): OWNER="owner", ADMIN="admin", MEMBER="member", VIEWER="viewer"
Permission (enum): READ="read", WRITE="write", ADMIN="admin", DELETE="delete"

ROLE_PERMISSIONS:
  OWNER  → [READ, WRITE, ADMIN, DELETE]
  ADMIN  → [READ, WRITE, ADMIN]
  MEMBER → [READ, WRITE]
  VIEWER → [READ]

TeamMember (frozen dataclass)
- member_id: str              # 唯一标识
- name: str                   # 成员名称
- role: MemberRole            # 角色，默认 MEMBER
- email: str                  # 邮箱，默认 ""

Team (mutable dataclass)
- team_id: str                # 团队唯一 ID
- name: str                   # 团队名称
- description: str            # 说明
- members: list[TeamMember]   # 成员列表
- repositories: list[str]     # 关联仓库
- tags: list[str]             # 标签
- created_at: int             # Unixtime
+ add_member(member)           # 同 ID 更新，否则追加
+ remove_member(member_id)     # 按 ID 移除，返回是否成功
+ get_member(member_id)        # 按 ID 查找，返回 None 表示不存在

TeamCatalog (mutable dataclass)
- team_id: str                # 所属团队 ID
- contract_ids: list[str]     # 共享合约 ID 引用
- role_ids: list[str]         # 共享角色 ID 引用
- pack_ids: list[str]         # 共享能力包 ID 引用
- capability_ids: list[str]   # 共享能力资产 ID 引用
- shared_templates: list[dict] # 共享模板 [{name, content}]
+ add_contract/add_role/add_pack/add_template()  # 去重追加

TeamPolicy (mutable dataclass)
- team_id: str                # 所属团队 ID
- default_member_role: str    # 默认角色，默认 "member"
- allow_self_enrollment: bool # 是否允许自助加入
- require_approval_for_install: bool  # 安装需审批，默认 True
- shared_contract_templates: bool     # 共享合约模板，默认 True
- shared_role_packs: bool             # 共享角色包，默认 True
- auto_install_trusted: bool          # 信任来源自动安装，默认 False
- blocked_sources: list[str]          # 来源黑名单
- allowed_sources: list[str]          # 来源白名单
- exception_rules: list[dict]         # 例外规则 [{subject, action, reason}]
+ can_install(source, member_role) → bool
+ can_share_contract(member_role) → bool
+ can_share_role(member_role) → bool

# ---- Onboarding ----
OnboardingPack (frozen dataclass)
- pack_id: str                # SHA-1 前 12 位
- repo_name: str              # 目标仓库名
- team_id: str                # 关联团队
- rules: list[str]            # 收集到的活跃规则
- required_capabilities: list[str]  # 必需能力清单（最多 20 条）
- recommended_packs: list[str]      # 推荐能力包（最多 10 个）
- roles: list[str]                  # 推荐角色（最多 10 个）
- contract_templates: list[dict]    # 合约模板（最多 5 个）
- setup_instructions: list[str]     # 初始化步骤
- created_at: int
```

## 4. Interfaces

### CLI

```text
argus team create|add-member|remove-member|show|list|catalog|policy|set-policy
  create:     --team-id --name [--description]
  add-member: --team-id --member-id --name [--role owner|admin|member|viewer]
  remove-member: --team-id --member-id
  show:       --team-id
  list:       (无参数，列出所有团队)
  catalog:    --team-id (显示编目统计)
  policy:     --team-id (显示团队策略)
  set-policy: --team-id [--allow-self-enrollment]
              [--require-approval-for-install] [--shared-contract-templates]
              [--shared-role-packs] [--auto-install-trusted]
              [--blocked-source ...] [--allowed-source ...]

argus onboarding generate
  --repo-name <name> [--team-id <id>]
```

### Python API

```python
from argus.team import Team, TeamMember, MemberRole, TeamCatalog, TeamCatalogManager, TeamPolicy
from argus.onboarding import OnboardingGenerator, OnboardingPack

# 团队管理
team = Team.create("eng", "Engineering Team", "Core engineering")
member = TeamMember("alice", "Alice", MemberRole.ADMIN)
team.add_member(member)
team.remove_member("bob")

# 编目管理
mgr = TeamCatalogManager(Path("teams/catalogs"))
stats = mgr.compute_stats("eng", storage, inventory, pack_store, role_store)
# stats → {team_id, contracts, roles, packs, capabilities, templates}

# 策略决策
policy = TeamPolicy.load(path)
can = policy.can_install("https://skills.example.com", MemberRole.MEMBER)
# 阻止名单优先检查 → 允许名单放行 → OWNER/ADMIN 放行 → require_approval 开关决定

# 入职包生成
gen = OnboardingGenerator(storage, inventory, pack_store, role_store, catalog_mgr)
pack = gen.generate("my-repo", team_id="eng", policy=team_policy)
md_path = gen.save(pack, out_dir)  # 输出 {pack_id}.md + {pack_id}.json
```

## 5. Storage

| 数据 | 存储路径 | 格式 |
|------|---------|------|
| 团队定义 | `<store>/teams/{team_id}.json` | JSON |
| 团队编目 | `<store>/teams/catalogs/{team_id}.json` | JSON |
| 团队策略 | `<store>/teams/policies/{team_id}.json` | JSON |
| 入职包 | `<store>/onboarding/{pack_id}.md` + `.json` | Markdown + JSON |

所有文件均独立存储。Team 和 TeamPolicy 分开管理（CLI 的 `team policy` 和 `team set-policy` 操作独立的 `teams/policies/` 目录），两者通过 `team_id` 关联。TeamCatalog 存储引用 ID（不复制数据），实际数据由各自的 store 对象查询提供。OnboardingPack 生成后持久化为双格式文件。

## 6. Governance and Security

- **角色权限矩阵**：OWNER > ADMIN > MEMBER > VIEWER，权限逐级继承。TeamMember.has_permission() 通过查表实现权限检查。
- **安装策略**：TeamPolicy.can_install() 采用 blocklist-first 安全策略——阻止来源直接拒绝，允许来源直接放行，OWNER/ADMIN 始终可安装，其余成员受 `require_approval_for_install` 开关控制。
- **共享策略**：can_share_contract/can_share_role 同时检查共享开关和角色权限（VIEWER 不可共享）。
- **入职包安全**：OnboardingGenerator._gather_required_capabilities() 仅收集 active 状态资产，废弃/归档资产不会出现在推荐清单中。最多限制 20 条能力、10 个包和角色，防止生成过大的入职文档。
- **无自动变更**：所有团队治理决策通过策略检查方法返回布尔值，由调用方决定是否执行操作。不自动安装、不自动删除、不自动更改权限。

## 7. Failure Modes

- **团队不存在**：_load_team() 返回 None，CLI handler 返回 `{"error": "Team X not found"}` 和退出码 1。TeamCatalog.load() 缺失文件时返回空编目（team_id 设为路径 stem）。
- **策略文件缺失**：TeamPolicy.load() 返回默认策略（所有开关为安全默认值：需审批安装、不允许自助注册）。
- **成员重复添加**：add_member() 原地替换同 ID 旧成员（支持角色升级），不产生错误。
- **入职包生成无数据**：所有子收集方法均有空列表兜底，generate() 始终返回合法 OnboardingPack，不会因上游无数据而崩溃。
- **编目统计无匹配项**：compute_stats() 在各维度过滤后可能返回空列表，计数为 0，不报错。

## 8. Test Strategy

- **Unit Tests**：TeamMember.has_permission() 各角色+权限组合。Team.add_member/remove_member/replace 行为。TeamPolicy.can_install 白名单/黑名单/角色/审批开关组合。MemberRole/Permission 枚举值与权限矩阵一致性。
- **Fixture Tests**：使用固定 fixtures 目录的团队 JSON 文件测试 from_dict/to_dict 往返一致性。编目 save/load 往返。
- **Integration Tests**：CLI 子命令 create→show→add-member→policy set→catalog 完整团队配置流程。onboarding generate 端到端输出文件存在性和内容校验。
- **Acceptance Tests**：完整团队场景：创建团队→添加成员→设置策略→生成入职包→检查入职包 Markdown 可读性和 JSON 结构完整性。

## 9. Compatibility

- **不修改 Phase 1-10 任何模块**：团队和入职模块为全新子系统，通过注入已有 Service 对象访问数据（storage, inventory, pack_store, role_store），不引入 breaking change。
- **与 Phase 10 Web 工作台的关系**：Web 工作台当前不内置团队页面，但 Team/TeamPolicy 可通过未来 API 端点集成（与 Phase 10 的 11 页模板模式兼容）。
- **入职包与 Phase 9 维护报告独立**：入职包存储在 `onboarding/` 目录，维护报告在 `maintenance/` 目录，互不干扰。

## 10. Open Questions

- TeamPolicy 的 `exception_rules` 是否应在 can_install 中动态消费（当前仅存储，策略决策未引用例外规则），需明确例外覆盖逻辑（例外是否优先于阻止名单）。
- TeamCatalog 当前仅存储引用 ID，不追踪数据变更——如果上游能力包被删除，编目中会出现悬空引用，是否需要周期性健康检查或软删除标记。
- 入职包的 role_ids 收集逻辑是否需要按优先级排序（编目角色 > 全局角色），当前为简单列表拼接。
- 是否需要 Team 级别的审计日志，记录成员增删、策略变更和共享操作。
