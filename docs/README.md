# Argus Documentation

This directory is a shared project-context namespace. It is not owned by any single agent, skill, automation, or workflow.

## Source Of Truth

| Artifact | Owns | Must Not Own |
| --- | --- | --- |
| `../DESIGN.md` | Long-term product judgment, principles, non-goals, and strategic boundaries | Sprint tasks, phase status, line-level implementation |
| `../CONTEXT.md` | Domain language, glossary, concept relationships, and flagged ambiguities | Product positioning, phase status, task tracking |
| `roadmap/` | Phase sequence, phase goals, acceptance criteria, and exit conditions | Detailed PRDs, module internals, task tracking |
| `context/` | Current handoff, context loading rules, branch state, next work, verification commands | Full design history, product essay, complete implementation detail |
| `phases/` | Phase handoffs, implementation plans, acceptance evidence, and historical phase records | Durable product direction |
| `prd/` | Product requirements, user value, goals, non-goals, and success criteria | Module internals, storage detail, task status |
| `technical/` | Architecture contracts, models, interfaces, storage, risks, and security boundaries | Product positioning, daily progress |
| `testing/` | Test strategy, fixtures, regression risks, and validation scope | Acceptance evidence after the fact |
| `adr/` | Durable decisions that are hard to reverse, surprising without context, and based on real tradeoffs | Temporary notes, routine implementation choices |
| `agents/` | Agent-facing repo conventions, issue tracker hints, domain-doc routing | Product or architecture source material |
| `templates/` | Reusable document skeletons | Project-specific proof or status |
| `process/` | Documentation flow and maintenance rules | Phase-specific execution status |

## Write Rule

Before editing, classify the change by responsibility. If an artifact already owns the topic, update or link that artifact instead of duplicating its content elsewhere.

Historical phase files are evidence records. Do not rewrite them just to apply a newer documentation convention unless the historical record is misleading for current work.
