# Argus 完整开发阶段计划

本文是 Argus 从设计记忆走向长期工程项目的阶段路线图。它回答“先做什么、后做什么、每个阶段怎样算完成”，不替代各阶段的 PRD、技术设计或开发任务清单。

`DESIGN.md` 继续作为长期产品判断和架构原则入口；本文件负责可执行阶段规划，并会随着实际开发持续修订。

## 0. 路线图原则

- 先追问模式工作契约，再自动学习和能力管理底座。
- 先个人可用，再团队平台。
- 先真实可用小闭环，再完整 AI Work Contract & Capability Operating System。
- 先主动追问、需求澄清、工作契约、结构化交付，再进入自动安装、自动修改和跨 agent 运行时能力。
- 产品形态先采用 CLI + 本地文件存储；中期扩展 Argus Core、MCP server 和 adapter；后期再做 Dashboard、桌面 App、团队 Web / SaaS。
- Argus 的本体是 runtime-neutral core，不是某个 agent 插件，也不是早期独立 agent runtime。
- 所有 durable behavior change 都必须可追踪、可验证、可治理、可回滚。
- 核心模型保持 runtime-neutral，短期 adapter 可以 Codex-first。
- 开发执行采用“短 handoff 驱动 + 长文档按需加载”：roadmap 只做阶段地图，当前阶段执行依赖 `docs/context/CURRENT_HANDOFF.md` 和 `docs/phases/<phase>/HANDOFF.md`，阶段证据保存在 `ACCEPTANCE.md`，避免每次开发完整加载所有长期文档。

## 1. 阶段总览

| 阶段 | 名称 | 核心目标 | 主要产物 |
| --- | --- | --- | --- |
| Phase 0 | 项目文档与决策骨架 | 让 Argus 从设计记忆变成可持续开发项目 | 路线图、流程、模板、ADR |
| Phase 1 | 追问模式工作契约 MVP | 证明“主动追问并生成工作契约”是更直接的用户价值 | CLI、本地文件存储、work contract、question strategy、completeness score、deliverable contract、结构化交付物 |
| Phase 2 | Argus Core 事件与候选学习账本 | 证明工作契约需要可追踪学习底座 | Argus Core 雏形、event ledger、candidate learning ledger、学习报告 |
| Phase 3 | 个人本地能力资产清单 | 证明 Argus 管的是 capability assets | asset inventory、扫描器、资产报告 |
| Phase 4 | Capability Pack 与角色组合 | 把能力组合成可治理的工作契约、工作模式和角色 | work contract capability pack、role pack、能力依赖、版本、风险、回滚信息 |
| Phase 5 | 个人版治理报告与低风险自动化 | 从看见工作契约、角色和资产进入治理 | governance report、低风险自动化、确认边界 |
| Phase 6 | 能力解析器与受控安装建议 | 判断缺的是知识、流程还是工具能力 | capability resolver、复用/安装/创建建议 |
| Phase 7 | 受控修改与回滚机制 | 进入受控工作契约、角色和能力修改 | backup、diff、audit、rollback |
| Phase 8 | 跨角色与跨 Agent Adapter | 从单角色单 agent 走向 runtime-neutral | MCP server、adapter、CLI/MCP 查询、role handoff |
| Phase 9 | Dashboard、ROI 与维护任务 | 让工作契约、学习和能力管理效果可见 | local dashboard、维护任务、contract ROI、learning ROI、capability ROI |
| Phase 10 | 个人 Pro 版工作台 | 打磨重度 AI 用户和 AI coding 用户体验 | Desktop App / Local Web UI、Work Contract Console、Personal Playbook Registry、Role Pack Registry、策略自动化 |
| Phase 11 | 团队版工作契约与能力治理平台 | 扩展到团队 agent enablement | Web App / SaaS、team work contract templates、role catalog、权限、审计、共享策略 |
| Phase 12 | AI Work Contract & Capability Operating System | 形成长期基础设施形态 | runtime-neutral core、生命周期治理、供应链安全、adapter SDK |

## 2. Phase 0：项目文档与决策骨架

目标：把 Argus 从设计记忆变成可持续开发项目。

核心能力：

