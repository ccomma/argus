# Phase 5 Implementation Plan

## Behavior Preserved

Phase 5 must not mutate discovered capability sources, capability packs, role packs, or global agent configuration.

## Step 1: Governance Report Model

- Define `GovernanceFinding`.
- Define `PendingAction`.
- Define `GovernanceReportResult`.

## Step 2: Read-Only Aggregation

- Read contracts and evaluations.
- Read candidate learnings.
- Read capability asset inventory.
- Read latest capability packs.
- Read latest role packs.

## Step 3: Finding Categories

- Dedupe findings.
- Stale findings.
- Risk findings.
- Work contract findings.
- Role findings.

## Step 4: Outputs

- Markdown governance report.
- JSON governance report.
- Low-risk maintenance log.
- Pending action list.

## Step 5: CLI And Tests

- Add `argus governance report`.
- Add focused tests.
- Run full project verification.

## Final Status

Completed on branch `phase5`.
