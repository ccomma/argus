# Phase 5 Handoff: Personal Governance Report

## Purpose

Generate a personal governance report that helps the user decide what to handle next across work contracts, role packs, candidate learnings, capability assets, and capability packs.

## Implemented Slice

- `src/argus/governance.py`
  - governance findings
  - pending actions
  - low-risk maintenance log
  - Markdown and JSON report output
- `src/argus/application.py`
  - `GovernanceApplication`
- `src/argus/cli.py`
  - `governance report`
- `src/argus/storage.py`
  - `list_contracts`
- `src/argus/capability_packs.py`
  - latest pack and role pack listing
- `tests/test_phase5_governance.py`

## Boundaries

In scope:

- Read-only governance reporting.
- Five finding categories: dedupe, stale, risk, work contract, role.
- Question strategy and deliverable contract improvement suggestions.
- Argus-owned report artifacts.

Out of scope:

- Installing, editing, archiving, disabling, deleting, or merging capability assets.
- Mutating role packs or capability packs.
- Scheduling.
- Team governance.

## Validation

Current passing command:

```bash
./scripts/check.sh
```

Result:

- 42 tests passed.
- Compile check passed.
- Diff whitespace check passed.

Smoke store:

```text
/private/tmp/argus-phase5-closeout/.argus
```

Smoke evidence:

- `assets scan --profile local-codex`: 48 assets, 0 warnings.
- `governance report`: wrote Markdown report, JSON report, low-risk log, and pending actions.
- JSON report summary: 48 assets, 7 findings, 7 pending actions, 2 low-risk log entries.

## Next Steps

1. Start Phase 6 on a new phase branch.
2. Define capability resolution decision enum and evidence schema.
3. Keep Phase 6 local-first and read-only before any install suggestion path.
