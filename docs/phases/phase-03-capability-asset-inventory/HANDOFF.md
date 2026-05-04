# Phase 3 Handoff: Capability Asset Inventory

## Purpose

Build the first personal local capability asset inventory for Argus.

Phase 3 proves Argus can inspect capability assets such as skills, plugins, MCP configs, rules, scripts, and memory without modifying them.

## Scope

In scope:

- Capability asset schema.
- Read-only scanners for local asset sources.
- Local inventory output.
- Asset scan report.
- Candidate learning to asset link report.
- Duplicate or suspicious overlap hints.

Out of scope:

- Installing external assets.
- Editing skills, plugins, MCP configs, rules, memory, or scripts.
- Deleting, disabling, archiving, or merging assets.
- Team governance.

## Current Implementation

Implemented and pushed on branch `phase3`:

- `src/argus/assets.py` compatibility exports.
- `src/argus/asset_models.py`
- `src/argus/asset_scanning.py`
- `src/argus/asset_inventory.py`
- `src/argus/asset_reporting.py`
- `src/argus/asset_linking.py`
- `src/argus/asset_text.py`
- `src/argus/cli.py`
  - `assets scan`
  - `assets list`
  - `assets report`
  - `assets link-learnings`
- `src/argus/paths.py`
  - `.argus/assets/inventory.json`
  - `.argus/assets/reports/`
- `tests/test_phase3_assets.py`
- `tests/fixtures/assets/`

## Current Validation

Final known passing commands:

```bash
./scripts/check.sh
```

Result:

- 28 tests passed.
- Compile check passed.
- Diff whitespace check passed.

The Phase 3 fixture scan discovers six asset types:

- skill
- plugin
- mcp_server
- rule
- script
- memory

The final `local-codex` smoke scans the current machine with:

```bash
PYTHONPATH=src python3 -m argus.cli assets scan --store /private/tmp/argus-phase3-closeout/.argus --profile local-codex
```

Result:

- 25 assets
- 0 warnings

## Design Boundary

Phase 3 is observe-only. It may write Argus inventory and reports under `.argus/`, but it must not modify any discovered capability source.

## Next Steps

1. Prepare Phase 4 capability pack and role-composition design.
2. Create `phase4` branch from `main`.
3. Keep Phase 4 read-only until capability pack semantics are proven.
