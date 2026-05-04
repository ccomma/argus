# Phase 7 Implementation Plan

## Behavior Preserved

Phase 7 must not auto-execute modifications without user confirmation. Every modification produces a snapshot before mutation.

## Step 1: Models

- `ModificationSnapshot` — frozen dataclass with deterministic ID via SHA-1
- `AssetDiff` — diff output model
- `ModificationAuditRecord` — audit log entry
- `ModificationResult` — operation result with warnings
- `ModificationReport` — report paths

## Step 2: Snapshot Manager

- Serialize objects (asset or contract) to JSON
- Write to `{store}/modifications/snapshots/{id}.json`
- Load snapshots by ID for rollback

## Step 3: Diff Engine

- Field-level comparison via `_changed_fields_dict`
- Line-level unified diff via `_unified_diff_lines`
- Separate methods for capability assets and work contracts

## Step 4: Audit Ledger

- Wraps `AppendOnlyJsonlStore[ModificationAuditRecord]`
- Deduplicates by audit record ID
- Supports list and get-by-id

## Step 5: Rollback Manager

- Loads snapshot from disk
- Deserializes to original model
- Restores asset in inventory or contract in storage
- Creates rollback audit record

## Step 6: Application Orchestrator

- `preview_asset_modification` — diff only, no mutation
- `apply_asset_modification` — snapshot → modify → diff → audit
- `preview_contract_modification` / `apply_contract_modification` — same for contracts
- `rollback` — via audit record ID
- `write_report` — Markdown + JSON

## Step 7: CLI And Tests

- 7 subcommands: preview, apply, contract-preview, contract-apply, rollback, audit-log, report
- 15 focused tests covering all exit conditions
- Full suite regression check (71 tests)

## Final Status

Completed on branch `phase7`.
