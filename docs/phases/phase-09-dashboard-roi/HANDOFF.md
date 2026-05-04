# Phase 9: Dashboard, ROI & Maintenance

## Phase

Phase 9 — Dashboard, ROI Metrics & Maintenance Tasks.

## Branch

`phase9`

## Scope

Add analytics, dashboard reporting, and maintenance capabilities:
- ROICalculator computing ContractROI, LearningROI, and RoleROI from ledger/storage data
- DashboardReporter writing combined markdown + JSON dashboard reports
- MaintenanceEngine detecting duplicates, conflicts, deprecated/archived assets, and unused packs
- MaintenanceReporter writing maintenance reports
- CLI commands: `dashboard`, `maintenance run`, `maintenance report`

## Key Artifacts

| Artifact | Path |
| --- | --- |
| ROI models | `src/argus/analytics/models.py` |
| ROI calculator | `src/argus/analytics/calculator.py` |
| Dashboard reporter | `src/argus/analytics/reporting.py` |
| Maintenance engine | `src/argus/maintenance/engine.py` |
| Maintenance reporter | `src/argus/maintenance/reporting.py` |
| CLI commands | `src/argus/cli.py` (modified) |

## Validation

```bash
python -m unittest discover tests/ -v
```

Last result: 115 tests passed.
