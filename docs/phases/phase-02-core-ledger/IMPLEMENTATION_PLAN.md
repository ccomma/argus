# Phase 2 Implementation Plan

> This is the historical task record for Phase 2. Product rationale lives in the PRD; architecture details live in the technical design; proof lives in `ACCEPTANCE.md`.

## Goal

Build the append-only Argus Core ledger and candidate learning loop that later capability management can consume.

## Milestones

### 1. Event Ledger

Status: done.

Tasks:

- Define `EventRecord`.
- Add append-only JSONL storage.
- Add event listing.

### 2. Contract Evidence Ingestion

Status: done.

Tasks:

- Import Phase 1 contract evidence.
- Preserve contract id, version, workspace, session, and evidence references.

### 3. Transcript Ingestion

Status: done.

Tasks:

- Support Codex transcript fixtures.
- Normalize user correction, command failure, success, and acceptance events.

### 4. Candidate Learning Ledger

Status: done.

Tasks:

- Define `CandidateLearningItem`.
- Extract candidate learnings from events.
- Preserve confidence, status, reverse learning target, and evidence refs.

### 5. Reports And Refactor

Status: done.

Tasks:

- Generate a local learning report.
- Keep CLI thin and ledger modules focused.
- Preserve append-only behavior.

## Verification Commands

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall -q src tests
git diff --check
```
