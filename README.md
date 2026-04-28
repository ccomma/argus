# Argus

Argus is a local-first learning and capability governance system for AI agents.

It helps agents learn from real work, discover capability gaps, manage skills and tools as assets, and make every long-term behavior change traceable, reviewable, and reversible.

## Why Argus

Modern AI agent workflows are becoming powerful but messy. Developers often accumulate:

- project rules
- memories
- skills
- MCP servers
- plugins
- local scripts
- workflow conventions
- repeated corrections and tool-specific lessons

Each piece can make an agent better, but the whole system is hard to inspect, govern, upgrade, or roll back.

Argus is designed around one question:

> How can agents automatically get better from real work without turning long-term memory and tool installation into uncontrolled behavior drift?

## What Argus Does

Argus is not just a memory store or a skill installer. It is built around three product pillars:

1. **Correction-driven learning**
   - Detect repeated mistakes, user corrections, failed commands, and successful recovery paths.
   - Turn raw events into candidate learnings before promoting anything into long-term behavior.

2. **Capability lifecycle management**
   - Treat skills, MCP servers, plugins, scripts, rules, memories, workflows, and packages as capability assets.
   - Track where they came from, what they can do, how risky they are, whether they are still useful, and how to roll them back.

3. **Policy-driven automation**
   - Automate low-risk work such as scanning, reporting, deduplication, and local reuse.
   - Keep higher-risk actions such as external installation, global rule changes, and executable code changes behind explicit policy or confirmation.

## Core Loop

Argus follows a staged learning and governance loop:

```text
agent events
  -> candidate learnings
  -> capability resolution
  -> reuse / install suggestion / local creation
  -> runtime use
  -> governance
  -> maintenance and ROI tracking
```

The key boundary is simple: raw events are not memory, and memory is not policy. Every durable behavior change needs evidence, review, and a path back.

## Project Status

Argus is in early development.

The first public milestone is a personal, local-first capability ledger:

- ingest Codex session or transcript data
- identify candidate learnings
- scan local agent capabilities
- generate a capability inventory
- produce governance reports
- keep all risky changes manual by default

Team governance, shared policies, dashboards, and cross-agent runtime integrations are planned for later stages.

## Intended Users

Argus is for developers and teams that use AI agents heavily and want to answer questions like:

- What has my agent actually learned from prior work?
- Which skills, MCP servers, plugins, scripts, rules, and memories are installed?
- Which capabilities are useful, stale, duplicated, risky, or conflicting?
- When should an agent reuse an existing capability instead of creating a new rule or skill?
- Can agent self-improvement be auditable and reversible?

## Design Principles

- Local-first by default.
- Runtime-neutral core, agent-specific adapters at the edge.
- Prefer mature existing capabilities before generating new ones.
- Do not promote one-off events into long-term rules.
- Automate low-risk governance work.
- Make high-risk behavior changes explicit, backed up, and reversible.
- Measure whether learning actually improves future work.

## Development Status

This repository currently contains the public project entrypoint and will grow into the implementation workspace for Argus.

Internal design notes, roadmap drafts, planning documents, and session context are intentionally kept out of git so that the public repository can stay focused on implementation artifacts and user-facing documentation.
