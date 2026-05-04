# Phase 1 Acceptance

## Acceptance Criteria

- [x] Can start from a vague intent.
- [x] Can generate clarifying questions from a question strategy.
- [x] Can produce a work contract with goal, context, inputs, outputs, constraints, risks, confirmation points, acceptance criteria, and completion definition.
- [x] Can compute a completeness score with explainable missing fields.
- [x] Can store contract JSON and Markdown locally.
- [x] Can preserve contract versions.
- [x] Can render a structured deliverable from a contract.
- [x] Can evaluate a deliverable against required sections and acceptance criteria.
- [x] Can write execution evidence without modifying external agent capabilities.

## Verification Evidence

Historical closeout command set:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall -q src tests
git diff --check
```

Result:

- Phase 1 tests passed before merge.
- Phase 1 was committed as `063b5af Implement Phase 1 work contract MVP`.
- Later full-suite checks continued to cover Phase 1 and passed during Phase 3 closeout.

## Final Artifacts

- Code: `src/argus/contracts.py`, `src/argus/core.py`, `src/argus/deliverables.py`, `src/argus/storage.py`, `src/argus/rendering.py`, `src/argus/cli.py`
- Tests: `tests/test_phase1_core.py`, `tests/test_phase1_contract_flow.py`, `tests/test_phase1_cli.py`
- Runtime output: `.argus/contracts/<contract-id>/`
- Commit: `063b5af Implement Phase 1 work contract MVP`

## Remaining Risks

- Completeness scoring is intentionally heuristic.
- First CLI is local and non-interactive enough for MVP, but not yet a polished user-facing app.
- Deliverable evaluation is structural and rule-based; it does not yet reason deeply about content quality.
