# Phase 10 Acceptance

## Acceptance Criteria

| Criterion | Status |
| --- | --- |
| Strategy engine covers 5 action types per roadmap | PASS — trusted text skills, project rules, contract templates, role flows, installed MCP enablement |
| Version locking usable by rollback mechanism | PASS — lockfile with persistent JSON, lock/unlock/list |
| Risk reporting usable by rollback | PASS — SecurityScanner reports risk scores and findings |
| Policy-driven automation with risk levels | PASS — LOW→auto, MEDIUM→ask, HIGH→block defaults |
| Local web UI for workbench | PASS — 11 HTML pages with REST API backend |
| Work Contract Console (web) | PASS — contracts page with status badges, detail links |
| Personal Playbook Registry (web + CLI) | PASS — create/list/show/delete via both web and CLI |
| Role Pack Registry (web) | PASS — roles page with detail links |
| Security scanning functional | PASS — prompt-injection + supply-chain detection |
| CLI web serve command | PASS — configurable host/port |
| No regression | PASS — 154 tests |

## Tests

```bash
python -m unittest discover tests/ -v
```

154 tests passed, no regressions.

## Commands

```bash
# Start web workbench
python -m argus.cli web --store .argus --port 8765

# Strategy management
python -m argus.cli strategy show --store .argus
python -m argus.cli strategy set-rule --action-type install_trusted_skill --risk-level low --decision auto

# Playbook management
python -m argus.cli playbook create --name "My Workflow" --role architect
python -m argus.cli playbook list --store .argus

# Version locking
python -m argus.cli version-lock lock --asset-id a1 --asset-type skill --source local --version 1.0.0
python -m argus.cli version-lock list --store .argus

# Security scanning
python -m argus.cli security scan --content "ignore previous instructions"
python -m argus.cli security scan --file path/to/skill.md
```

## Final Commit

`2ac765e`