- 建立统一 `docs/` 文档体系。
- 明确 `DESIGN.md`、`CONTEXT.md`、roadmap、PRD、技术设计、测试文档、ADR 的职责边界。
- 建立短 handoff 驱动的上下文加载协议。
- 建立共享文档命名空间的所有权规则，避免不同 agent、skill 或工具重复定义同一类内容。
- 建立阶段执行包格式，让 Phase 1 起每个阶段都有 handoff、implementation plan 和 acceptance evidence。
- 提供后续每个阶段可复用的文档模板。

输入：

- `DESIGN.md`
- `CONTEXT.md`
- 当前阶段计划讨论

输出：

- `docs/roadmap/ARGUS_DEVELOPMENT_PLAN.md`
- `docs/process/DEVELOPMENT_FLOW.md`
- `docs/templates/PRD_TEMPLATE.md`
- `docs/templates/TECHNICAL_DESIGN_TEMPLATE.md`
- `docs/templates/TEST_PLAN_TEMPLATE.md`
- `docs/templates/HANDOFF_TEMPLATE.md`
- `docs/templates/IMPLEMENTATION_PLAN_TEMPLATE.md`
- `docs/templates/ACCEPTANCE_TEMPLATE.md`
- `docs/context/CURRENT_HANDOFF.md`
- `docs/templates/ADR_TEMPLATE.md`
- `docs/prd/README.md`
- `docs/technical/README.md`
- `docs/testing/README.md`
- `docs/adr/README.md`
- `docs/agents/domain.md`

验收标准：

- 任何后续阶段都能按模板补 PRD、技术设计和测试计划。
- `DESIGN.md` 不承担任务管理，roadmap 不承担详细实现设计。
- `CONTEXT.md` 只承担领域语言，不承担产品定位或阶段状态。
- 共享 `docs/` 目录内的每类文档都有明确所有权和更新触发条件。
- 新开发者能从 README 进入公开项目介绍，维护者能从本地设计文档进入路线图和开发流程。

退出条件：

- 文档骨架已创建。
- `docs/context/CURRENT_HANDOFF.md` 已成为默认承接入口。
- Phase 1 阶段执行包已创建。
- README 已转为面向 GitHub 用户的公开介绍。
- 设计、计划、上下文文档仍保持本地私有，不进入 git。

下一阶段前置条件：

- Phase 1 PRD 已创建并评审。
- Phase 1 技术设计已明确 work contract、question strategy、deliverable contract 的最小模型。

## 3. Phase 1：追问模式工作契约 MVP

目标：证明用户需要“agent 主动追问并生成工作契约”，不只是 memory、角色模板、skill 或能力治理。

核心能力：

- 提供最小 CLI 入口，优先服务本地开发和 fixture 验证。
- 使用本地文件存储 work contract、版本历史、交付物和验收结果。
- 用户只输入模糊意图。
- Argus 主动追问，直到形成目标、背景、输入、输出、约束、风险、确认点和验收标准。
- 输出 work contract，并可派生结构化交付物，例如市场价值判断、需求澄清记录、PRD 草案、阶段计划或技术前置问题。
- 支持追问模式的 completeness score、question budget 和 exit condition，避免无限聊天。
- 支持工作契约最小版本号和变更记录，让后续需求变化可以 diff 和复盘。
- 支持交付物验收清单，让生成的 PRD、计划或报告能对照契约检查缺失项。
- 可以预制 1-2 个角色作为能力组合示例，例如 Product Strategist 和 Product Manager，但角色不是第一版唯一中心。

关键接口：

- Work Contract：`intent`、`goal`、`context`、`inputs`、`outputs`、`constraints`、`risks`、`confirmation_points`、`acceptance_criteria`、`completion_definition`、`status`、`version`、`change_history`。
- Role Profile：`name`、`role_type`、`responsibilities`、`non_goals`、`task_types`、`status`。
- Question Strategy：`required_facts`、`decision_points`、`follow_up_rules`、`question_budget`、`completion_criteria`。
- Completeness Score：`goal_score`、`context_score`、`input_score`、`output_score`、`constraint_score`、`risk_score`、`acceptance_score`、`overall_score`。
- Workflow Playbook：`stages`、`stage_inputs`、`stage_outputs`、`handoff_points`。
- Deliverable Contract：`deliverable_type`、`required_sections`、`acceptance_criteria`、`missing_item_policy`。

输入：

- 用户模糊意图。
- 角色定义。
- 交付物模板。

输出：

