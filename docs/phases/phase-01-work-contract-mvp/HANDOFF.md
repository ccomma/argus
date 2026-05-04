# Phase 1 Handoff: Work Contract MVP

## Load Order

1. Read this file for Phase 1 historical context.
2. Read `docs/prd/PHASE_1_WORK_CONTRACT_MVP_PRD.md` only when product acceptance details are needed.
3. Read `docs/technical/PHASE_1_WORK_CONTRACT_MVP_TECHNICAL_DESIGN.md` only when model or interface details are needed.
4. Read `docs/testing/PHASE_1_WORK_CONTRACT_MVP_TEST_PLAN.md` only when test intent is unclear.

## Branch And Policy

- Phase branch: `phase1`
- Final commit: `063b5af Implement Phase 1 work contract MVP`
- Phase branch is retained after merge.

## Current Phase

- Phase: Phase 1, Work Contract MVP.
- Goal: prove Argus can turn vague intent into a structured, reviewable work contract.
- In scope: local CLI, local file storage, question strategy, completeness score, deliverable rendering, deliverable evaluation, contract evidence.
- Out of scope: event learning ledger, capability inventory, external installation, global behavior changes, team features.

## Key Artifacts

- Product doc: `docs/prd/PHASE_1_WORK_CONTRACT_MVP_PRD.md`
- Technical doc: `docs/technical/PHASE_1_WORK_CONTRACT_MVP_TECHNICAL_DESIGN.md`
- Test plan: `docs/testing/PHASE_1_WORK_CONTRACT_MVP_TEST_PLAN.md`
- Main code: `src/argus/contracts.py`, `src/argus/core.py`, `src/argus/deliverables.py`, `src/argus/storage.py`, `src/argus/rendering.py`, `src/argus/cli.py`
- Main tests: `tests/test_phase1_core.py`, `tests/test_phase1_contract_flow.py`, `tests/test_phase1_cli.py`

## Verification Commands

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall -q src tests
git diff --check
```

## Final State

Phase 1 is complete. It established the local work contract data model, CLI flows, deliverable evaluation, versioned storage, and contract evidence output used by later phases.

## Context Budget Rule

Use this handoff for historical Phase 1 context. Do not load all Phase 1 long-form docs unless a current task needs their details.
