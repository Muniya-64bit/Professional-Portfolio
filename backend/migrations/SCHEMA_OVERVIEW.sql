-- =============================================================================
-- KVPL Database - Entity Relationship Overview
-- =============================================================================
-- This file documents the database structure and relationships

-- =============================================================================
-- DATABASE SCHEMA DIAGRAM
-- =============================================================================

/*
CORE ENTITIES
=============

┌─────────────┐         ┌──────────────┐
│   estate    │◄────┐   │   factory    │
│   ──────    │     │   │   ───────    │
│ • id (PK)   │     └───┤ • id (PK)    │
│ • name      │         │ • estate_id  │
│ • region    │         │ • name       │
│ • blocks    │         │ • location   │
└─────────────┘         └──────────────┘
        │
        │ has many
        ▼
    ┌─────────┐
    │  block  │
    │ ─────── │
    │ • id    │
    │ • code  │
    │ • soil  │
    │ • area  │
    └─────────┘
        ▲
        │ located in
        │
    ┌──────────┐
    │   user   │
    │ ──────── │
    │ • id (PK)│
    │ • name   │
    │ • email  │
    │ • role   │
    │ • active │
    └──────────┘

MODULES
=======

MODULE 1: Fertilizer Rotation
──────────────────────────────
    ┌──────────────────┐
    │ fertilizer_type  │
    ├──────────────────┤
    │ • id (PK)        │
    │ • code (UNIQUE)  │
    │ • name           │
    │ • default_dose   │
    └──────────────────┘
            ▲
            │ references
            │
    ┌──────────────────────┐      ┌──────────────────────┐
    │ fertilizer_          │      │ fertilizer_          │
    │ application          │      │ recommendation       │
    ├──────────────────────┤      ├──────────────────────┤
    │ • id (PK)            │      │ • id (PK)            │
    │ • block_id (FK)      │      │ • block_id (FK)      │
    │ • fert_type_id (FK)  │      │ • generated_by (FK)  │
    │ • applied_by (FK)    │      │ • recommended_for    │
    │ • application_date   │      │ • action             │
    │ • quantity_kg        │      │ • is_overridden      │
    │ • recommendation     │      │ • rationale          │
    │ • notes              │      └──────────────────────┘
    └──────────────────────┘

MODULE 2: Input Cost vs Yield ROI
─────────────────────────────────
    ┌──────────────────┐
    │  input_cost      │      ┌──────────────────┐
    ├──────────────────┤      │  yield_record    │
    │ • id (PK)        │      ├──────────────────┤
    │ • estate_id (FK) │      │ • id (PK)        │
    │ • year           │      │ • estate_id (FK) │
    │ • month          │      │ • year           │
    │ • fert_cost_lkr  │      │ • month          │
    │ • chem_cost_lkr  │      │ • yield_kg       │
    │ • labour_cost    │      │ • source         │
    │ • other_cost     │      └──────────────────┘
    │ • total_cost     │
    │   (generated)    │
    └──────────────────┘
            ▲ ▲                      ▲ ▲
            │ │ combined for ROI     │ │
            └─┴──────────────────────┴─┘
                    │
                    ▼
        ┌──────────────────────┐
        │  roi_snapshot        │
        ├──────────────────────┤
        │ • id (PK)            │
        │ • estate_id (FK)     │
        │ • year               │
        │ • month              │
        │ • cost_per_kg        │
        │ • rank               │
        │ • is_flagged         │
        │ • flag_reason        │
        └──────────────────────┘

MODULE 3: Water Usage Efficiency
────────────────────────────────
    ┌──────────────────────┐
    │  water_baseline      │
    ├──────────────────────┤
    │ • id (PK)            │
    │ • factory_id (FK)    │
    │ • baseline_year      │
    │ • baseline_intensity │
    │ • annual_target_pct  │
    │ • set_by (FK)        │
    └──────────────────────┘
            ▲
            │ defines target for
            │
    ┌──────────────────────┐
    │  water_usage         │
    ├──────────────────────┤
    │ • id (PK)            │
    │ • factory_id (FK)    │
    │ • year               │
    │ • month              │
    │ • water_m3           │
    │ • yield_kg           │
    │ • intensity          │
    │   (m3/kg, generated) │
    │ • track_status       │
    └──────────────────────┘

MODULE 4: Labour Allocation
──────────────────────────
    ┌──────────────────────┐
    │  labour_plan         │
    ├──────────────────────┤
    │ • id (PK)            │
    │ • estate_id (FK)     │
    │ • created_by (FK)    │
    │ • week_start         │
    │ • total_workers      │
    │ • target_kg          │
    │ • status             │
    │ • notes              │
    └──────────────────────┘
            │ contains
            │
            ▼
    ┌──────────────────────┐
    │  block_allocation    │
    ├──────────────────────┤
    │ • id (PK)            │
    │ • labour_plan_id(FK) │
    │ • block_id (FK)      │
    │ • allocated_workers  │
    │ • expected_yield_kg  │
    │ • actual_yield_kg    │
    │ • plucking_rounds    │
    │ • productivity_ratio │
    └──────────────────────┘

CROSS-MODULE
═════════════
    ┌──────────────────────┐
    │  audit_log           │
    ├──────────────────────┤
    │ • id (BIGSERIAL)     │
    │ • user_id (FK)       │
    │ • table_name         │
    │ • record_id          │
    │ • action (I/U/D)     │
    │ • old_data (JSONB)   │
    │ • new_data (JSONB)   │
    │ • changed_at         │
    └──────────────────────┘

*/

