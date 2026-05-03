# Argus Context

Argus is a local-first work contract and capability governance system for AI power users. This file owns domain language only; product direction lives in `DESIGN.md`, current execution context lives in `docs/context/CURRENT_HANDOFF.md`, and durable decisions live in `docs/adr/`.

## Language

**Work Contract**:
A bounded agreement that turns vague intent into goals, non-goals, constraints, deliverables, confirmation points, and acceptance criteria.
_Avoid_: prompt, chat summary, task note

**Deliverable Contract**:
A reusable acceptance shape for a specific deliverable type, including required sections and evaluation expectations.
_Avoid_: template when it is used for evaluation

**Execution Evidence**:
Observed facts from agent work, deliverable evaluation, commands, transcripts, or user corrections that can support later learning and review.
_Avoid_: log when it may become evidence

**Capability Asset**:
A skill, MCP server, plugin, script, rule, memory, workflow, role pack, or package that can change what an agent can do.
_Avoid_: tool when the asset may be a rule, memory, or workflow

**Capability Inventory**:
A local snapshot of discovered capability assets, used for review, conflict detection, risk analysis, and later pack composition.
_Avoid_: installed tools list, scan output

**Capability Conflict**:
A detected overlap between capability assets that may confuse selection, duplicate behavior, or increase risk.
_Avoid_: error, violation

**Capability Change**:
A proposed or applied change to capability assets or packs, derived from candidate learning or explicit user intent.
_Avoid_: automatic memory write, silent skill edit

**Capability Pack**:
A versioned bundle of capability assets attached to a work contract, role, or work mode.
_Avoid_: random installed tools

**Candidate Learning**:
An observed correction, failure, recovery path, or successful pattern that may become durable behavior after review.
_Avoid_: memory until it is promoted

**Learning Target**:
The kind of durable behavior or capability asset that a candidate learning may update if promoted.
_Avoid_: reverse learning target, memory target

**Learning Ledger**:
An append-only record of events and candidate learnings used for audit and later promotion decisions.
_Avoid_: database when discussing the domain concept

**Governance Policy**:
The layered rules that decide which capability or behavior changes can be automatic, policy-driven, isolated, rejected, or require explicit confirmation.
_Avoid_: approval queue

**Risk Tier**:
A governance classification of a capability asset or change, used to decide review and automation behavior.
For **Capability Packs**, each pack entry stores the selected asset's **Risk Tier** snapshot, and the pack stores an aggregate **Risk Tier** snapshot derived from its entries.
_Avoid_: raw risk score

**Role Pack**:
A governed bundle of workflow, questions, deliverables, capability packs, and acceptance criteria for a recurring work mode.
_Avoid_: personality

## Relationships

- A **Work Contract** can require one or more **Capability Packs**.
- A **Work Contract** can require one or more **Deliverable Contracts**.
- A **Work Contract** can constrain which **Governance Policies** or **Capability Changes** are allowed during execution.
- A **Deliverable Contract** helps evaluate whether a produced deliverable satisfies a **Work Contract**.
- A **Capability Pack** contains one or more **Capability Assets**.
- A **Capability Pack** stores entry-level **Risk Tier** snapshots and a pack-level aggregate **Risk Tier** snapshot.
- A **Capability Inventory** contains zero or more **Capability Assets** and can inform **Capability Pack** composition.
- A **Capability Inventory** can surface **Capability Conflicts** for a **Governance Policy** to review.
- A **Candidate Learning** has a **Learning Target** before any durable behavior changes.
- A **Candidate Learning** can propose a **Capability Change**.
- **Execution Evidence** can be recorded in a **Learning Ledger**.
- **Candidate Learnings** are derived from **Execution Evidence**.
- A **Governance Policy** decides whether a **Capability Change** is automatic, confirmation-gated, isolated, or rejected.
- A **Governance Policy** uses **Risk Tiers** when reviewing **Capability Changes** and **Capability Assets**.
- A **Learning Ledger** records **Candidate Learnings** before they become durable behavior.
- A **Governance Policy** controls how **Candidate Learnings** and **Capability Assets** are promoted, changed, installed, or rolled back.
- A **Role Pack** is a kind of **Capability Asset**.
- A **Role Pack** can require one or more **Capability Packs**.
- A **Role Pack** can reuse **Capability Packs** across many **Work Contracts**.

## Example Dialogue

> **Dev:** "Can Argus just remember that this agent should always use my product docs?"
> **Domain expert:** "Not directly. That starts as a **Candidate Learning** in the **Learning Ledger**. A **Governance Policy** decides whether it becomes a rule, a **Capability Asset**, or only a note linked to a specific **Work Contract**."

## Flagged Ambiguities

- "Capability" can mean a user-visible ability or the asset that provides it. Use **Capability Asset** when talking about the governed object on disk or in a registry.
- "Inventory" records discovered **Capability Assets** but does not own or modify the underlying files; ownership remains with the source system until a governed **Capability Change** is applied.
- `EventLedger` and `LearningLedger` are implementation slices of the domain **Learning Ledger**, not separate domain ledgers.
- "Memory" can mean raw recollection, a promoted user preference, or a ledger record. Use **Candidate Learning** before promotion and **Learning Ledger** for the audit record.