- CLI 命令输出。
- 本地 `.argus/` 或等价本地存储产物。
- 澄清后的需求。
- 工作契约。
- 结构化阶段计划或 PRD 草案。
- 交付物验收清单。
- 用户确认记录。

验收标准：

- 用户能明显感受到“不用知道流程，Argus 会问到足够清楚”。
- 追问不是泛泛聊天，而是稳定收敛到工作契约和交付物。
- 至少一个真实项目场景能从模糊意图走到可执行阶段计划。
- 工作契约能说明为什么还需要继续追问，或为什么已经可以进入执行。
- 交付物能对照工作契约给出通过、部分通过或缺失项提示。
- 第一版可以通过 CLI 和本地文件完整跑通，不依赖桌面 App、Web App、插件或独立 agent runtime。
- 不接入复杂自动安装和自动修改，避免过早进入治理复杂度。

退出条件：

- 固定 fixture 能稳定复现追问、工作契约和交付物结构。
- 至少一个 question strategy、work contract 和 deliverable contract 完整可读。
- 工作契约 schema 能支持后续 contract diff、execution evidence 和 reverse learning。
- CLI 命令形态足够稳定，可作为 Phase 2 Argus Core 的输入入口。

下一阶段前置条件：

- 明确工作契约生成过程中的事件如何进入 Argus Core。
- Phase 2 PRD 已确定 event schema 和 candidate learning item schema。

## 4. Phase 2：Argus Core 事件与候选学习账本

目标：补上原项目核心，证明工作契约背后需要可追踪学习底座。

核心能力：

- 抽出 Argus Core 雏形，让 CLI 调用核心模型而不是把业务逻辑写死在命令层。
- 读取 Codex transcript 或本地会话导出。
- 记录追问过程、工作契约版本、用户确认、用户纠正、命令失败、成功路径。
- 抽取失败、纠正、重复模式、成功路径。
- 生成 candidate learning items。
- 记录交付物验收结果和执行证据，为后续反向学习提供依据。
- 输出本地学习报告。
- 不写入长期规则，不自动修改能力资产。

关键接口：

- Event Record：`agent`、`contract_id`、`contract_version`、`role`、`workspace`、`session`、`timestamp`、`event_type`、`evidence`、`execution_evidence`、`risk_metadata`。
- Candidate Learning Item：`summary`、`type`、`scope`、`confidence`、`evidence_refs`、`reverse_learning_target`、`status`。

输入：

- Codex transcript 样例。
- 工作契约对话样例。
- 用户纠正、命令失败、任务成功路径等事件。

输出：

- append-only event ledger。
- candidate learning ledger。
- 本地学习报告。
- 工作契约执行证据摘要。

验收标准：

- 能用真实 Codex 记录和工作契约对话记录生成候选学习账本。
- 能区分原始事件、工作契约事件、角色交互事件和候选学习项。
- 能把返工、验收失败或用户纠正归因到 question strategy、deliverable contract、role playbook 或 capability pack。
- 能输出说明性强、可追踪证据的本地学习报告。
- 没有自动写入 memory、skill、rules、role profile 或 agent 全局配置。

退出条件：

- 固定 fixture 能稳定生成相同 ledger 和 report。
- 至少覆盖成功会话、命令失败后修复、用户明确纠正、工作契约追问四类样例。
- Argus Core 与 CLI 边界清晰，后续可被 MCP server、adapter 或 UI 复用。

下一阶段前置条件：

- Phase 3 PRD 明确首批扫描范围。
- capability asset schema 初版冻结。

## 5. Phase 3：个人本地能力资产清单

目标：证明 Argus 管的是 capability assets，不只是 memory。

核心能力：

- 扫描本机 skills、plugins、MCP config、rules、scripts、memory。
- 生成统一 capability asset inventory。
- 记录来源、路径、类型、状态、作用域、风险初评。
- 把候选学习项关联到已有能力资产。

关键接口：

- Capability Asset：`name`、`type`、`source`、`version`、`install_path`、`agents`、`scope`、`permissions`、`risk_score`、`status`。
- Asset Status：`active`、`disabled`、`isolated`、`deprecated`、`archived`。

输入：

- 本机 skill 目录。
- 本机 plugin manifest。
- MCP 配置文件。
- rules、memory、scripts 等本地能力文件。

输出：