-- =============================================================================
-- SAMPLE RELATIONSHIPS
-- =============================================================================

/*
Data Flow Example:
─────────────────

1. Create Estate
   CREATE estate → "Kundasale Estate"

2. Add Blocks
   CREATE block → A1, A2, B1 (belong to Kundasale)

3. Apply Fertilizer
   CREATE fertilizer_application → Applied T0_200 to block A1
   → Inserted to audit_log (INSERT action)

4. Record Costs & Yield
   CREATE input_cost → Jan 2026: 585,000 LKR total
   CREATE yield_record → Jan 2026: 2,150,000 kg

5. Calculate ROI
   CREATE roi_snapshot → cost_per_kg = 0.2722 LKR/kg
   → Ranked against other estates

6. Track Water
   CREATE water_usage → 6,750 m³ used for 2,150 kg
   → intensity = 3.14 m³/kg vs baseline of 3.5

7. Plan Labour
   CREATE labour_plan → Week Jan 6: 450 workers
   CREATE block_allocation → 75 workers to block A1
   → Expected yield: 85,000 kg

8. Audit Trail
   Multiple INSERT/UPDATE/DELETE actions
   → All tracked in audit_log with old/new JSON data

*/

-- =============================================================================
-- KEY RELATIONSHIPS & CONSTRAINTS
-- =============================================================================

/*
Primary Key Relationships:
──────────────────────────

CORE ENTITIES:
  estate ◄─────────────────────┐
    └─► factory                │
    └─► block                  │
        └─► block_allocation   │
            └─► labour_plan    │
    └─► user                   │
    └─► input_cost            │ All reference
    └─► yield_record          │ estate or
    └─► roi_snapshot          │ child tables
    └─► labour_plan           │
                              │
CROSS-REFERENCES:            │
  fertilizer_application ────┘
  fertilizer_recommendation  │
  water_usage (→factory)     │
  water_baseline             │
  audit_log (→user)          │

REFERENTIAL INTEGRITY:
  • CASCADE DELETE on estate → removes all child data
  • SET NULL on user delete → preserves data relationships
  • UNIQUE constraints on (estate_id, block_code)
  • UNIQUE constraints on monthly records (estate_id, year, month)

COMPUTED COLUMNS:
  • input_cost.total_cost_lkr = GENERATED AS (fert + chem + labour + other)
  • water_usage.intensity = GENERATED AS (water_m3 / yield_kg)

*/

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

