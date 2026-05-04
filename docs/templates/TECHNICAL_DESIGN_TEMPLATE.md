# Phase XX: <阶段名称> Technical Design

> Context loading: 新会话默认先读 `docs/context/CURRENT_HANDOFF.md`，再按需读取本技术设计。本文件回答模块、接口、数据和风险边界，不记录每日执行状态。

## 1. Overview

说明本阶段技术设计如何满足对应 PRD。

## 2. Architecture

描述模块边界和主要数据流。

## 3. Data Model

核心数据结构：

```text
<ModelName>
- field: description
```

## 4. Interfaces

CLI、API、文件输入输出或 MCP 接口：

```text
<interface example>
```

## 5. Storage

说明本阶段使用的存储格式、目录位置、读写边界和迁移策略。

## 6. Governance and Security

说明风险分级、权限边界、备份、审计和回滚要求。

## 7. Failure Modes

需要处理的失败模式：

- <失败模式 1>
- <失败模式 2>

## 8. Test Strategy

本阶段测试策略：

- Unit Tests：
- Fixture Tests：
- Integration Tests：
- Acceptance Tests：

## 9. Compatibility

说明是否影响已有文档、ledger、配置或外部 agent adapter。

## 10. Open Questions

- <问题 1>
