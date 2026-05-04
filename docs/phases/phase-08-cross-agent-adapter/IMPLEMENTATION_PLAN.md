# Phase 8 Implementation Plan

## Completed

1. Adapter contract (`BaseAdapter` ABC) — CodexAdapter wraps TranscriptIngestor, ClaudeAdapter reads Claude transcript JSONL
2. Role handoff (`HandoffRecord` + `HandoffManager`) — deterministic IDs, list by contract/role
3. QueryApplication — unified cross-cutting queries across contracts, packs, roles, learnings, assets
4. MCP server — stdio JSON-RPC 2.0, 10 tools: query_contracts, query_roles, query_packs, query_learnings, query_assets, check_role, run_resolution, handoff_role, submit_event, list_handoffs
5. CLI commands — `contract list`, `packs list`, `roles list`, `query contract <id>`, `query role <id>`, `mcp-serve`
6. Tests — 32 tests (9 adapter, 6 handoff, 10 MCP, 7 CLI)
7. Full regression — 103 tests passing
