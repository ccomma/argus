# Phase 10: Personal Pro 工作台 PRD

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本 PRD。本文件只回答产品问题，不承担实现任务管理。

## 1. Background

Phase 9 用 CLI 报告证明了治理效果的可见性，但重度 AI 用户需要的是日常交互界面，而非每次手动运行命令。Phase 10 将 Argus 从 CLI 工具升级为个人 Pro 工作台：提供本地 Web UI、策略自动化引擎、个人剧本注册中心、能力版本锁定和安全扫描器，让用户不用记命令即可管理合约、角色、能力和安全策略。这是 roadmap 中"个人可用"阶段的收官之作，为 Phase 11 的团队扩展奠定基础。

## 2. Users and Jobs

目标用户：

- 每日使用 AI coding agent 的重度开发者，需要随时查看和管理治理状态。
- 希望将反复成功的合约和流程沉淀为个人剧本的个人用户。
- 需要对能力资产的来源、版本和安全性有精细控制的专业用户。

用户任务：

- 在浏览器中访问本地 Web 工作台，查看 Dashboard、合约、角色、能力包、资产、学习、维护、策略、剧本和交接记录。
- 配置自动化策略边界：哪些操作自动执行，哪些需要确认，哪些直接阻止。
- 创建和管理个人剧本（playbook），将成功的合约流程模板化。
- 锁定关键能力的精确版本，防止上游变更导致不兼容。
- 扫描外部能力内容中的提示注入和供应链风险。

## 3. Problem

当前问题：

- 所有治理操作依赖 CLI 命令和文件路径，使用门槛高，无法快速浏览全貌。
- 策略自动化规则分散在用户心智中，没有系统化的配置和持久化机制。
- 反复成功的合约模板无法沉淀复用，每次需要重新开始。
- 能力资产的版本变更不受控，上游更新可能引入不兼容或安全风险。
- 外部来源的能力内容（skill、rule、MCP config）缺乏安全扫描机制。

## 4. Goals

- 提供本地 Web 工作台（HTTP 服务器，127.0.0.1:8765），包含 11 个 HTML 页面和 REST API。
- 实现策略自动化引擎（PolicyEngine），支持规则匹配、信任源管理、风险等级回退决策。
- 构建个人剧本注册中心（PlaybookRegistry），支持剧本的创建、查看、更新和删除。
- 实现能力版本锁定（VersionLock），同一资产重复锁定自动替换旧条目。
- 构建安全扫描器（SecurityScanner），覆盖提示注入检测（14 种模式）和供应链风险检测（10 种模式）。
- 浏览器内即可完成策略配置、剧本管理、版本锁定和安全扫描。

## 5. Non-goals

- 不做用户认证和登录系统（本地单用户场景）。
- 不做桌面 App 打包（Electron/Tauri），维持纯 Python HTTP 服务。
- 不做实时推送和 WebSocket 通知。
- 不做外部注册中心集成（Skillsmith、SkillHub 等），仅本地剧本注册。
- 不修改用户的能力资产文件（安全扫描只读分析）。

## 6. Core User Flows

核心流程 1 -- 浏览治理全貌：
1. 用户运行 `python -m argus.cli web --store .argus`。
2. WebServer 初始化所有依赖（存储、账本、库存、ROI 计算器、维护引擎、策略引擎、剧本注册中心、版本锁、安全扫描器）。
3. 浏览器打开 `http://127.0.0.1:8765`，显示 Dashboard 首页（统计卡片 + 三大 ROI 详情）。
4. 用户点击导航栏切换 Contracts/Roles/Packs/Assets/Learnings/Maintenance/Strategy/Playbooks/Handoffs/Security 页面。

核心流程 2 -- 配置自动化策略：
1. 用户进入 Strategy 页面，查看当前 11 条默认规则（从低风险的 scan_assets 自动执行到高风险的 enable_unknown_mcp 阻止）。
2. 用户通过 POST /api/strategy 提交自定义策略配置。
3. PolicyEngine 加载新配置，实时生效。
4. 策略持久化到 strategy.json。

核心流程 3 -- 沉淀个人剧本：
1. 用户在 Playbooks 页面通过 POST /api/playbooks 创建新剧本，填入名称、描述、提问策略、确认点、交付物模板、合约模板、角色和能力包清单。
2. PlaybookRegistry 保存为 {playbook_id}.json，SHA-1 哈希生成唯一 ID。
3. 用户在剧本列表中查看、删除已有剧本。

核心流程 4 -- 版本锁定与安全扫描：
1. 用户在 Web UI 中通过 POST /api/version-locks 锁定能力的精确版本（asset_id + version + source + reason），同一 ID 重复锁定自动替换。
2. 用户进入 Security 页面，粘贴能力内容到扫描表单，触发 POST /api/security/scan。
3. SecurityScanner 检测提示注入和供应链风险模式，返回 ScanReport（findings + risk_score + passed）。

## 7. Success Criteria

- 本地 Web 工作台可启动并访问 11 个 HTML 页面（Dashboard/Contracts/Roles/Packs/Assets/Learnings/Maintenance/Strategy/Playbooks/Handoffs/Security）。
- 每个页面展示对应数据（表格 + 统计卡片 + JSON 详情）。
- PolicyEngine 覆盖 11 条默认规则，支持 AUTO/ASK/BLOCK 三级决策和信任源/阻止源管理。
- PlaybookRegistry 支持剧本的完整 CRUD 操作，ID 基于 SHA-1 哈希生成。
- VersionLock 支持锁定/解锁/查询，同一 asset_id 重复锁定实现原地替换。
- SecurityScanner 扫描能力内容，输出提示注入和供应链风险发现，risk_score = min(1.0, findings * 0.15)。
- 工作台关闭（Ctrl+C）优雅退出。

## 8. Risks and Open Questions

风险：

- SecurityScanner 基于固定模式匹配，对变体攻击（大小写绕过、编码混淆）可能漏检。当前已做 lower() 大小写不敏感处理，但编码绕过仍是盲区。
- Playbook 创建时无冲突检测，同名剧本可能产生多个不同 ID 的条目。
- Web 工作台无并发保护，多标签页同时 POST 策略/剧本可能导致竞态条件（当前为单用户本地场景，风险可控）。

开放问题：

- 策略规则是否需要支持正则表达式或通配符匹配（当前仅支持精确 action_type 匹配）？
- 剧本的版本演进与合约模板的版本如何关联？当前剧本版本字段为独立版本号。
- 是否需要为 Web 工作台添加启动认证 token 以避免本地网络内的未授权访问？
