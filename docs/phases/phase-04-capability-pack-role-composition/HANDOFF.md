# Phase 4 Handoff: Capability Pack and Role Composition

## Purpose

Turn scanned capability assets into versioned, auditable capability pack manifests.

Phase 4 connects inventory assets, work contracts, and role packs through versioned capability pack manifests. It writes only Argus-owned manifests and binding evidence under `.argus/`.

## Implemented Slice

- `src/argus/capability_packs.py`
  - manifest, entry, result, and check report models
  - deterministic risk inference table
  - canonical JSON content hashing
  - versioned manifest storage
  - pre-execution-style checks for missing and drifted assets
  - work contract capability pack binding
  - role capability pack manifests that reference packs
  - missing capability and duplicate asset advice
- `src/argus/application.py`
  - `CapabilityPackApplication`
- `src/argus/cli.py`
  - `packs propose`
  - `packs create`
  - `packs inspect`
  - `packs check`
  - `packs advise`
  - `contract bind-pack`
  - `roles create-pack`
  - `roles inspect-pack`
  - `roles check-pack`
- `src/argus/paths.py`
  - `.argus/capability-packs`
- `tests/test_phase4_capability_packs.py`

## Boundaries

In scope:

- Required and optional asset entries.
- Stable `entry_id` values based on pack id, asset id, and primary purpose.
- Snapshot metadata for asset identity, permissions, asset hash, risk tier, and risk reasons.
- Highest-risk-wins aggregate risk.
- Read-only check reports that do not mutate manifests.
- Work contract binding locks contract version, pack version, and content hash.
- Role pack composition references capability packs instead of inlining entries.

Out of scope for this slice:

- Nested packs.
- External capability installation.
- User-configurable risk policy.
- Governance approval workflows.
- Full execution-run evidence beyond contract binding evidence.

## Validation

Current passing command:

```bash
./scripts/check.sh
```

Result:

- 39 tests passed.
- Compile check passed.
- Diff whitespace check passed.

Local smoke store:

```bash
/private/tmp/argus-phase4-closeout/.argus
```

Smoke evidence:

- `assets scan --profile local-codex`: 48 assets, 0 warnings.
- `packs create product-manager-pack`: version 1, content hash `ce57b0801c2210a0c86039da6ef993c9e417a235438aa467198bb439f372e536`.
- `packs check product-manager-pack`: complete before simulated drift.
- `roles create-pack product-manager`: role pack references `product-manager-pack@1`.
- `roles check-pack product-manager`: complete before simulated drift.
- `contract bind-pack`: fuzzy product contract bound to `product-manager-pack@1`.
- `packs advise`: reports duplicate asset groups and missing `roadmap-gap-demo`.
- Simulated required asset removal: `packs check` reports incomplete with missing required entry.

## Next Steps

1. Start Phase 5 on a new phase branch.
2. Define governance report reader and output format before expanding governance workflows.
3. Expand pack checks to report policy-version drift and permission/risk drift separately.
4. Add governance proposal outcomes before any automatic pack update path.
