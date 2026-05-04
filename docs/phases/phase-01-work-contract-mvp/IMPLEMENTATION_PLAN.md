# Phase 1 Implementation Plan

> This is the historical task record for Phase 1. Product rationale lives in the PRD; architecture details live in the technical design; proof lives in `ACCEPTANCE.md`.

## Goal

Build the smallest local-first work contract loop that turns vague intent into a structured contract and evaluates derived deliverables.

## Milestones

### 1. Contract Model And Storage

Status: done.

Tasks:

- Define work contract, question strategy, completeness score, deliverable contract, and evaluation models.
- Store contracts, versions, deliverables, evaluations, and evidence under `.argus/`.

### 2. Contract Drafting CLI

Status: done.

Tasks:

- Add `contract start` and `contract draft`.
- Support quick, standard, and strict question modes.
- Generate clarifying questions and contract completeness feedback.

### 3. Contract Viewing And Scoring

Status: done.

Tasks:

- Add `contract show`.
- Add `contract score`.
- Render contract Markdown.

### 4. Deliverable Rendering And Evaluation

Status: done.

Tasks:

- Add `contract render`.
- Add `contract evaluate`.
- Detect missing deliverable requirements against the contract.

### 5. Verification And Closeout

Status: done.

Tasks:

- Add core, flow, and CLI tests.
- Run unit and integration tests.
- Preserve evidence in `ACCEPTANCE.md`.

## Verification Commands

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall -q src tests
git diff --check
```
