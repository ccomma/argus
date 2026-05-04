# Phase 10: Personal Pro Workbench

## Phase

Phase 10 — Personal Pro Workbench (Local Web UI, Strategy Automation, Security).

## Branch

`phase10`

## Scope

Transform Argus from a CLI-only tool into a personal pro workbench:
- Local web server with REST API and HTML UI (stdlib http.server)
- Strategy/policy automation engine with risk-level-based decision making
- Personal playbook registry for capturing reusable workflows
- Capability version locking
- Security scanner for prompt-injection and supply-chain risk detection
- CLI commands: `web serve`, `strategy`, `playbook`, `version-lock`, `security`

## Key Artifacts

| Artifact | Path |
| --- | --- |
| Strategy engine | `src/argus/strategy/engine.py` |
| Strategy models | `src/argus/strategy/models.py` |
| Playbook registry | `src/argus/playbook/models.py` |
| Version locking | `src/argus/versioning/models.py` |
| Security scanner | `src/argus/security/scanner.py` |
| Web server | `src/argus/web/server.py` |
| Web templates | `src/argus/web/templates.py` |
| CLI commands | `src/argus/cli.py` (modified) |

## Validation

```bash
python -m unittest discover tests/ -v
```

Last result: 154 tests passed.