- capability asset inventory。
- asset scan report。
- candidate-to-asset link report。
- 当前阶段 handoff、实现计划和验收清单。

验收标准：

- 能展示当前本机 agent 能力资产全貌。
- 能发现重复或疑似冲突能力。
- 能判断一个候选问题是否已有本地能力可复用。

退出条件：

- 至少支持 Codex skills/plugins、MCP config 和本地 scripts 三类资产。
- 扫描过程默认只读，不修改任何能力文件。
- `docs/phases/phase-03-capability-asset-inventory/` 已记录实际实现、验收结果和下一阶段交接信息。
- Phase 1、Phase 2、Phase 3 都有阶段执行包和验收证据，未来会话不需要回读完整历史文档即可承接。

下一阶段前置条件：

- 初版 work contract capability pack 和 role capability pack schema 已写入技术设计。

## 6. Phase 4：Capability Pack 与角色组合

目标：把能力从零散工具变成可组合、可治理、可切换的工作模式或角色。

核心能力：

- 每个工作契约可以绑定默认 capability pack，并记录为什么当前任务需要这些能力。
- 每个角色可以绑定默认 capability pack。
- capability pack 可以引用 skill、MCP、plugin、script、workflow、template、rule。
- 支持本地能力优先检索，再建议外部能力。
- 对能力包做版本、权限、风险、使用次数和回滚方式记录。
- 支持工作模式和角色间的能力复用、能力冲突提示和能力组合。

关键接口：

- Role Capability Pack：`role_id`、`required_assets`、`optional_assets`、`activation_policy`、`risk_level`、`version`、`rollback_ref`。
- Work Contract Capability Pack：`contract_id`、`required_assets`、`optional_assets`、`activation_policy`、`risk_level`、`version`、`rollback_ref`。
- Role Asset Link：`role_id`、`asset_id`、`purpose`、`trigger_condition`、`required`。

输入：

- work contract。
- deliverable contract。
- role profile。
- capability asset inventory。
- candidate learning items。

输出：

- work contract capability pack。
- role capability pack。
- role-to-asset link report。
- missing capability suggestions。

验收标准：

- 至少一个工作契约能展示完整能力包。
- 至少一个角色能展示完整能力包。
- 能说明每个能力为何被当前工作需要。
- 能发现工作契约或角色的能力缺口和重复能力。
- 能把 capability pack 与工作契约版本绑定，避免需求变化后继续使用过期能力组合。

退出条件：

- 一个从模糊意图生成的工作契约拥有最小可用能力包。
- Product Manager 或 Product Strategist 角色拥有最小可用能力包。
- 能力包默认只读，不自动安装外部能力。

下一阶段前置条件：

- 治理报告的读者和输出格式已在 PRD 中确定。

## 7. Phase 5：个人版治理报告与低风险自动化

目标：从“看见工作契约、角色和资产”进入“治理工作契约、角色和资产”。

核心能力：

- 生成周期性治理报告。
- 标记重复、过期、低使用、高风险能力。
- 标记低质量、返工率高或验收标准不完整的工作契约。
- 标记低质量、返工率高或提问不完整的角色流程。
- 标记交付物验收器发现的缺失项、模糊项和反复返工项。
- 自动执行低风险动作：只读扫描、备份、报告、候选项去重。
- 所有持久行为变更仍需人工确认。

治理规则：

- 低风险：自动处理。
- 中风险：生成建议，等待确认或遵循用户预设策略。
- 高风险：必须解释风险、收益和回滚方案。

输入：

- work contracts。
- role profiles。
- candidate learning ledger。
- capability asset inventory。
- 本地策略配置。

输出：

- governance report。
- low-risk maintenance log。
- pending action list。

验收标准：

- 报告能回答：工作契约是否清晰、角色做了什么、学到了什么、有哪些能力、哪些可能有风险、哪些建议处理。
- 没有任何未经确认的全局规则、skill、plugin、MCP、role profile 修改。
- 低风险动作有记录，可审计。

退出条件：

- 至少完成去重、过期标记、风险标记、工作契约改进建议、角色改进建议五类治理输出。
- 至少能输出一类 question strategy 改进建议和一类 deliverable contract 改进建议。
- 报告能被用户用于决定下一步处理动作。

下一阶段前置条件：

- capability resolution 的决策枚举和证据格式已确定。

