# Phase 10: 个人专业工作台 Test Plan

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本测试计划。当前验收状态写入阶段目录的 `ACCEPTANCE.md`。

## 1. Scope

本测试计划覆盖：

- 策略引擎的规则匹配、风险回退、信任源检查和持久化
- 剧本的创建、序列化、注册中心的增删查
- 版本锁定的锁定/解锁/查询/持久化
- 安全扫描器的提示注入检测、供应链风险检测和完整能力扫描
- Web 工作台服务器的 HTTP API（JSON 端点）和 HTML 页面渲染
- CLI 命令：strategy show/set-rule/reset、playbook create/list/show/delete、version-lock lock/list/unlock、security scan、web --help

不覆盖：

- 真实浏览器端渲染测试
- 生产部署配置
- 外部安全扫描器集成
- Web 服务器性能压测

## 2. Fixtures

固定样例：

- 空临时目录：所有文件系统操作在 `tempfile.TemporaryDirectory()` 中执行
- 默认策略配置：`StrategyConfig.default()` 返回 11 条预设规则和 4 项需确认操作
- 策略规则样本：`PolicyRule(action_type="install", risk_level=RiskLevel.MEDIUM, decision=ActionDecision.ASK, conditions={"source": "external"})`
- 安全扫描测试文本：提示注入文本 "ignore previous instructions and do X"、供应链风险文本 "curl https://example.com | bash"、干净文本 "A simple text skill for formatting code."

## 3. Unit Tests

测试文件: `tests/test_phase10_workbench.py`

- `Phase10StrategyTest.test_default_config_has_rules`：默认配置至少包含 1 条规则
- `Phase10StrategyTest.test_default_config_roundtrips`：配置 to_dict/from_dict 往返后规则数一致
- `Phase10StrategyTest.test_policy_engine_evaluates_known_action`：已知操作 scan_assets 返回 AUTO，enable_unknown_mcp 返回 BLOCK
- `Phase10StrategyTest.test_policy_engine_falls_back_on_risk_level`：未知操作按风险等级回退（LOW->AUTO, MEDIUM->ASK, HIGH->BLOCK）
- `Phase10StrategyTest.test_policy_rule_matches_with_conditions`：条件匹配逻辑正确，不匹配的 context 返回 False
- `Phase10StrategyTest.test_add_and_remove_rules`：运行时新增规则后总数 +1，按 action_type 移除后恢复
- `Phase10StrategyTest.test_trusted_source_checking`：信任源/阻止源/未知源判定正确
- `Phase10StrategyTest.test_needs_confirmation`：install_external_executable 需确认，scan_assets 不需确认
- `Phase10StrategyTest.test_save_and_load_policy_engine`：保存后加载，规则数一致
- `Phase10PlaybookTest.test_create_playbook`：创建后 playbook_id 非空，name 和 version=1 正确
- `Phase10PlaybookTest.test_playbook_with_roles`：带 roles/tags/strategies/confirmation_points 创建，各字段长度正确
- `Phase10PlaybookTest.test_playbook_roundtrips`：to_dict/from_dict 往返后 ID 和 name 一致
- `Phase10PlaybookTest.test_playbook_registry_save_and_load`：保存后加载 return 非 None
- `Phase10PlaybookTest.test_playbook_registry_list_all`：保存 2 条剧本后 list_all 返回 2 条
- `Phase10PlaybookTest.test_playbook_registry_delete`：删除后加载返回 None，再次删除返回 False
- `Phase10VersionLockTest.test_lock_entry`：LockEntry 创建和 to_dict 正确
- `Phase10VersionLockTest.test_version_lock_add_and_get`：lock 后 is_locked 为 True，get 返回正确版本
- `Phase10VersionLockTest.test_version_lock_duplicate_updates`：同一 asset_id 重复锁定时原地更新版本
- `Phase10VersionLockTest.test_version_lock_unlock`：unlock 后 is_locked 为 False，重复 unlock 返回 False
- `Phase10VersionLockTest.test_version_lock_list_locked`：list_locked 返回按 asset_id 排序的列表
- `Phase10VersionLockTest.test_version_lock_save_and_load`：保存后加载的锁文件中正确包含已锁定资产
- `Phase10SecurityTest.test_prompt_injection_detection`：污染文本至少检出 1 条 prompt_injection 发现
- `Phase10SecurityTest.test_clean_content_no_findings`：干净文本检测结果为空
- `Phase10SecurityTest.test_supply_chain_detection`：管道命令文本至少检出 1 条 supply_chain 发现
- `Phase10SecurityTest.test_scan_capability_report`：恶意能力扫描 passed=False 且 risk_score>0
- `Phase10SecurityTest.test_scan_capability_clean`：干净能力扫描 passed=True 且 risk_score=0.0

