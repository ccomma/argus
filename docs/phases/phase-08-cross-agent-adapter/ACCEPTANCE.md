# Phase 8 Acceptance

## Acceptance Criteria

| Criterion | Status |
| --- | --- |
| Core models don't depend on any agent's directory structure | PASS — BaseAdapter is agent-agnostic |
| At least two agent sources can enter the same ledger | PASS — CodexAdapter + ClaudeAdapter |
| Runtime queries don't dump raw events into context | PASS — QueryApplication returns structured dicts |
| At least one scenario: researcher → pm → architect handoff | PASS — test_manager_supports_multi_role_handoff_chain |
| At least one existing agent can use Argus Core via MCP | PASS — MCP server over stdio with 10 tools |
| CLI or MCP query interface usable by real agent workflows | PASS — CLI + MCP both functional |
| Plugin form doesn't break runtime-neutral core boundary | PASS — no agent-specific code in core |

## Exit Conditions

| Condition | Status |
| --- | --- |
| At least one non-Codex adapter prototype (Claude) | PASS — ClaudeAdapter ingests Claude transcripts |
| CLI query commands functional | PASS — contract list, packs list, roles list, query |
| MCP server query interface functional | PASS — stdio JSON-RPC 2.0 with 10 tools |

## Tests

```bash
python -m unittest discover tests/ -v
```

103 tests passed, no regressions.

## Commands

```bash
# Start MCP server
python -m argus.mcp --store .argus
python -m argus.cli mcp-serve --store .argus

# Query commands
python -m argus.cli contract list --store .argus
python -m argus.cli packs list --store .argus
python -m argus.cli roles list --store .argus
python -m argus.cli query contract <id> --store .argus
python -m argus.cli query role <id> --store .argus
```

## Final Commit

`<commit>`
