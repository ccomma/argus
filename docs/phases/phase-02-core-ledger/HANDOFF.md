# Phase 2 Handoff: Argus Core Ledger

## Load Order

1. Read this file for Phase 2 historical context.
2. Read `docs/prd/PHASE_2_ARGUS_CORE_LEDGER_PRD.md` only when product acceptance details are needed.
3. Read `docs/technical/PHASE_2_ARGUS_CORE_LEDGER_TECHNICAL_DESIGN.md` only when ledger model or interface details are needed.
4. Read `docs/testing/PHASE_2_ARGUS_CORE_LEDGER_TEST_PLAN.md` only when test intent is unclear.

## Branch And Policy

- Phase branch: `phase2`
- Final branch commit: `b9cf460 refactor: clean up phase 2 ledgers`
- Mainline merge: `9d76501 Merge Phase 2 ledger refactor`
- Phase branch is retained after merge.

## Current Phase

- Phase: Phase 2, Argus Core event and candidate learning ledger.
- Goal: prove work contracts and transcripts can become append-only events, and events can become candidate learnings without polluting long-term behavior.
- In scope: event record schema, JSONL ledger, transcript ingestion, contract evidence ingestion, candidate learning extraction, learning report.
- Out of scope: capability inventory, capability modification, external installation, global memory/rule writes.

## Key Artifacts

- Product doc: `docs/prd/PHASE_2_ARGUS_CORE_LEDGER_PRD.md`
- Technical doc: `docs/technical/PHASE_2_ARGUS_CORE_LEDGER_TECHNICAL_DESIGN.md`
- Test plan: `docs/testing/PHASE_2_ARGUS_CORE_LEDGER_TEST_PLAN.md`
- Main code: `src/argus/ledger.py`, `src/argus/learning.py`, `src/argus/ingestion.py`, `src/argus/jsonl.py`, `src/argus/paths.py`, `src/argus/cli.py`
- Main tests: `tests/test_phase2_ledger.py`, `tests/test_phase2_cli.py`

## Verification Commands

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall -q src tests
git diff --check
```

## Final State

Phase 2 is complete. It established append-only event and candidate learning ledgers, transcript ingestion, contract evidence ingestion, learning extraction, and local reports.

## Context Budget Rule

Use this handoff for historical Phase 2 context. Do not load all Phase 2 long-form docs unless a current task needs their details.
