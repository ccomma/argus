# Argus

Argus is a local-first work contract and capability operating system for AI power users.

It helps users turn vague intent into professional, executable, reviewable work contracts, while making AI skills, tools, memories, workflows, role packs, and long-term behavior changes traceable, measurable, and reversible.

## Why Argus

Modern AI tools are powerful, but using them well is still surprisingly hard.

Most users do not know the professional process behind a task. They may know they want to "build a product", "research a market", "write a proposal", or "ship a feature", but they do not know which questions to answer first, which artifacts to produce, or when the requirements are good enough to execute.

At the same time, heavy AI users and developers accumulate:

- project rules
- memories
- skills
- MCP servers
- plugins
- local scripts
- workflow conventions
- work contract templates
- role packs
- repeated corrections and tool-specific lessons

Each piece can make an agent better, but the whole system is hard to inspect, govern, upgrade, or roll back.

Argus is designed around one question:

> How can AI agents turn vague human intent into executable work, learn from real outcomes, and improve their capabilities without turning long-term behavior into uncontrolled drift?

## What Argus Does

Argus is not just a memory store, a skill installer, or another agent template library. It is built around four product pillars:

1. **Work contracts**
   - Let the agent ask the questions first, clarify vague intent, and produce a structured contract with goals, context, constraints, deliverables, confirmation points, and acceptance criteria.
   - Version work contracts so requirement changes, handoffs, and reviews can be tracked instead of buried in chat history.

2. **Correction-driven learning**
   - Detect repeated mistakes, user corrections, failed commands, and successful recovery paths.
   - Turn raw events into candidate learnings before promoting anything into long-term behavior.

3. **Capability lifecycle management**
   - Treat skills, MCP servers, plugins, scripts, rules, memories, workflows, and packages as capability assets.
   - Attach capability packs to work contracts and role packs, then track where each capability came from, what it can do, how risky it is, whether it is still useful, and how to roll it back.

4. **Policy-driven automation**
   - Automate low-risk work such as scanning, reporting, deduplication, and local reuse.
   - Keep higher-risk actions such as external installation, global rule changes, and executable code changes behind explicit policy or confirmation.

## Core Loop

Argus follows a staged learning and governance loop:

```text
vague intent
  -> agent-led clarification
  -> work contract
  -> role or work mode
  -> capability pack
  -> execution evidence
  -> candidate learnings
  -> capability resolution
  -> capability updates
  -> runtime use
  -> governance
  -> maintenance and ROI tracking
```

The key boundary is simple: raw events are not memory, and memory is not policy. Every durable behavior change needs evidence, review, and a path back.

## Project Status

Argus is in early development.

The first public milestone is a personal, local-first work contract MVP:

- start with a vague user intent
- let Argus ask clarifying questions
- produce a work contract with clear boundaries and acceptance criteria
- derive a structured deliverable such as a PRD, research plan, or development roadmap
- record candidate learnings from corrections and repeated patterns
- keep all risky capability or behavior changes manual by default

Capability inventories, governance reports, team policies, dashboards, and cross-agent runtime integrations are planned for later stages.

## Quickstart

Run the Phase 1 CLI locally:

```bash
PYTHONPATH=src python3 -m argus.cli contract draft \
  --intent "Build Argus Phase 1" \
  --mode quick \
  --goal "Create a CLI work contract MVP" \
  --outputs "Work contract JSON" \
  --acceptance-criteria "The contract is saved locally"
```

Argus writes local runtime output under `.argus/`, which is ignored by git.

Useful Phase 1 commands:

```bash
PYTHONPATH=src python3 -m argus.cli contract start --intent "Plan a complex task" --mode quick
PYTHONPATH=src python3 -m argus.cli contract show <contract-id>
PYTHONPATH=src python3 -m argus.cli contract score <contract-id>
PYTHONPATH=src python3 -m argus.cli contract render <contract-id> --type prd
PYTHONPATH=src python3 -m argus.cli contract evaluate <contract-id> path/to/deliverable.md --type prd
```

Useful Phase 2 commands:

```bash
PYTHONPATH=src python3 -m argus.cli ledger ingest-contract <contract-id>
PYTHONPATH=src python3 -m argus.cli ledger ingest-transcript path/to/transcript.jsonl
PYTHONPATH=src python3 -m argus.cli ledger list
PYTHONPATH=src python3 -m argus.cli learning extract
PYTHONPATH=src python3 -m argus.cli learning list
PYTHONPATH=src python3 -m argus.cli learning report
```

Useful Phase 3 commands:

```bash
PYTHONPATH=src python3 -m argus.cli assets scan --profile local-codex
PYTHONPATH=src python3 -m argus.cli assets scan \
  --skill-dir path/to/skills \
  --plugin-dir path/to/plugins \
  --mcp-config path/to/mcp.json \
  --rule-file path/to/AGENTS.md \
  --script-dir path/to/scripts \
  --memory-dir path/to/memory
PYTHONPATH=src python3 -m argus.cli assets list
PYTHONPATH=src python3 -m argus.cli assets report
PYTHONPATH=src python3 -m argus.cli assets link-learnings
```

The local contract workspace stores:

- `contract.json`
- `contract.md`
- `versions/v1.json`
- `deliverables/<type>.md`
- `evaluations/evaluation-1.json`
- `evidence.jsonl`

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Intended Users

Argus is for people who use AI to produce real work and want better outcomes without first becoming expert prompt writers or workflow designers.

It is especially useful for developers, creators, operators, and teams that want to answer questions like:

- What questions should be asked before execution starts?
- When is the request clear enough to start?
- What should the work contract include?
- What deliverable should be produced?
- Which role or work mode should handle the task?
- What has my agent actually learned from prior work?
- Which skills, MCP servers, plugins, scripts, rules, and memories are installed?
- Which capabilities are useful, stale, duplicated, risky, or conflicting?
- When should an agent reuse an existing capability instead of creating a new rule or skill?
- Can agent self-improvement be auditable and reversible?

## Design Principles

- Local-first by default.
- Runtime-neutral core, agent-specific adapters at the edge.
- Work contracts are not chat summaries; they need goals, boundaries, confirmation points, and acceptance criteria.
- Roles are not personalities; they are governed bundles of workflow, questions, deliverables, capability packs, and acceptance criteria.
- Prefer mature existing capabilities before generating new ones.
- Do not promote one-off events into long-term rules.
- Automate low-risk governance work.
- Make high-risk behavior changes explicit, backed up, and reversible.
- Measure whether learning actually improves future work.

## Development Status

This repository currently contains the public project entrypoint and will grow into the implementation workspace for Argus.

Internal design notes, roadmap drafts, planning documents, and session context are intentionally kept out of git so that the public repository can stay focused on implementation artifacts and user-facing documentation.
