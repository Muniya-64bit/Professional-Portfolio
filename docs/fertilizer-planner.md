# Fertilizer Rotation Planner — Implementation Reference

## Overview

The fertilizer planner manages three distinct concerns:

- **Catalogue** — what fertilizer products exist and their NPK composition
- **Programme** — per-estate schedule templates (which product, at what rate and interval)
- **Schedule** — generated instances derived from the programme (one row per block per step)
- **Applications** — actual field applications recorded against schedule entries

The separation between `fertilizer_programme` (template) and `fertilizer_schedule` (instance) is the core design decision: the programme defines *"Kundasale applies T0_200 at 200 kg/ha every 8 weeks for Mature blocks"*; the schedule derives *"Block A1 is due T0_200 on 2026-07-14"*.

---

## Database Tables

### `fertilizer_type`
Product catalogue. Seeded with 6 standard KVPL products, extended in migration 011.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `code` | VARCHAR(50) UNIQUE | e.g. `T0_200`, `U750`, `EP_GOLD` |
| `name` | VARCHAR(150) | |
| `description` | TEXT | |
| `default_dosage_kg` | DECIMAL(8,3) | Original field from migration 001 |
| `npk_n` | NUMERIC(5,2) | Added in migration 011 — % Nitrogen |
| `npk_p` | NUMERIC(5,2) | % Phosphorus (as P₂O₅) |
| `npk_k` | NUMERIC(5,2) | % Potassium (as K₂O) |

Seeded products: `T0_200` (46% N), `U750` (28.6/3.8/14.8), `EP_GOLD` (15/15/15), `MOP` (60% K), `RPR` (28% P), `DOLOMITE` (0/0/0).

### `fertilizer_application`
Historical record of what was actually applied to each block.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `block_id` | UUID FK → block | |
| `fertilizer_type_id` | UUID FK → fertilizer_type | |
| `applied_by` | UUID FK → "user" | Nullable |
| `application_date` | DATE | |
| `quantity_kg` | DECIMAL(10,3) | Must be > 0 |
| `rate_kg_per_ha` | NUMERIC(8,2) | Added migration 011; backfilled from quantity_kg / block area |
| `recommendation` | VARCHAR(20) | `apply_now` / `delay` / `increase_dosage` / `skipped` |
| `notes` | TEXT | |

### `fertilizer_programme`
Per-estate schedule template. Estate managers can edit via API.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `estate_id` | UUID FK → estate | |
| `fertilizer_type_id` | UUID FK → fertilizer_type | |
| `application_no` | INTEGER | Sequence within annual cycle for this product (1, 2, 3…) |
| `interval_weeks` | INTEGER | Weeks after previous `application_no` step; for step 1 = weeks from crop year start (Apr 1) |
| `rate_kg_per_ha` | NUMERIC(8,2) | Standard rate for this step |
| `zone_override` | VARCHAR(20) | `Low` / `Mid` / `High` — NULL means applies to all zones |
| `growth_stage_filter` | VARCHAR(100) | `Mature` / `Young` / `Immature` — NULL means all stages |
| `notes` | TEXT | |
| `is_active` | BOOLEAN | Soft-delete flag |

Unique constraint: `(estate_id, fertilizer_type_id, application_no, zone_override)`.

