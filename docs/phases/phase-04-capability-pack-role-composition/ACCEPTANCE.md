# Phase 4 Acceptance

## Current Status

Phase 4 accepted locally: capability pack manifests can be proposed, created, inspected, checked, bound to work contracts, referenced by role packs, and used for missing/duplicate capability advice.

## Evidence

Command:

```bash
./scripts/check.sh
```

Result:

- 35 tests passed.
- 39 tests passed.
- Compile check passed.
- Diff whitespace check passed.

## Acceptance Coverage

- A capability pack can reference required and optional inventory assets.
- A persisted manifest records version, schema version, risk policy version, entries, risk snapshots, and creation metadata.
- The content hash is stable after writing and loading the same manifest.
- Required missing assets make a check incomplete.
- Optional drift is reported without blocking the full pack.
- Check reports do not rewrite stored manifests.
- CLI supports `packs propose`, `packs create`, `packs inspect`, and `packs check`.
- CLI supports `contract bind-pack`.
- CLI supports `roles create-pack`, `roles inspect-pack`, and `roles check-pack`.
- CLI supports `packs advise`.
- A fuzzy work contract can bind to a concrete pack version and content hash.
- A Product Manager role can reference a complete capability pack.

## Smoke Evidence

Store:

```text
/private/tmp/argus-phase4-closeout/.argus
```

Commands and results:

- `assets scan --profile local-codex`: 48 assets, 0 warnings.
- `packs create product-manager-pack`: wrote version 1 with content hash `ce57b0801c2210a0c86039da6ef993c9e417a235438aa467198bb439f372e536`.
- `packs check product-manager-pack`: complete, no missing or drifted entries.
- `roles create-pack product-manager`: created role pack version 1 referencing `product-manager-pack`.
- `roles check-pack product-manager`: complete.
- `contract bind-pack contract-7485d1285e-e3093791 product-manager-pack`: binding records contract version 1, pack version 1, and content hash.
- `packs advise`: reports duplicate asset groups and missing `roadmap-gap-demo`.
- Simulated required asset removal from temporary inventory: `packs check product-manager-pack` reports incomplete and missing `product-manager-pack-asset-af3389c0b74429d1-implementation`.

## Remaining Phase 4 Work

- Report policy drift separately from asset drift.
- Add governed proposal outcomes before any durable pack update automation.
