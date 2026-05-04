# Phase 2 Acceptance

## Acceptance Criteria

- [x] Can represent event records with agent, workspace, session, timestamp, event type, evidence, and risk metadata.
- [x] Can append events to a local JSONL ledger.
- [x] Can ingest Phase 1 contract evidence.
- [x] Can ingest a Codex transcript fixture.
- [x] Can distinguish raw events from candidate learning items.
- [x] Can extract candidate learnings with summary, type, scope, confidence, evidence refs, reverse learning target, and status.
- [x] Can write a local learning report.
- [x] Does not automatically modify memory, skills, rules, plugins, MCP config, or global agent configuration.

## Verification Evidence

Historical closeout command set:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall -q src tests
git diff --check
```

Result:

- Phase 2 tests passed before merge.
- Phase 2 implementation landed in `80a4b6c Implement Phase 2 learning ledger`.
- Phase 2 cleanup landed in `b9cf460 refactor: clean up phase 2 ledgers`.
- Mainline merge is `9d76501 Merge Phase 2 ledger refactor`.
- Later full-suite checks continued to cover Phase 2 and passed during Phase 3 closeout.

## Final Artifacts

- Code: `src/argus/ledger.py`, `src/argus/learning.py`, `src/argus/ingestion.py`, `src/argus/jsonl.py`, `src/argus/paths.py`, `src/argus/cli.py`
- Tests: `tests/test_phase2_ledger.py`, `tests/test_phase2_cli.py`
- Fixture: `tests/fixtures/codex_mixed_events.jsonl`
- Runtime output: `.argus/ledger/events.jsonl`, `.argus/learning/candidates.jsonl`, `.argus/learning/reports/`
- Commit: `b9cf460 refactor: clean up phase 2 ledgers`

## Remaining Risks

- Transcript parsing is intentionally tolerant and fixture-led; future adapters may need stricter contracts.
- Candidate learning extraction is heuristic and should remain candidate-only until governance phases promote it.
- No runtime query interface exists yet.
