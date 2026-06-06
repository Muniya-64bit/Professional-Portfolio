# Database Migrations

PostgreSQL migrations for the KVPL system. Run in order via `migrate.py`.

## Files

| File | Purpose |
|---|---|
| `001_initial_schema.sql` | Core tables, indexes, views, fertilizer seed data |
| `002_sample_data.sql` | Estates, blocks, users, fertilizer/water/ROI sample data |
| `003_labour_planner_schema.sql` | Labour module: employee, worker_group, rotation_cycle, block_assignment |
| `004_labour_sample_data.sql` | Kundasale Estate: 90 employees, 6 groups, rotation, current week plan |
| `005_remaining_estates_sample_data.sql` | Ramboda / Hunasgiriya / Haputale: full labour data + 4 weeks history |
| `006_ml_yield_prediction.sql` | ML module: block ML columns, block_yield_record, estate_weather, yield_prediction |
| `QUERIES.sql` | Reference SQL for all modules (not run by migrate.py) |

## Commands

```powershell
cd backend
python migrate.py migrate    # run all pending
python migrate.py status     # show executed / pending
python migrate.py rollback   # drop everything (dev only)
```

## Schema Overview

### Core
- `estate` — 4 plantations
- `factory` — processing facilities
- `user` — system users (managers, supervisors, admin)
- `block` — tea blocks within an estate

### Module 1 — Fertilizer Rotation
- `fertilizer_type`, `fertilizer_application`, `fertilizer_recommendation`

### Module 2 — ROI Calculator
- `input_cost`, `yield_record`, `roi_snapshot`

### Module 3 — Water Efficiency
- `water_baseline`, `water_usage`

### Module 4 — Labour Planner
- `employee` — field workers (pluckers, supervisors)
- `worker_group` — teams of workers, one per block
- `worker_group_member` — employee ↔ group membership with dates
- `rotation_cycle` — named rotation pattern per estate
- `rotation_round_block` — full matrix: which group → which block in each round
- `labour_plan` — weekly plan header
- `block_assignment` — daily group→block assignment (rotation or manual override)
- `employee_day_assignment` — individual add/remove overrides per day

### ML Yield Prediction
- `block_yield_record` — monthly block-level yield records
- `estate_weather` — monthly weather data per estate (NASA POWER)
- `yield_prediction` — ML model predicted yield output per block per month
- `block.elevation_m`, `block.bush_age_yrs`, `block.zone` — new ML feature columns added to block table

### Audit
- `audit_log` — cross-module change history

## Views

| View | Description |
|---|---|
| `v_active_group_members` | Group headcount vs capacity per estate |
| `v_current_week_assignments` | This week's block assignments with efficiency % |
| `v_rotation_progress` | Current round / total rounds per estate |
| `v_roi_current_month` | Current month ROI ranking |
| `v_water_status_latest` | Latest water intensity per factory |
| `v_block_fert_summary` | Fertilizer applications last 12 months |

## Notes

- All primary keys are UUIDs (`uuid-ossp` extension)
- `block_allocation` was replaced by `block_assignment` in migration 003
- Migration 003 drops `block_allocation` — run 001+002 before 003
- Migrations 004 and 005 depend on 003 tables existing