/*
Query Performance Indexes:
──────────────────────────

Block Lookups:
  idx_block_estate → (estate_id)
  → Fast: SELECT * FROM block WHERE estate_id = X

Fertilizer Module:
  idx_fert_app_block → (block_id)
  idx_fert_app_date → (application_date DESC)
  idx_fert_rec_block → (block_id)
  idx_fert_rec_date → (recommended_for DESC)
  → Fast date range queries

ROI Module:
  idx_input_cost_period → (estate_id, year, month)
  idx_yield_record_period → (estate_id, year, month)
  idx_roi_period → (year, month)
  idx_roi_flagged → (is_flagged WHERE is_flagged = TRUE)
  → Fast: Current month queries, flagged record lookup

Water Module:
  idx_water_factory → (factory_id, year, month)
  idx_water_status → (track_status)
  → Fast: Water efficiency dashboard

Labour Module:
  idx_labour_plan_estate → (estate_id, week_start DESC)
  idx_block_alloc_plan → (labour_plan_id)
  → Fast: Weekly plan lookups

Audit Module:
  idx_audit_table → (table_name, record_id)
  idx_audit_user → (user_id)
  idx_audit_time → (changed_at DESC)
  → Fast: Audit trail queries, compliance reports

*/

-- =============================================================================
-- VIEWS FOR REPORTING
-- =============================================================================

/*
Pre-Built Reporting Views:
───────────────────────────

v_roi_current_month
  SELECT estate, year, month, cost_per_kg, rank, is_flagged, flag_reason
  FROM roi_snapshot WHERE (year, month) = (current top month)
  ORDER BY rank
  ► Use: Dashboard, ROI rankings, anomaly detection

v_water_status_latest
  SELECT factory, estate, year, month, water_m3, yield_kg, 
         intensity_m3_per_kg, baseline_intensity, track_status
  FROM water_usage + water_baseline
  WHERE (year, month) = (current top month)
  ► Use: Water dashboard, efficiency tracking, alerts

v_block_fert_summary
  SELECT block_code, estate, fertilizer, applications, 
         total_kg, last_applied
  FROM fertilizer_application (last 12 months)
  GROUP BY block, fertilizer
  ► Use: Fertilizer usage reports, compliance tracking

*/

-- =============================================================================
-- DATA TYPES & VALIDATION
-- =============================================================================

/*
Key Data Types:
───────────────

IDs:
  UUID DEFAULT uuid_generate_v4() → Globally unique, safer than auto-increment

Numeric:
  DECIMAL(14, 2) for money → LKR currency with 2 decimal places
  DECIMAL(8, 2) for area → hectares with precision
  DECIMAL(10, 4) for intensity → m³/kg with 4 decimal precision

Dates:
  DATE → Application dates, week starts
  TIMESTAMP DEFAULT NOW() → Audit trail, created/updated

Enums (CHECK constraints):
  role: 'admin', 'estate_manager', 'field_supervisor', 
        'factory_manager', 'finance', 'agronomist'
  
  action (recommendations): 'apply_now', 'delay', 'increase_dosage'
  action (audit): 'INSERT', 'UPDATE', 'DELETE'
  status (labour): 'draft', 'published', 'completed'
  track_status: 'on_track', 'at_risk', 'off_track'

JSON:
  JSONB old_data, new_data → Flexible audit trail storage

Text:
  VARCHAR(50) for codes (unique identifiers)
  VARCHAR(150) for names
  TEXT for descriptions and notes

*/

-- =============================================================================
-- SAMPLE QUERY PATTERNS
-- =============================================================================

/*
Common Query Patterns:
──────────────────────

1. TIMESERIES AGGREGATION
   SELECT year, month, SUM(quantity_kg) 
   FROM fertilizer_application GROUP BY year, month
   ► Usage: Fertilizer usage trends

2. RANKING
   SELECT ROW_NUMBER() OVER (PARTITION BY year, month ORDER BY cost_per_kg)
   FROM roi_snapshot
   ► Usage: Estate rankings, top/bottom performers

3. JOINS WITH AGGREGATION
   SELECT e.name, COUNT(DISTINCT b.id), SUM(b.area_hectares)
   FROM estate e LEFT JOIN block b ON e.id = b.estate_id
   GROUP BY e.name
   ► Usage: Estate summary statistics

4. WINDOW FUNCTIONS
   SELECT *, LAG(yield_kg) OVER (ORDER BY month) AS prev_yield
   FROM yield_record WHERE estate_id = X
   ► Usage: Month-over-month analysis

5. JSON QUERYING
   SELECT * FROM audit_log 
   WHERE new_data @> '{"is_flagged": true}'::jsonb
   ► Usage: Audit trail searches

*/

-- =============================================================================
-- END OF OVERVIEW
-- =============================================================================