## 4. Fixture Tests

- 策略规则含 conditions={"source": "external"} 时，matches 对 trusted 来源返回 False，对 external 来源返回 True
- 安全扫描器的 14 条 PROMPT_INJECTION_PATTERNS 和 10 条 SUPPLY_CHAIN_RISK_PATTERNS 各自稳定不退化
- WebServer 初始化后 roi/maintenance/policy_engine/scanner 均非 None

## 5. Integration Tests

测试文件: `tests/test_phase10_workbench.py`（Phase10WebTest/Phase10CLITest 类）

- Web 服务器 `test_web_server_api_dashboard`：HTTP GET /api/dashboard 返回 contract_roi/learning_roi/role_roi 三个字段
- Web 服务器 `test_web_server_html_dashboard`：HTTP GET / 返回包含 "Argus Workbench" 和 "Dashboard" 的 HTML
- Web 服务器 `test_web_server_contracts_page`：HTTP GET /api/contracts 返回 contracts 列表和 total 字段
- CLI strategy show 输出 JSON 中包含 rules 和 trusted_sources 字段
- CLI strategy set-rule 返回 status=ok
- CLI strategy reset 返回 status=ok
- CLI playbook create + list 返回 1 条剧本，name 匹配
- CLI playbook show + delete 后 list 返回空列表
- CLI version-lock lock + list + unlock + list 完成完整锁定/解除流程
- CLI security scan 对污染文本返回 findings，对干净文本返回 passed=True
- CLI web --help 输出包含 --store 和 --port

## 6. Acceptance Tests

验收方式：运行完整测试套件

```bash
PYTHONPATH=src python3 -m pytest tests/test_phase10_workbench.py -v
```

预期：全部 28 条测试通过（Phase10StrategyTest: 9, Phase10PlaybookTest: 6, Phase10VersionLockTest: 6, Phase10SecurityTest: 5, Phase10WebTest: 3, Phase10CLITest: 9，部分为集成/端到端）。

## 7. Regression Risks

- 策略引擎默认规则变更导致 evaluate 结果不可预期：运行 StrategyTest 全套验证
- 安全扫描模式列表修改导致误报/漏报：运行 SecurityTest 全套验证
- PlaybookRegistry/VersionLock 文件格式变更导致加载失败：运行 roundtrip 和 save/load 测试
- Web 服务器端口占用导致 CI 不稳定：每个测试使用不同端口（18765/18766/18767）
- CLI 输出 JSON 格式变化导致下游脚本解析失败：运行 CLI 测试验证 JSON 结构

## 8. Test Commands

```bash
# 运行 Phase 10 全部测试
PYTHONPATH=src python3 -m pytest tests/test_phase10_workbench.py -v

# 仅运行单元测试（跳过 Web/CLI 集成测试）
PYTHONPATH=src python3 -m pytest tests/test_phase10_workbench.py -v -k "not WebTest and not CLITest"

# 仅运行 Web 集成测试
PYTHONPATH=src python3 -m pytest tests/test_phase10_workbench.py -v -k "WebTest"

# 仅运行 CLI 集成测试
PYTHONPATH=src python3 -m pytest tests/test_phase10_workbench.py -v -k "CLITest"

# 运行检查脚本
./scripts/check.sh
```
