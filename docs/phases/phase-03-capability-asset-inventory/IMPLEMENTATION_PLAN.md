# Phase 3 Implementation Plan

## Goal

Create a local-first, read-only capability inventory that can show what capability assets exist and how candidate learnings may relate to them.

## Milestones

### 1. Minimum Inventory Slice

Status: done locally.

Tasks:

- Add `CapabilityAsset` data model.
- Add scanner for skills, plugins, MCP configs, rules, scripts, and memory.
- Add `.argus/assets/inventory.json`.
- Add `assets scan` and `assets list`.
- Add fixture tests.

### 2. Report and Learning Link Slice

Status: done locally.

Tasks:

- Add asset scan report.
- Add candidate learning to asset link report.
- Add duplicate hint section.
- Add CLI smoke tests.

### 3. Robust Local Scan Slice

Status: done locally.

Tasks:

- Define default local scan profile.
- Support additional MCP config shapes.
- Expand plugin manifest metadata extraction.
- Add warnings for unreadable or invalid assets.
- Keep source asset files read-only.

### 4. Risk and Conflict Slice

Status: done locally.

Tasks:

- Refine permission extraction.
- Refine risk scoring.
- Detect likely conflict groups.
- Add report sections that distinguish duplicate, overlap, conflict, and risky asset.

### 5. Phase Acceptance

Status: done.

Tasks:

- Run full tests.
- Run read-only scan on local user asset directories.
- Update `ACCEPTANCE.md`.
- Update `HANDOFF.md`.
- Update `docs/context/CURRENT_HANDOFF.md`.

### 6. Candidate Matching Slice

Status: done locally.

Tasks:

- Remove generic capability words from candidate-to-asset matching.
- Match against asset name, path stem, parent path, permissions, and metadata.
- Keep match reason explainable.

## Verification Commands

```bash
./scripts/check.sh
PYTHONPATH=src python3 -m argus.cli assets scan --store /private/tmp/argus-phase3-final-check/.argus --profile local-codex
```
