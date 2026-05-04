# Phase 3 Acceptance

## Acceptance Criteria

- [x] Can represent capability assets with name, type, source, version, install path, agents, scope, permissions, risk score, and status.
- [x] Can scan Codex-style skills.
- [x] Can scan Codex plugin manifests.
- [x] Can scan MCP config JSON.
- [x] Can scan local rule files.
- [x] Can scan local scripts.
- [x] Can scan local memory files.
- [x] Can write a local capability asset inventory.
- [x] Can write an asset scan report.
- [x] Can link candidate learnings to existing assets with evidence.
- [x] Can flag potential duplicate assets.
- [x] Can flag potential conflict groups.
- [x] Can show risky assets in the report.
- [x] Candidate-to-asset matching ignores generic capability words.
- [x] Scan behavior is read-only for source assets.
- [x] Default local scan profile is defined.
- [x] MCP config variants beyond JSON fixture are covered.
- [x] Risk scoring is documented and tested beyond the first heuristic.
- [x] Phase 3 PRD, technical design, and test plan are fully aligned with final implementation.

## Verification Evidence

Final local verification:

```bash
./scripts/check.sh
```

Result:

- 28 tests passed.
- Compile check passed.
- Diff whitespace check passed.

Local read-only smoke:

```bash
PYTHONPATH=src python3 -m argus.cli assets scan --store /private/tmp/argus-phase3-final-check/.argus --profile local-codex
```

Result:

- 25 assets scanned.
- 0 warnings.

## Final Artifacts

- Code: `src/argus/asset_models.py`, `src/argus/asset_scanning.py`, `src/argus/asset_inventory.py`, `src/argus/asset_reporting.py`, `src/argus/asset_linking.py`, `src/argus/asset_text.py`, `src/argus/assets.py`, `src/argus/cli.py`, `src/argus/paths.py`
- Tests: `tests/test_phase3_assets.py`, `tests/fixtures/assets/`
- Runtime output: `.argus/assets/inventory.json`, `.argus/assets/reports/`
- Commits: `761cf81 feat: add phase 3 capability inventory`, `1d45497 refactor: split capability asset modules`

## Remaining Risks

- Risk scoring is still heuristic and should not be treated as a security verdict.
- Duplicate and conflict detection is name/token based and may produce false positives or false negatives.
- Phase 3 is intentionally read-only; actual capability changes must wait for later governed phases.