## 8. Phase 6：能力解析器与受控安装建议

目标：让系统能判断“缺的是知识、流程，还是工具能力”。

核心能力：

- 本地能力优先检索。
- 外部能力只做发现和评分，不默认安装。
- 生成 `reuse`、`configure`、`install_suggested`、`create_local`、`merge`、`ignore` 决策建议。
- 建立质量评分和风险评分雏形。
- 将建议关联到工作契约、交付物验收结果和角色能力包。

关键接口：

- Capability Resolution：`candidate_id`、`contract_id`、`role_id`、`decision`、`matched_assets`、`external_options`、`risk_level`、`recommended_action`。
- Decision：`reuse`、`configure`、`install_suggested`、`create_local`、`merge`、`ignore`。

输入：

- candidate learning item。
- work contract capability pack。
- role capability pack。
- capability asset inventory。
- 本地和外部能力索引。

输出：

- capability resolution report。
- install suggestion。
- create-local suggestion。
- work contract pack update suggestion。
- role pack update suggestion。

验收标准：

- 同一个能力缺口能先查本地，再给外部建议。
- 高风险外部代码不会自动安装。
- 每条建议都有证据和理由。
- 能区分“需要补问流程问题”和“需要补工具能力”的两类缺口。

退出条件：

- 至少支持本地能力匹配和一个外部来源的只读发现。
- 决策建议可被后续受控修改阶段消费。

下一阶段前置条件：

- backup、diff、audit、rollback 的最小数据模型已确定。

## 9. Phase 7：受控修改与回滚机制

目标：进入受控修改，但保持本地优先和可回滚。

核心能力：

- 修改前自动备份。
- 对 skill、rule、config、role profile、workflow playbook 生成 diff。
- 对 work contract template、question strategy、deliverable contract 生成 diff。
- 新规则或新角色流程先 project scope 或 quarantine scope 试运行。
- 支持回滚到上一版本。
- 记录审计日志。

输入：

- 用户确认的中高风险治理动作。
- capability resolution。
- 当前能力资产文件、角色文件和配置。
- 当前工作契约模板、提问策略和交付物契约。

输出：

- backup snapshot。
- planned diff。
- audit log。
- rollback command 或 rollback record。

验收标准：

- 每次 durable behavior change 都有 evidence、diff、backup、rollback。
- 修改失败可恢复。
- 修改后能运行最小验证。

退出条件：

- 支持至少一种文本能力文件和一种角色文件的受控修改与回滚。
- 支持至少一种工作契约模板或提问策略的受控修改与回滚。
- 审计日志能解释谁触发、为什么触发、改了什么、如何恢复。

下一阶段前置条件：

- runtime-neutral adapter contract 已确定。

## 10. Phase 8：跨工作契约、跨角色与跨 Agent Adapter

目标：从单工作契约、单角色、单 agent 走向 runtime-neutral。

核心能力：

- Codex adapter 稳定化。
- 增加 Claude Code / Hermes adapter 设计或原型。
- 提供 MCP server，并保留 CLI 查询接口。
- 让 agent 能按 workspace、任务类型、工作契约、角色、工具调用查询相关学习项和能力资产。
- 支持角色切换和多角色接力。
- 插件、skill 或 extension 只作为 adapter / distribution 形态，不承载核心业务逻辑。

关键接口：

- Query Contract：按 `workspace`、`status`、`deliverable`、`role` 查询工作契约。
- Query Role：按 `task`、`workspace`、`deliverable` 查询推荐角色。
- Query Learning：按 `workspace`、`contract_id`、`role`、`scope`、`type`、`confidence` 查询。
- Query Capability：按 `agent`、`contract_id`、`role`、`task`、`tool`、`risk` 查询。
- Submit Event：允许不同 agent 提交事件。

输入：

- 多 agent event sources。
- role profiles。
- work contracts。
- candidate learning ledger。
- capability asset inventory。

输出：

- adapter-normalized events。
- runtime query response。
- contract handoff record。
- role handoff record。
- MCP server。
- CLI 查询入口。
- agent adapter 原型。

验收标准：

- 核心模型不依赖某个 agent 的目录结构。
- 至少两个 agent 来源能进入同一 ledger。
- 运行时查询不会把原始事件直接塞进上下文。
- 至少一个场景能围绕同一工作契约完成市场研究员 -> 产品经理 -> 架构师的角色交接。
- 至少一个现有 agent 能通过 MCP 或 adapter 使用 Argus Core，而不是要求用户切换到独立 Argus agent。

