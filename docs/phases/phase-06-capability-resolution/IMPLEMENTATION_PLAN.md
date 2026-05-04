# Phase 6 Implementation Plan

## Behavior Preserved

Phase 6 must not install, download, or mutate capability assets. All decisions are read-only suggestions.

## Step 1: Decision Model

- Define `Decision` StrEnum with six values.
- Define `DECISION_RISK` mapping.
- Define `CapabilityResolution` frozen dataclass with evidence and confidence.

## Step 2: Keyword-Based Matching

- `normalize` for text preprocessing.
- `_extract_keywords` for token extraction (≥3 chars).
- `_keyword_overlap` with Jaccard-style scoring (capped at 0.75).
- `_is_exact_match` when ≥50% of asset tokens appear in gap keywords.
- `_CONFIGURE_THRESHOLD = 0.15` to separate CONFIGURE from CREATE_LOCAL.

## Step 3: Resolution Cascade

1. Exact match → REUSE (risk: low)
2. Scored match ≥0.15 → CONFIGURE (risk: low)
3. Similar match >0.0 → CREATE_LOCAL (risk: medium)
4. No match → INSTALL_SUGGESTED (risk: high)

## Step 4: Multi-Source Resolution

- `resolve(gaps)` — raw gap dicts.
- `resolve_from_learnings(learnings)` — candidate learning items.
- `resolve_from_advice(missing)` — pack advisor output.
- `resolve_from_findings(findings)` — governance dedupe/risk/role findings.
- Deduplication by gap_id.

## Step 5: Reporting And CLI

- `ResolutionReporter` → Markdown + JSON reports.
- `argus resolve run` — stdout JSON.
- `argus resolve report` — file output.
- 12 focused tests.

## Final Status

Completed on branch `phase6`.
