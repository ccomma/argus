# Phase 11: Team Governance Platform PRD

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本 PRD。本文件只回答产品问题，不承担实现任务管理。

## 1. Background

Phase 10 完成了个人 Pro 工作台，让单用户可以通过 Web UI 管理合约、角色、策略和安全。Phase 11 将治理范围从个人扩展到团队：当多个开发者使用同一套 AI Agent 能力时，团队需要一个共享的合约模板库、角色目录、能力编目和权限体系。本阶段承接 roadmap 中 Phase 10 的个人策略引擎，扩展到团队维度的成员角色模型、编目管理、安装/共享策略和仓库入职包生成。

## 2. Users and Jobs

目标用户：

- 技术团队负责人或工程经理，需要统一管理团队的 AI Agent 能力。
- 团队成员，需要知道团队共享了哪些合约模板、角色和能力，以及如何使用。
- 新成员入职时的引导者，需要为新仓库生成包含规则、能力和角色的入职包。

用户任务：

- 创建团队、添加成员并分配角色（OWNER/ADMIN/MEMBER/VIEWER）。
- 构建团队能力编目，管理共享的合约、角色、能力包和模板。
- 配置团队策略：哪些来源的能力可安装、谁可以共享合约模板和角色包、是否需要安装审批。
- 为团队仓库生成入职包（OnboardingPack），包含活跃规则、所需能力、推荐包和角色、合约模板和初始化步骤。

## 3. Problem

当前问题：

- 个人工作台无法满足团队场景：所有合约、角色和能力包都是个人的，没有共享机制。
- 团队引入外部能力资产时缺乏审批流程和来源管控，可能引入安全风险或不一致的能力定义。
- 新成员加入仓库时不知道应该配置哪些规则、安装哪些能力和使用哪些角色。
- 团队成员对能力资产的修改没有权限边界，OWNER 和普通成员拥有相同的操作能力。

## 4. Goals

- 实现团队模型（Team、TeamMember），支持四级角色（OWNER/ADMIN/MEMBER/VIEWER）和四级原子权限（READ/WRITE/ADMIN/DELETE）。
- 构建团队能力编目（TeamCatalog）和编目管理器（TeamCatalogManager），管理共享的合约、角色、能力包和模板引用。
- 实现团队策略（TeamPolicy），控制能力安装审批、合约/角色共享权限、来源黑白名单和例外规则。
- 构建入职包生成器（OnboardingGenerator），从活跃规则、能力库存、团队编目和合约模板中聚合生成 OnboardingPack。
- 入职包输出 Markdown 和 JSON 双格式，Markdown 可直接作为新成员文档。

## 5. Non-goals

- 不做团队 Web APP 或 SaaS 形态（Phase 11 仍以 CLI + 数据模型为主，Web 团队界面为后续扩展）。
- 不做复杂的组织层级（多团队、子团队、跨团队共享），仅支持单团队模型。
- 不做实时协作编辑和冲突解决。
- 不做细粒度的资产级 ACL（如"Alice 只能修改 skill A"），权限控制在团队角色层面。

## 6. Core User Flows

核心流程 1 -- 创建团队并添加成员：
1. 团队负责人通过 CLI 创建 Team（team_id、name、description）。
2. 添加 TeamMember（member_id、name、role、email），角色决定其权限矩阵（OWNER 拥有全部权限，VIEWER 仅 READ）。
3. Team 保存为 JSON 文件，支持增删成员和按 ID 查询。

核心流程 2 -- 管理团队能力编目：
1. 团队负责人通过 TeamCatalog 添加共享的 contract_ids、role_ids、pack_ids、capability_ids 和 shared_templates。
2. TeamCatalogManager.save() 将编目持久化为 {team_id}.json。
3. TeamCatalogManager.compute_stats() 汇总编目覆盖情况：各维度的条目数量。
4. 成员通过 CLI 查询 `argus team catalog show <team_id>` 查看团队可用资源。

核心流程 3 -- 配置团队策略：
1. 团队负责人配置 TeamPolicy：设置 require_approval_for_install、shared_contract_templates、shared_role_packs、blocked_sources、allowed_sources。
2. can_install() 方法基于来源和成员角色判断安装权限：阻止源直接拒绝，允许源直接放行，OWNER/ADMIN 始终可安装，其余按审批开关决定。
3. can_share_contract() 和 can_share_role() 基于共享开关和角色（OWNER/ADMIN/MEMBER）判断共享权限。
4. 管理例外规则 add_exception/remove_exception。

核心流程 4 -- 生成仓库入职包：
1. 团队负责人运行 `argus team onboarding <repo_name> --team-id <id>`。
2. OnboardingGenerator.generate() 收集：库存中 active 的 rule 型资产、仓库关联的 work contracts、所有 active 资产（前 20 项）、团队编目中的推荐包和角色（不足时从全局补充）、团队共享模板和初始化步骤。
3. 组装为 OnboardingPack（不可变数据类，含 pack_id 基于 SHA-1 哈希）。
4. 输出 {pack_id}.md（Markdown 格式，含规则/能力/推荐包/角色/初始化步骤分节）和 {pack_id}.json。

## 7. Success Criteria

- Team 模型支持四级角色和对应的权限矩阵，has_permission() 方法正确检查。
- TeamCatalogManager 支持编目的保存、加载、列表和统计计算。
- TeamPolicy 的 can_install 正确执行来源黑白名单和角色权限判断。
- TeamPolicy 的 can_share_contract 和 can_share_role 正确执行共享开关和角色判断。
- OnboardingGenerator 成功收集规则、能力、推荐包、角色和合约模板，组装为 OnboardingPack。
- 入职包 render_markdown() 输出结构化的人可读文档。
- 团队策略支持持久化为 JSON 文件并重新加载。

## 8. Risks and Open Questions

风险：

- 当前未实现真正的权限执行层：TeamPolicy 和 Team 模型定义了权限逻辑，但 CLI 命令和 Web API 尚未接入权限检查，权限系统目前是"模型完备，执行空转"状态。
- TeamCatalog 仅存储 ID 引用，不实际持有数据，如果被引用的合约、角色或能力包被删除，编目将出现悬空引用。
- OnboardingGenerator 的 _gather_required_capabilities 硬编码为前 20 条 active 资产，可能无法准确反映仓库实际需求。

开放问题：

- 权限执行层何时与 Web 工作台和 CLI 命令集成？
- TeamCatalog 是否需要支持悬空引用检测和自动清理？
- 入职包是否需要支持基于仓库语言/框架的智能推荐（当前为简单聚合）？
- 多团队场景下，跨团队共享的合约模板和角色如何建模？