### `fertilizer_schedule`
Generated instances. Populated by the scheduling engine; field staff close entries by recording applications.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `block_id` | UUID FK → block | |
| `programme_id` | UUID FK → fertilizer_programme | |
| `due_date` | DATE | Calculated by engine |
| `status` | VARCHAR(20) | `pending` / `due` / `overdue` / `done` / `skipped` |
| `actual_application_id` | UUID FK → fertilizer_application | Set when marked done |
| `scheduled_rate_kg_per_ha` | NUMERIC(8,2) | Copied from programme at generation time — preserved if programme is later edited |
| `generated_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

Unique constraint: `(block_id, programme_id, due_date)`.

---

## Database Views

### `v_block_fert_summary`
Rolling 12-month summary per block × fertilizer product. Includes NPK composition and average application rate. Recreated in migration 011 to add the NPK columns (required `DROP VIEW` first — `CREATE OR REPLACE` cannot reorder columns).

### `v_fertilizer_schedule_alerts`
All `pending` / `due` / `overdue` schedule entries across all estates, ordered by urgency (`due_date ASC`). Used directly by the `/alerts` endpoint. Includes `days_overdue` (negative = days until due), `total_kg_needed` (rate × block area), and NPK context.

---

## Scheduling Engine

**Entry point:** `_generate_schedule_for_estate(cur, estate_id, today=None)` in `backend/fertilizer.py`.

The function iterates every block in the estate and every applicable programme step, applying three guard conditions before inserting a `fertilizer_schedule` row.

### Step by step

1. Fetch all blocks for the estate (`block.estate_id = %s`). Note: `block` has no `is_active` column — all blocks are included.

2. For each block, query `fertilizer_programme` steps that match the block's `zone` and `growth_stage`:
   - `zone_override IS NULL` → applies to all zones
   - `zone_override = block.zone` → zone-specific override
   - Same logic for `growth_stage_filter`

3. For each applicable step, run the three guards in order:

   **Guard 1 — Block area**
   Skip if `block.area_hectares` is NULL or ≤ 0. A zero-area block would produce a nonsensical `total_kg` and should not be scheduled.

   **Guard 2 — Idempotency**
   Skip if a `fertilizer_schedule` row already exists for `(block_id, programme_id)` with status `pending`, `due`, or `overdue`. Safe to call repeatedly without stacking duplicates.

   **Guard 3 — Over-fertilization**
   Find the `MAX(application_date)` from `fertilizer_application` for this block × fertilizer type. If the last application date falls within the current interval (`last_date >= today - interval_weeks`), the block was applied too recently — skip.

4. Calculate `due_date`:
   - Never applied → `due_date = today`
   - Previously applied → `due_date = last_date + interval_weeks`

5. Derive initial `status`:
   - `due_date > today` → `pending`
   - `due_date <= today` and `(today - due_date).days <= 7` → `due`
   - `due_date <= today` and `(today - due_date).days > 7` → `overdue`

6. Insert the `fertilizer_schedule` row. Returns counters: `inserted`, `skipped_existing`, `skipped_area`, `skipped_recent`.

### Public wrapper

`_run_generate_schedule(estate_id)` owns its own connection, commits, and returns `(payload_dict, http_status)`. Both HTTP routes call this function — no view-calling-view.

---

## API Endpoints

Base URL: `/api/fertilizer`  
All endpoints require `Authorization: Bearer <token>`.  
Write endpoints (`POST`, `PUT`, `DELETE`) additionally require role `admin` or `estate_manager`.  
`manager` role is read-only and estate-scoped (enforced by `effective_estate_id`).

### Product Catalogue

#### `GET /types` · `GET /products`
Returns all fertilizer types with NPK data. Both paths hit the same handler.

**Response**
```json
[
  { "id": "...", "code": "T0_200", "name": "T0 200", "npk_n": 46.0, "npk_p": 0.0, "npk_k": 0.0, "description": "..." }
]
```

---

### Programme (Schedule Templates)

#### `GET /programme?estate_id=<uuid>`
List active programme steps. `estate_id` optional for full-access roles; managers are forced to their own estate.

**Response** — array of programme steps with joined estate name, fertilizer code, and NPK.

#### `POST /programme`
Create a new programme step.

**Body**
```json
{
  "estate_id": "<uuid>",
  "fertilizer_type_id": "<uuid>",
  "application_no": 1,
  "interval_weeks": 8,
  "rate_kg_per_ha": 200.0,
  "zone_override": "Mid",
  "growth_stage_filter": "Mature",
  "notes": "optional"
}
```
`zone_override` and `growth_stage_filter` are optional (NULL = applies to all).

#### `PUT /programme/<id>`
Partial update. Only fields present in the body are changed. Updatable fields: `interval_weeks`, `rate_kg_per_ha`, `zone_override`, `growth_stage_filter`, `notes`.

#### `DELETE /programme/<id>`
Soft-delete — sets `is_active = false`. The step is excluded from future schedule generation but historical schedule rows are preserved.

---

### Schedule Generation

#### `POST /generate` · `POST /schedule/generate`
Runs the scheduling engine for one estate. Both paths are identical — same handler, same body.

**Body**
```json
{ "estate_id": "<uuid>" }
```

**Response**
```json
{
  "message": "Schedule generated",
  "estate_id": "...",
  "inserted": 42,
  "skipped_existing": 5,
  "skipped_area": 1,
  "skipped_recent": 3
}
```

Idempotent — safe to call multiple times. Already-open entries are counted under `skipped_existing`. Entries that already exist with status `done` or `skipped` are also skipped silently via `ON CONFLICT (block_id, programme_id, due_date) DO NOTHING` — this prevents a unique-constraint error on re-generation after entries have been closed.

---

### Schedule View & Status

#### `GET /schedule?estate_id=&block_id=&status=&limit=`
List schedule entries. `status` accepts comma-separated values (e.g. `due,overdue`). Default limit 200, max 500.

**Response** — array of entries with block code, estate, fertilizer details, `due_date`, `status`, `scheduled_rate_kg_per_ha`, and `total_kg_needed` (rate × block area).

#### `PUT /schedule/<id>`
Mark a schedule entry as `done` or `skipped`.

**Body**
```json
{ "status": "done", "actual_application_id": "<uuid>" }
```
`actual_application_id` is optional — if omitted, the existing value is preserved via `COALESCE`.

---

### Alerts

#### `GET /alerts?estate_id=<uuid>`
Returns all `pending` / `due` / `overdue` entries from `v_fertilizer_schedule_alerts`. Estate managers see only their own estate. Full-access roles see all four estates.

**Response fields include:** `estate`, `block_code`, `zone`, `growth_stage`, `fertilizer`, `npk_n`, `npk_k`, `due_date`, `status`, `scheduled_rate_kg_per_ha`, `total_kg_needed`, `days_overdue` (negative = days until due).

---

### Applications

#### `GET /applications?estate_id=&block_id=&limit=`
Application history across an estate or for a specific block. Default limit 200, max 500.

#### `POST /applications`
Record an actual field application.

**Body**
```json
{
  "block_id": "<uuid>",
  "fertilizer_type_id": "<uuid>",
  "application_date": "2026-06-08",
  "quantity_kg": 500.0,
  "rate_kg_per_ha": 200.0,
  "recommendation": "apply_now",
  "notes": "optional",
  "schedule_id": "<uuid>"
}
```

- `rate_kg_per_ha` — optional; backfilled automatically as `quantity_kg / block.area_hectares` if omitted and area is known.
- `applied_by` — optional UUID of the user who applied. Defaults to the JWT user's ID if not provided. Must be a valid user UUID if supplied.
- `schedule_id` — optional; if provided, the linked `fertilizer_schedule` entry is atomically marked `done` and `actual_application_id` is set.

#### `GET /history?block_id=<uuid>&limit=`
Full application history for a single block. Returns the same fields as `/applications` plus the linked schedule entry's `status` and `due_date` (LEFT JOIN on `fertilizer_schedule.actual_application_id`). Default limit 100, max 500. Returns 404 if the block does not exist.

---

## Seeded Programme Data (Migration 012)

51 programme rows across 4 estates, based on TRI SP03 mid-country recommendations:

| Estate | Zone | T0_200 apps/yr | U750 apps/yr | Other |
|---|---|---|---|---|
| Kundasale | Mid (920–950 m) | 3 (Mature) + 3 (Young) | 2 (Mature) | EP_GOLD ×2 (Immature), MOP ×1, Dolomite ×1 |
| Ramboda Heights | High (1380–1430 m) | 3 + 3 | 2 | EP_GOLD ×2, MOP ×1, Dolomite ×1 |
| Hunasgiriya | Low (575–640 m) | 4 + 4 | 2 | RPR ×1, EP_GOLD ×2, MOP ×1, Dolomite ×1 |
| Haputale Park | High (1470–1530 m) | 3 + 3 | 2 | EP_GOLD ×2, MOP ×1, Dolomite ×1 |

Hunasgiriya gets an extra T0_200 application and RPR (rock phosphate) because low-elevation soils have higher aluminium/iron coupling and faster nitrogen leaching from heavy rainfall.

---

## Role Access Summary

| Endpoint | `admin` / `estate_manager` | `manager` |
|---|---|---|
| GET catalogue, programme, schedule, alerts, history | All estates | Own estate only |
| POST / PUT / DELETE programme | ✅ | ❌ 403 |
| POST schedule generate | ✅ | ❌ 403 |
| PUT schedule entry | ✅ | ❌ 403 |
| POST applications | ✅ | ❌ 403 |

---

## Frontend Integration

### `frontend/app/api/apiService.js`

All fertilizer calls go through the `_fertilizer(token, method, path, body)` helper, which follows the same pattern as `_labour` and `_water`: injects the Bearer token, handles 401 globally via `_onUnauthorized`, and throws on non-ok responses.

Exported methods:

| Method | Endpoint |
|---|---|
| `getFertilizerAlerts(token, estateId)` | `GET /alerts` |
| `getFertilizerSchedule(token, { estateId, blockId, status, limit })` | `GET /schedule` |
| `getFertilizerProgramme(token, estateId)` | `GET /programme` |
| `getFertilizerTypes(token)` | `GET /types` |
| `generateFertilizerSchedule(token, estateId)` | `POST /generate` |
| `updateFertilizerScheduleEntry(token, id, data)` | `PUT /schedule/<id>` |
| `recordFertilizerApplication(token, data)` | `POST /applications` |
| `getFertilizerApplications(token, { estateId, blockId, limit })` | `GET /applications` |
| `getFertilizerHistory(token, blockId, limit)` | `GET /history` |
| `createFertilizerProgrammeStep(token, data)` | `POST /programme` |
| `updateFertilizerProgrammeStep(token, id, data)` | `PUT /programme/<id>` |
| `deleteFertilizerProgrammeStep(token, id)` | `DELETE /programme/<id>` |

### `frontend/app/dashboard/page.jsx` — `FertilizerTab`

The `FertilizerTab` component replaced the previous mock-data block grid entirely.

**State:**
- `estateId` — selected estate; pre-populated from `getEstates` on mount
- `alerts` — result of `getFertilizerAlerts` for the selected estate
- `schedule` — result of `getFertilizerSchedule` filtered by `scheduleStatus`
- `scheduleStatus` — dropdown filter; defaults to `""` (all entries)
- `genResult` — success payload from the last `generateFertilizerSchedule` call

**Layout (top to bottom):**
1. Estate selector + Generate Schedule button (button hidden for `manager` role via `canWrite`)
2. Success/error banners
3. KPI cards — overdue / due / pending / total alerts (all live from the alerts API)
4. Overdue danger alert banner (shown only when `overdueCount > 0`)
5. Active Alerts table — columns: Block, Zone, Fertilizer, Due Date, Status, Total Kg, Rate kg/ha
6. Schedule table — columns: Block, Fertilizer, Due Date, Status, Rate kg/ha, Total Kg, Actions
   - Status filter dropdown (All / Due & Overdue / Pending / Done / Skipped)
   - Done / Skip inline action buttons on open entries (hidden for `manager` role)
7. Empty state card when both alerts and schedule are empty

**Data reload:** both `handleGenerate` and `handleUpdateEntry` call a shared `reload()` helper that re-fetches alerts and schedule in parallel after a mutation.

### `frontend/app/dashboard/page.jsx` — `OverviewTab`

The static `fertilizerBlocks` mock array was removed. `OverviewTab` now calls `getFertilizerAlerts(token)` (no estate filter — full-access users see all estates) on mount and stores results in `fertAlerts`.

The fertilizer alerts card shows only `due` and `overdue` entries as block cards. `pending` entries are mapped to `ok` status and filtered out of the attention list. The overdue count badge is live.

### `frontend/app/dashboard/page.jsx` — `DashboardPage`

`DashboardPage` loads `getFertilizerAlerts(token)` on mount to populate `fertOverdueCount` for the sidebar badge. The badge is hidden when the count is zero.

---

## Adding to the Monthly Cron

If auto-generation on a schedule is needed, the pattern from the labour module applies: add a job to `scheduler.py` that calls `_run_generate_schedule(estate_id)` for each estate, the same way `generate_monthly_plans` is called for labour plans.
