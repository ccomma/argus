# Phase 8: Cross-Agent Adapter, MCP Server & Role Handoff

## Phase

Phase 8 — Cross-Agent Adapter, MCP Server & Role Handoff.

## Branch

`phase8`

## Scope

Move Argus from single-agent to multi-agent runtime-neutral architecture:
- Agent adapter contract (BaseAdapter ABC + CodexAdapter + ClaudeAdapter)
- MCP server (stdlib JSON-RPC 2.0 over stdio)
- CLI query commands (contract list, packs list, roles list, query group)
- Role handoff records (HandoffRecord + HandoffManager)
- QueryApplication for unified cross-cutting read queries

## Key Artifacts

| Artifact | Path |
| --- | --- |
| Adapter contract | `src/argus/adapter/base.py` |
| Codex adapter | `src/argus/adapter/codex.py` |
| Claude adapter | `src/argus/adapter/claude.py` |
| MCP server | `src/argus/mcp/server.py` |
| Handoff models | `src/argus/handoff/models.py` |
| Handoff manager | `src/argus/handoff/manager.py` |
| Query application | `src/argus/application/query.py` |
| CLI commands | `src/argus/cli.py` (modified) |
| Paths | `src/argus/paths.py` (modified) |

## Validation

```bash
python -m unittest discover tests/ -v
```

Last result: 103 tests passed (69 existing + 32 Phase 8 + 2 structure).
