# Phase 4: 能力包与角色组合 技术设计

> 上下文加载：新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本技术设计。本文件是 schema 和接口的权威参考。

## 1. 概述

Phase 4 在 Phase 3 资产清单之上增加带版本的能力包清单。能力包通过资产 ID 引用已扫描的资产，并保留快照元数据用于审计和偏差检查。

## 2. 组件

- `CapabilityPackManifest`：持久化清单，存储于 `.argus/capability-packs/<pack_id>/<version>.json`。
- `CapabilityPackEntry`：必选或可选的资产引用，包含选择理由和快照。
- `CapabilityPackStore`：带版本的清单持久化和内容哈希。
- `CapabilityPackChecker`：将清单快照与当前资产清单进行比对，不产生任何修改。
- `CapabilityPackBindingStore`：将具体的包版本/哈希绑定到工作契约。
- `RolePackStore`：存储角色能力包，路径为 `.argus/role-packs/<role_id>/<version>.json`。
- `CapabilityPackAdvisor`：报告缺失的必选能力名称和重复的资产分组。

## 3. 清单 Schema

必填字段：

- `manifest_schema_version`
- `pack_id`
- `version`
- `display_name`
- `entries`
- `aggregate_risk_tier_snapshot`
- `aggregate_risk_reason_snapshot`
- `aggregate_reason_codes_snapshot`
- `aggregate_contributing_entry_ids_snapshot`
- `risk_policy_version`
- `created_at`
- `created_by`

条目存储内容：

- 稳定的 `entry_id`
- `asset_id`
- `required`
- `primary_purpose`
- `selection_rationale`
- 资产身份快照
- `permissions_snapshot`
- `asset_snapshot_hash`
- 风险原因和等级快照

## 4. 哈希

内容哈希采用 SHA-256，基于排序键和紧凑分隔符的规范 JSON 进行计算。哈希值在清单体外部报告和引用，以避免自引用哈希。

## 5. 风险策略

风险推断使用内置 `risk-policy-v1`：

- `reads_files`：低
- `writes_files`：中
- `executes_commands`：中
- `network_access`：高
- `changes_agent_behavior`：高
- `uses_secrets`：严重
- `external_service`：高
- `unknown`：中

聚合风险取所有包含条目中的最高风险等级。

## 6. 工作契约绑定

`contract bind-pack` 解析具体清单和内容哈希，然后记录：

- `contract_id`
- `contract_version`
- `pack_id`
- `pack_version`
- `content_hash`
- `rationale`
- `bound_at`

工作契约同时存储 `capability_pack_ref`（格式为 `<pack_id>@<version>#<content_hash>`），并追加 `capability_pack_bound` 执行证据。

## 7. 角色包设计

角色包引用能力包的标识和版本，而非内联资产条目。角色检查复用能力包检查逻辑。

这种设计将角色组合与资产清单细节解耦，并保持能力包在工作契约和角色之间的可复用性。

## 8. CLI

- `packs propose`
- `packs create`
- `packs inspect`
- `packs check`
- `packs advise`
- `contract bind-pack`
- `roles create-pack`
- `roles inspect-pack`
- `roles check-pack`

## 9. 非目标

- 自动安装。
- 自动修复。
- 嵌套包。
- 远程注册表。
- 用户可配置的风险策略。
- 完整的治理审批流程。

## 10. 失败模式

- 必选资产缺失：能力包检查不完整。
- 必选资产偏差：能力包检查不完整。
- 可选资产偏差：单独报告，不阻塞整个包。
- 缺失能力包或角色清单：CLI 报错退出。