退出条件：

- 至少一个非 Codex adapter 原型可提交事件或导入事件。
- CLI 或 MCP 查询接口能被真实 agent 工作流调用。
- 插件形态不破坏 runtime-neutral core 边界。

下一阶段前置条件：

- ROI 指标和 dashboard 信息架构已确定。

## 11. Phase 9：Dashboard、ROI 与维护任务

目标：让“工作契约、角色和 agent 是否变强”可见。

核心能力：

- 本地 dashboard 或等价 local web UI 展示工作契约、角色、学习项、能力资产、风险、使用趋势。
- 维护任务：去重、归档、过期、冲突检查、坏链路检查。
- 学习 ROI 指标：重复纠正减少、失败恢复时间、能力复用次数、风险事件数。
- 工作契约 ROI 指标：需求完整率、追问轮次、契约变更次数、交付物一次通过率、返工原因归因。
- 角色 ROI 指标：提问轮次、需求完整率、返工率、交付物接受率、角色复用次数。
- 交付物验收器：对照 work contract 输出通过、部分通过、不通过和缺失项。

输入：

- ledger。
- work contracts。
- role profiles。
- asset inventory。
- audit log。
- maintenance log。

输出：

- local dashboard 或 CLI report。
- ROI report。
- deliverable evaluation report。
- scheduled maintenance report。

验收标准：

- 用户能直观看到哪些工作契约模板、角色和学习有用。
- 长期不用或被替代能力能被发现。
- 报告不是泛泛总结，而是能指导角色和能力治理动作。
- 返工能反向归因到追问策略、契约模板、角色流程或能力包。

退出条件：

- 至少支持一个本地 dashboard 或等价 CLI report。
- ROI 指标可从真实样例数据计算。

下一阶段前置条件：

- 个人 Pro 版策略语言和安全边界已确定。

## 12. Phase 10：个人 Pro 版工作台

目标：把个人工具打磨成重度 AI 用户和 AI coding 用户愿意长期使用的产品。

核心能力：

- Desktop App 或 Local Web UI。
- Work Contract Console。
- Personal Playbook Registry。
- Role Pack Registry。
- 工作契约版本历史。
- 工作契约模板发布、回滚和复用。
- 个人追问策略、确认点和交付物结构沉淀。
- 策略自动化配置。
- 可信来源能力自动安装策略。
- 项目级规则、工作契约模板和角色流程自动更新策略。
- 本地能力版本锁定。
- 更完整的 supply-chain 和 prompt-injection 扫描。

输入：

- 用户策略。
- trusted registry。
- role capability pack。
- capability resolution。
- audit history。

输出：

- local app / local web workspace。
- policy-driven automation。
- version lock file。
- security scan report。
- work contract template release。
- personal playbook release。
- role pack release。

验收标准：

- 用户可以不用记 CLI 命令，通过个人工作台查看和管理工作契约、playbook、角色和策略。
- 用户能配置自动化边界，而不是逐条审批。
- 用户能把反复成功的工作契约沉淀成自己的 playbook。
- 中风险动作可批量处理。
- 高风险动作仍显式确认。

退出条件：

- 策略系统至少覆盖可信纯文本 skill、项目级规则、工作契约模板更新、角色流程更新、已安装 MCP 启用五类动作。
- 版本锁定和风险报告可被回滚机制使用。

下一阶段前置条件：

- 团队权限、审计和共享策略模型已进入 PRD。

## 13. Phase 11：团队版工作契约与能力治理平台

目标：扩展到团队 agent enablement 和 capability governance。

核心能力：

- 团队 Web App 或 SaaS 形态。
- 团队 work contract catalog。
- 团队 work contract templates。
- 团队 role catalog。
- 团队 capability inventory。
- 多用户权限和审计。
- repo-specific agent onboarding。
- 团队共享 skill / MCP / plugin / role policy。
- 组织级默认规则与例外机制。
- 团队能力使用统计和风险报告。

输入：

- 组织成员和权限。
- 团队仓库。
- 共享角色和能力资产。
- 共享工作契约模板。
- 组织策略。

输出：

