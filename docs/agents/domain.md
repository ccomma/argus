# Domain Docs

This repo uses a single-context domain documentation layout. `CONTEXT.md` owns domain language only; product direction, phase status, and task tracking live elsewhere.

## Before Exploring

Engineering skills should read these only when domain context or architectural history is relevant to the task:

- `CONTEXT.md` at the repo root
- `docs/adr/` for architecture decision records

If these files do not exist yet, proceed silently. Do not flag their absence or create them unless the user asks or the current task requires domain documentation.

## Expected Structure

```text
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-example-decision.md
│   └── 0002-example-decision.md
└── src/
```

## Vocabulary Rule

When output names a domain concept in an issue title, refactor proposal, hypothesis, test name, or PRD, use the terms defined in `CONTEXT.md`.

If the needed concept is not in `CONTEXT.md`, either avoid inventing new terminology or note the gap for later domain documentation.

Do not copy `CONTEXT.md` definitions into PRDs, handoffs, technical designs, or issue bodies unless the local task needs a short quote. Link back to the source of truth instead.

## ADR Conflicts

If a recommendation contradicts an existing ADR, surface the conflict explicitly instead of silently overriding it.
