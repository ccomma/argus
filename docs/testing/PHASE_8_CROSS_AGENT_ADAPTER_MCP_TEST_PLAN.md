# Phase 8: 跨 Agent 适配器与 MCP 服务 Test Plan

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本测试计划。当前验收状态写入阶段目录的 `ACCEPTANCE.md`。

## 1. Scope

本测试计划覆盖：

- CodexAdapter 的 normalize_event、submit_event、ingest_transcript 完整链路
- ClaudeAdapter 的 Claude 特有字段映射（type->event_type、message->evidence、session_id->session）
- HandoffManager 的交接记录创建、加载、按合同/角色筛选和多角色交接链
- HandoffRecord 的内容寻址确定性 ID
- MCPServer 的 JSON-RPC 2.0 协议握手（initialize/initialized）、tools/list、tools/call、错误处理
- MCPServer 的 10 个注册工具：query_contracts、query_roles、query_packs、query_learnings、query_assets、check_role、run_resolution、handoff_role、submit_event、list_handoffs
- CLI 合同/角色/能力包/查询命令（contract list、packs list、roles list、query contract、query role）
- MCP 服务命令行启动（argus.mcp 和 argus.cli mcp-serve）

不覆盖：

- 实时转录流式摄入
- MCP 客户端并发连接
- 超大转录文件的性能边界

## 2. Fixtures

固定样例：

- Codex 风格原始事件字典（session/timestamp/event_type/evidence）：验证标准化和提交
- Claude 风格原始事件字典（type/session_id/timestamp/message）：验证字段映射兼容
- 单行 JSONL 转录文件：验证 ingest_transcript 批量导入
- 交接记录（researcher->pm->architect->engineer 四角色链）：验证多角色筛选和链式交接

## 3. Unit Tests

- `test_base_adapter_is_abstract`：BaseAdapter 不可直接实例化（TypeError）
- `test_codex_adapter_has_agent_name`：CodexAdapter.agent_name == "codex"
- `test_codex_adapter_normalizes_event`：标准化后 agent/source/event_type 正确映射
- `test_claude_adapter_has_agent_name`：ClaudeAdapter.agent_name == "claude"
- `test_claude_adapter_normalizes_claude_event_type_field`：Claude 的 "type" 字段映射为 event_type，"message" 字段内容提取为 evidence
- `test_claude_adapter_normalizes_event_with_event_type_fallback`：当 "type" 缺失时回退到 "event_type"，session 回退到 "session_id"
- `test_handoff_record_creates_deterministic_id`：相同输入产生相同 handoff ID
- `test_handoff_record_different_inputs_different_ids`：不同输入产生不同 ID

## 4. Fixture Tests

- `test_codex_adapter_ingests_transcript_fixture`：单行 JSONL 转录文件被 CodexAdapter 正确导入，事件 source 为 "codex_transcript"
- `test_claude_adapter_ingests_transcript`：单行 JSONL 转录文件被 ClaudeAdapter 正确导入，事件 source 为 "claude_adapter"
- `test_manager_creates_and_loads_handoff`：HandoffManager 创建 record 后 load 可获取完整字段（context.notes 等）
- `test_manager_lists_by_contract`：按合同筛选只返回该合同的交接记录
- `test_manager_lists_by_role`：按角色筛选返回该角色作为 from 或 to 的所有记录
- `test_manager_supports_multi_role_handoff_chain`：四角色链（researcher->pm->architect->engineer）完整创建并可通过 list_all 获取

## 5. Integration Tests

- `test_codex_adapter_submits_event_to_ledger`：normalize_event + submit_event 后 EventLedger 中可列出该事件
- `test_initialize_handshake_returns_protocol_version_and_capabilities`：MCP initialize 返回 "2024-11-05" 协议版本和 tools capabilities
- `test_initialized_notification_returns_none`：notifications/initialized 方法返回 None（通知无需响应）
- `test_tools_list_returns_all_registered_tools`：tools/list 返回 10 个已注册工具名称的超集
- `test_tools_call_unknown_tool_returns_error`：未知工具返回 -32601 错误码
- `test_query_contracts_tool_returns_empty_list`：空库下 query_contracts 返回 total=0
- `test_submit_event_and_query_learnings`：submit_event 写入后 query_learnings 可获取结果
- `test_handoff_role_tool_creates_record`：handoff_role 工具创建记录后 list_handoffs 可验证
- `test_unknown_method_returns_error`：未知 JSON-RPC method 返回 -32601 错误码
- `test_mcp_server_cli_startup`：`python -m argus.mcp --store` 启动后通过 stdio 完成 initialize 握手

## 6. Acceptance Tests

- CLI 合同/角色/能力包 list 命令输出 JSON 数组
- CLI query contract/role 命令带 --store 参数返回匹配结果
- MCP 服务通过标准输入输出完成完整的 JSON-RPC 2.0 交互循环
- Codex 和 Claude 两种 Agent 来源的转录数据均可被正确适配入库

## 7. Regression Risks

- MCP 服务静默丢失 JSON 解析错误（当前静默跳过非法 JSON 行）
- 适配器字段回退逻辑被破坏：event_type 和 session 的回退链（type->event_type、session_id->session）测试覆盖
- 交接记录文件目录不存在时崩溃：_list_filtered 返回空列表的容错设计

## 8. Test Commands

```bash
PYTHONPATH=src python -m pytest tests/test_phase8_adapter.py tests/test_phase8_handoff.py tests/test_phase8_mcp.py tests/test_phase8_cli.py -v
PYTHONPATH=src python -m unittest tests.test_phase8_adapter.Phase8AdapterTest tests.test_phase8_handoff.Phase8HandoffTest tests.test_phase8_mcp.Phase8MCPTest tests.test_phase8_cli.Phase8CLITest
```