- team web workspace。
- team work contract catalog。
- team role catalog。
- team work contract templates。
- team inventory。
- organization policy。
- audit report。
- repo onboarding pack。

验收标准：

- 团队能知道有哪些工作契约、工作契约模板和角色、装了什么能力、谁启用的、为什么启用、是否有效、如何回滚。
- 策略可按组织、团队、仓库、用户分层。
- 审计链路能支撑安全和合规讨论。

退出条件：

- 至少一个团队仓库能生成 onboarding pack。
- 团队策略能覆盖共享工作契约模板、共享角色、共享能力安装、禁用和例外。

下一阶段前置条件：

- adapter SDK 和多 registry 生命周期治理进入技术设计。

## 14. Phase 12：AI Work Contract & Capability Operating System

目标：形成长期基础设施形态。

核心能力：

- runtime-neutral Argus Core。
- 完整 work contract lifecycle management。
- 完整 personal playbook lifecycle management。
- 完整 role lifecycle management。
- 完整 capability lifecycle management。
- 多 registry 能力发现。
- 自动生成、修改、合并、隔离工作契约模板、角色和能力。
- 学习效果反馈闭环。
- 更强的 adapter SDK。
- 团队级治理、审计、回滚、供应链安全。

输入：

- 跨 agent ledger。
- work contract templates。
- personal playbooks。
- role catalog。
- 多 registry 能力目录。
- 策略系统。
- 团队审计和 ROI 数据。

输出：

- runtime-neutral work contract, personal playbook, role, and capability lifecycle platform。
- adapter SDK。
- governance automation。
- supply-chain security layer。

验收标准：

- Argus 不再只是报告工具，而是 AI 工作契约与能力操作系统雏形。
- 自动成长可追踪、可验证、可治理、可回滚。
- 核心价值不绑定单一 agent、单一 skill 格式或单一 MCP 市场。

退出条件：

- 核心工作契约、个人 playbook、角色和能力生命周期动作均有策略、审计、回滚和效果度量。
- 新 agent 可以通过 adapter SDK 接入事件、查询、工作契约、角色和能力资产治理。
- Argus 可以被 CLI、MCP、插件、桌面 App 和团队 Web 平台复用，但核心价值不依赖任何单一入口形态。

## 15. 跨阶段测试策略

每个阶段都必须有四类验证：

- Unit Tests：数据模型、解析器、评分器、策略判断。
- Fixture Tests：用固定工作契约对话、契约 diff、交付物验收样例、角色对话、transcript、skill manifest、MCP config 验证稳定输出。
- Integration Tests：从真实样例输入生成工作契约、角色交付物、ledger、inventory、report 和验收结果。
- Acceptance Tests：按阶段验收标准手动或自动确认。

MVP 到个人版阶段的最小测试样例：

- 一个模糊意图到工作契约再到 PRD 的追问对话。
- 一个工作契约变更和 diff 样例。
- 一个交付物缺失验收标准的失败样例。
- 一个成功会话 transcript。
- 一个命令失败后修复的 transcript。
- 一个用户明确纠正 agent 的 transcript。
- 一个本地 skill / plugin / MCP 混合资产目录。
- 一个重复能力或冲突能力样例。

## 16. 当前默认假设

- 采用统一 `docs/` 目录组织方式。
- 第一版路线图采用阶段级粒度，MVP 和个人版早期阶段后续再拆细。
- `DESIGN.md` 继续作为长期产品判断入口，不承担开发任务管理。
- 当前优先个人本地追问模式工作契约，不提前实现团队后台。
- Phase 1 产品形态采用 CLI + 本地文件存储，不做独立 agent、不做插件、不做 App。
- Argus Core 是原项目的能力治理与自动学习底座。
- Argus Core 是长期本体；CLI、MCP server、插件、Desktop App、Web App 都是入口或体验层。
- Work Contract Engine 是面向中重度 AI 产出者的产品入口。
- Completeness Score、Question Budget、Contract Diff、Deliverable Evaluator、Execution Evidence 和 Reverse Learning 是工作契约主线的长期差异化机制。
- 角色是能力组合和工作模式的一种形态，不是唯一中心。
- 所有外部安装、全局规则修改、删除能力资产、自动修改工作契约模板或角色流程都默认视为高风险动作。
- 短期可以 Codex-first，但核心模型必须保持 runtime-neutral。
