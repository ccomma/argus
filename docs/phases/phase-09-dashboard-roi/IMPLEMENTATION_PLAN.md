# Phase 9 Implementation Plan

## Completed

1. ROI calculator — ContractROI (completeness, status distribution, deliverable pass rate), LearningROI (by type/scope, confidence), RoleROI (handoff count, active roles)
2. DashboardReporter — writes combined markdown + JSON reports to disk
3. MaintenanceEngine — duplicate detection, conflict detection, deprecated/archived listing, unused pack detection (reuses `find_potential_duplicates` and `find_potential_conflicts` from `argus.assets.analysis`)
4. MaintenanceReporter — writes markdown + JSON maintenance reports
5. CLI commands — `dashboard`, `maintenance run`, `maintenance report`
6. Tests — 12 tests (8 dashboard/ROI + 4 maintenance)
7. Full regression — 115 tests passing
