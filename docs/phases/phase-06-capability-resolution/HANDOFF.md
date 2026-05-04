# Phase 6 Handoff: Capability Resolution & Controlled Install Suggestions

## Purpose

Local-first capability gap resolution with risk-tiered suggestions. When a gap is identified (from learnings, advice, or governance findings), the resolver matches it against local capability assets and returns a decision: reuse, configure, create_local, or install_suggested.

## Implemented Slice

- `src/argus/capability_resolution/models.py`
  - `Decision` StrEnum: reuse, configure, install_suggested, create_local, merge, ignore
  - `DECISION_RISK` mapping
  - `CapabilityResolution` frozen dataclass
- `src/argus/capability_resolution/resolver.py`
  - `CapabilityResolver` with keyword-overlap scoring
  - 4-tier decision cascade: exact match → partial (≥0.15) → similar (<0.15) → install suggested
  - `resolve`, `resolve_from_learnings`, `resolve_from_advice`, `resolve_from_findings`
  - Deterministic: same inputs yield same decisions
- `src/argus/capability_resolution/reporting.py`
  - Markdown + JSON resolution reports
- `src/argus/application/resolution.py`
  - `ResolutionApplication` orchestrator
- `src/argus/cli.py`
  - `argus resolve run` and `argus resolve report`
- `src/argus/paths.py`
  - `resolution_reports_dir`
- `tests/test_phase6_capability_resolution.py` (12 tests)
- `tests/test_structure_boundaries.py` (2 tests)

## Boundaries

In scope:

- Read-only capability gap resolution.
- 4 risk-tiered decisions with evidence and confidence scores.
- Input sources: raw gaps, candidate learnings, pack advice, governance findings.
- Local matching via keyword overlap scoring.

Out of scope:

- Installing, downloading, or mutating capability assets.
- External registry or marketplace queries.
- Auto-execution of suggested installs.

## Validation

```bash
python -m unittest discover tests/ -v
```

Result:

- 56 tests passed.
- All 12 Phase 6 tests pass.
- All 44 prior-phase tests pass (no regressions).

Smoke evidence:

- `resolve run` with research asset and "Need research capability" gap → decision: reuse, risk: low, confidence: 0.9.

## Next Steps

1. Start Phase 7 on a new phase branch.
2. Governed action lifecycle (accept/reject/schedule resolution actions).
3. External registry lookups for install_suggested decisions.
