# Phase 4 Implementation Plan

## Behavior Preserved

Phase 3 asset scanning remains read-only and continues to write only Argus inventory and reports. Phase 4 must not install, edit, delete, disable, or rewrite discovered capability sources.

## Step 1: Pack Manifest MVP

- Define capability pack manifest and entry models.
- Store manifests under `.argus/capability-packs/<pack_id>/<version>.json`.
- Compute content hashes from canonical JSON.
- Snapshot asset metadata and asset content hash.

## Step 2: Risk Snapshot MVP

- Use a deterministic built-in risk policy table.
- Infer reason codes from asset permissions.
- Calculate aggregate risk with highest-risk-wins semantics.
- Record `risk_policy_version` separately from manifest schema version.

## Step 3: CLI MVP

- `packs propose`: render the proposed manifest without writing it.
- `packs create`: write a new manifest version from explicit required/optional asset ids.
- `packs inspect`: show a manifest and computed content hash.
- `packs check`: compare a manifest against current inventory without mutation.

## Step 4: Tests

- Manifest serialization and content hash stability.
- Entry id stability.
- Risk inference and aggregate risk.
- Required/optional completeness behavior.
- Check report does not mutate persisted manifests.
- CLI create, inspect, and check flow.

## Step 5: Contract And Role Completion

- Bind concrete pack version and content hash to a work contract.
- Store binding evidence on the contract.
- Create role capability packs that reference pack manifests instead of inlining entries.
- Reuse pack checks for role checks.
- Add missing capability and duplicate asset advice.

## Final Status

Completed on branch `phase4`.
