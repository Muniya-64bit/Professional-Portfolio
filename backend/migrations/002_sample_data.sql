-- =============================================================================
-- KVPL Input & Resource Optimization System
-- Sample Data — PostgreSQL
-- =============================================================================

-- =============================================================================
-- SAMPLE DATA: ESTATES & FACTORIES
-- =============================================================================

-- Insert Estates
INSERT INTO estate (name, region, total_blocks) VALUES
    ('Kundasale Estate', 'Central', 12),
    ('Ramboda Heights', 'Central', 8),
    ('Hunasgiriya Estate', 'Western', 15),
    ('Haputale Park', 'Uva', 10);

-- Get estate IDs for reference
WITH estate_ids AS (
    SELECT id, name FROM estate
    WHERE name IN ('Kundasale Estate', 'Ramboda Heights', 'Hunasgiriya Estate', 'Haputale Park')
),

-- Insert Factories
factories_insert AS (
    INSERT INTO factory (estate_id, name, location)
    SELECT 
        e1.id,
        'Kundasale Processing Plant',
        'Kundasale Town'
    FROM (SELECT id FROM estate WHERE name = 'Kundasale Estate') e1
    UNION ALL
    SELECT 
        e2.id,
        'Ramboda Tea Factory',
        'Ramboda Junction'
    FROM (SELECT id FROM estate WHERE name = 'Ramboda Heights') e2
    UNION ALL
    SELECT 
        e3.id,
        'Western Region Mill',
        'Hunasgiriya Station'
    FROM (SELECT id FROM estate WHERE name = 'Hunasgiriya Estate') e3
    UNION ALL
    SELECT 
        e4.id,
        'Haputale Processing Unit',
        'Haputale Town'
    FROM (SELECT id FROM estate WHERE name = 'Haputale Park') e4
    RETURNING estate_id
)

-- Insert Users (Admin, Managers, Supervisors)
INSERT INTO "user" (estate_id, name, email, role, is_active) 
SELECT 
    e.id,
    'Admin User',
    'admin@kvpl.com',
    'admin',
    TRUE
FROM estate e WHERE e.name = 'Kundasale Estate'
UNION ALL
SELECT 
    e.id,
    'Estate Manager - Kundasale',
    'manager.kundasale@kvpl.com',
    'estate_manager',
    TRUE
FROM estate e WHERE e.name = 'Kundasale Estate'
UNION ALL
SELECT 
    e.id,
    'Field Supervisor - Block A',
    'supervisor.a@kvpl.com',
    'field_supervisor',
    TRUE
FROM estate e WHERE e.name = 'Kundasale Estate'
UNION ALL
SELECT 
    e.id,
    'Agronomist - Central Region',
    'agronomist.central@kvpl.com',
    'agronomist',
    TRUE
FROM estate e WHERE e.name = 'Kundasale Estate'
UNION ALL
SELECT 
    e.id,
    'Finance Officer',
    'finance@kvpl.com',
    'finance',
    TRUE
FROM estate e WHERE e.name = 'Kundasale Estate'
UNION ALL
SELECT 
    e.id,
    'Estate Manager - Ramboda',
    'manager.ramboda@kvpl.com',
    'estate_manager',
    TRUE
FROM estate e WHERE e.name = 'Ramboda Heights'
UNION ALL
SELECT 
    e.id,
    'Factory Manager - Kundasale',
    'factory.manager@kvpl.com',
    'factory_manager',
    TRUE
FROM estate e WHERE e.name = 'Kundasale Estate'
UNION ALL
SELECT 
    e.id,
    'Estate Manager - Hunasgiriya',
    'manager.hunasgiriya@kvpl.com',
    'estate_manager',
    TRUE
FROM estate e WHERE e.name = 'Hunasgiriya Estate';

-- =============================================================================
-- SAMPLE DATA: BLOCKS
-- =============================================================================

INSERT INTO block (estate_id, block_code, soil_type, growth_stage, area_hectares)
SELECT 
    e.id,
    block_code,
    soil_type,
    growth_stage,
    area_hectares
FROM estate e,
    (VALUES
        ('A1', 'Laterite', 'Mature', 2.5),
        ('A2', 'Laterite', 'Young', 2.0),
        ('B1', 'Red Loam', 'Mature', 3.0),
        ('B2', 'Red Loam', 'Mature', 2.8),
        ('C1', 'Laterite', 'Immature', 1.5),
        ('D1', 'Red Loam', 'Mature', 3.5)
    ) AS blocks(block_code, soil_type, growth_stage, area_hectares)
WHERE e.name = 'Kundasale Estate';

INSERT INTO block (estate_id, block_code, soil_type, growth_stage, area_hectares)
SELECT 
    e.id,
    block_code,
    soil_type,
    growth_stage,
    area_hectares
FROM estate e,
    (VALUES
        ('E1', 'Laterite', 'Mature', 2.0),
        ('E2', 'Red Loam', 'Mature', 2.5),
        ('F1', 'Laterite', 'Young', 1.8)
    ) AS blocks(block_code, soil_type, growth_stage, area_hectares)
WHERE e.name = 'Ramboda Heights';

-- =============================================================================
-- SAMPLE DATA: FERTILIZER APPLICATIONS
-- =============================================================================

INSERT INTO fertilizer_application (block_id, fertilizer_type_id, applied_by, application_date, quantity_kg, recommendation, notes)
SELECT 
    b.id,
    ft.id,
    u.id,
    app_date,
    quantity,
    'apply_now',
    notes
FROM 
    block b
    JOIN estate e ON b.estate_id = e.id
    JOIN fertilizer_type ft ON ft.code IN ('T0_200', 'U750', 'EP_GOLD', 'MOP')
    JOIN "user" u ON u.role = 'field_supervisor' AND u.estate_id = e.id,
    (VALUES
        ('2026-01-15'::DATE, 'T0_200', 150, 'Pre-plucking application'),
        ('2026-02-10'::DATE, 'U750', 500, 'Regular feeding'),
        ('2026-03-05'::DATE, 'EP_GOLD', 120, 'Balanced nutrition'),
        ('2026-04-20'::DATE, 'MOP', 80, 'Potassium boost for young leaves')
    ) AS app_data(app_date, fert_code, quantity, notes)
WHERE 
    b.block_code = 'A1' 
    AND ft.code = 'T0_200' AND app_date >= CURRENT_DATE - INTERVAL '5 months'
LIMIT 1;

-- =============================================================================
-- SAMPLE DATA: INPUT COSTS
-- =============================================================================

INSERT INTO input_cost (estate_id, year, month, fertilizer_cost_lkr, chemical_cost_lkr, labour_input_cost_lkr, other_cost_lkr, source)
SELECT 
    e.id,
    year,
    month,
    fertilizer_cost,
    chemical_cost,
    labour_cost,
    other_cost,
    'finance_upload'
FROM 
    estate e,
    (VALUES
        (2026, 1, 125000.00, 45000.00, 280000.00, 35000.00),
        (2026, 2, 135000.00, 48000.00, 290000.00, 38000.00),
        (2026, 3, 145000.00, 52000.00, 310000.00, 42000.00),
        (2026, 4, 155000.00, 55000.00, 320000.00, 45000.00),
        (2026, 5, 150000.00, 50000.00, 305000.00, 40000.00)
    ) AS costs(year, month, fertilizer_cost, chemical_cost, labour_cost, other_cost)
WHERE e.name = 'Kundasale Estate';

-- =============================================================================
-- SAMPLE DATA: YIELD RECORDS
-- =============================================================================

INSERT INTO yield_record (estate_id, year, month, yield_kg, source)
SELECT 
    e.id,
    year,
    month,
    yield_kg,
    'weighing_system'
FROM 
    estate e,
    (VALUES
        (2026, 1, 2150000.00),
        (2026, 2, 2280000.00),
        (2026, 3, 2420000.00),
        (2026, 4, 2350000.00),
        (2026, 5, 2410000.00)
    ) AS yields(year, month, yield_kg)
WHERE e.name = 'Kundasale Estate';

-- =============================================================================
-- SAMPLE DATA: ROI SNAPSHOTS
-- =============================================================================

INSERT INTO roi_snapshot (estate_id, year, month, cost_per_kg, rank, is_flagged, flag_reason)
SELECT 
    e.id,
    year,
    month,
    cost_per_kg,
    rank,
    is_flagged,
    flag_reason
FROM 
    estate e,
    (VALUES
        (2026, 1, 0.3142, 2, FALSE, NULL),
        (2026, 2, 0.2954, 1, FALSE, NULL),
        (2026, 3, 0.3301, 3, FALSE, NULL),
        (2026, 4, 0.3210, 2, TRUE, 'Cost per kg exceeded threshold by 5%'),
        (2026, 5, 0.3087, 2, FALSE, NULL)
    ) AS roi(year, month, cost_per_kg, rank, is_flagged, flag_reason)
WHERE e.name = 'Kundasale Estate';

-- =============================================================================
-- SAMPLE DATA: WATER BASELINE & USAGE
-- =============================================================================

INSERT INTO water_baseline (factory_id, baseline_year, baseline_intensity, annual_target_pct, set_by)
SELECT 
    f.id,
    2023,
    3.5,
    2.0,
    u.id
FROM 
    factory f
    JOIN estate e ON f.estate_id = e.id
    JOIN "user" u ON u.role = 'factory_manager' AND u.estate_id = e.id
WHERE e.name = 'Kundasale Estate'
LIMIT 1;

INSERT INTO water_usage (factory_id, year, month, water_m3, yield_kg, track_status)
SELECT 
    f.id,
    year,
    month,
    water_m3,
    yield_kg,
    track_status
FROM 
    factory f
    JOIN estate e ON f.estate_id = e.id,
    (VALUES
        (2026, 1, 6750.5, 2150000.00, 'on_track'),
        (2026, 2, 6825.3, 2280000.00, 'on_track'),
        (2026, 3, 7100.2, 2420000.00, 'at_risk'),
        (2026, 4, 7050.1, 2350000.00, 'on_track'),
        (2026, 5, 6900.8, 2410000.00, 'on_track')
    ) AS water_data(year, month, water_m3, yield_kg, track_status)
WHERE e.name = 'Kundasale Estate';

-- =============================================================================
-- SAMPLE DATA: LABOUR PLANS & ALLOCATIONS
-- =============================================================================

INSERT INTO labour_plan (estate_id, created_by, week_start, total_workers, target_kg, status, notes)
SELECT 
    e.id,
    u.id,
    week_start,
    total_workers,
    target_kg,
    'published',
    notes
FROM 
    estate e
    JOIN "user" u ON u.role = 'estate_manager' AND u.estate_id = e.id,
    (VALUES
        ('2026-01-06'::DATE, 450, 85000, 'Regular weekly plan - Peak plucking season'),
        ('2026-01-13'::DATE, 455, 87000, 'Increased workforce for high yield'),
        ('2026-01-20'::DATE, 460, 90000, 'Maximum capacity deployment'),
        ('2026-01-27'::DATE, 450, 85000, 'Return to standard levels'),
        ('2026-02-03'::DATE, 440, 82000, 'Post-peak adjustment')
    ) AS labour(week_start, total_workers, target_kg, notes)
WHERE e.name = 'Kundasale Estate'
LIMIT 5;

INSERT INTO block_allocation (labour_plan_id, block_id, allocated_workers, expected_yield_kg, actual_yield_kg, plucking_rounds, productivity_ratio)
WITH block_data AS (
    SELECT 
        lp.id as labour_plan_id,
        b.id as block_id,
        ROW_NUMBER() OVER (PARTITION BY lp.id ORDER BY b.block_code) as rn
    FROM 
        labour_plan lp
        JOIN estate e ON lp.estate_id = e.id
        JOIN block b ON b.estate_id = e.id
    WHERE 
        b.block_code IN ('A1', 'A2', 'B1', 'B2', 'C1')
        AND e.name = 'Kundasale Estate'
        AND lp.week_start >= CURRENT_DATE - INTERVAL '5 months'
),
allocations AS (
    SELECT 
        labour_plan_id,
        block_id,
        rn,
        CASE rn
            WHEN 1 THEN 75 WHEN 2 THEN 65 WHEN 3 THEN 80 WHEN 4 THEN 70 ELSE 60
        END as allocated_workers,
        CASE rn
            WHEN 1 THEN 85000.0 WHEN 2 THEN 72000.0 WHEN 3 THEN 90000.0 WHEN 4 THEN 78000.0 ELSE 65000.0
        END as expected_yield,
        CASE rn
            WHEN 1 THEN 84500.0 WHEN 2 THEN 71200.0 WHEN 3 THEN 91200.0 WHEN 4 THEN 77800.0 ELSE 65300.0
        END as actual_yield,
        CASE rn
            WHEN 1 THEN 11.33 WHEN 2 THEN 10.95 WHEN 3 THEN 11.40 WHEN 4 THEN 11.11 ELSE 10.88
        END as productivity_ratio
    FROM block_data
    WHERE rn <= 5
)
SELECT 
    labour_plan_id,
    block_id,
    allocated_workers,
    expected_yield,
    actual_yield,
    2 as plucking_rounds,
    productivity_ratio
FROM allocations;

-- =============================================================================
-- SAMPLE DATA: FERTILIZER RECOMMENDATIONS
-- =============================================================================

INSERT INTO fertilizer_recommendation (block_id, generated_by, recommended_for, action, rationale, is_overridden, override_reason, overridden_by, overridden_at)
SELECT 
    b.id,
    u.id,
    recommended_for,
    action,
    rationale,
    FALSE,
    NULL,
    NULL,
    NULL
FROM 
    block b
    JOIN estate e ON b.estate_id = e.id
    JOIN "user" u ON u.role = 'agronomist' AND u.estate_id = e.id,
    (VALUES
        ('2026-05-30'::DATE, 'apply_now', 'Block showing nitrogen deficiency signs after heavy rain'),
        ('2026-06-15'::DATE, 'increase_dosage', 'Young leaves emerging; higher potassium needed'),
        ('2026-07-01'::DATE, 'delay', 'Dry weather expected; defer application until moisture available')
    ) AS recs(recommended_for, action, rationale)
WHERE b.block_code = 'A1'
LIMIT 3;

-- =============================================================================
-- SAMPLE DATA: AUDIT LOG (Sample entries)
-- =============================================================================

INSERT INTO audit_log (user_id, table_name, record_id, action, new_data, changed_at)
SELECT 
    u.id,
    table_name,
    record_id::UUID,
    action,
    new_data,
    changed_at
FROM 
    (SELECT id FROM "user" WHERE role = 'admin' LIMIT 1) u,
    (VALUES
        ('input_cost', NULL::TEXT, 'INSERT', '{"estate": "Kundasale", "month": 5, "total_cost_lkr": 585000.00}'::JSONB, NOW() - INTERVAL '2 days'),
        ('yield_record', NULL::TEXT, 'INSERT', '{"estate": "Kundasale", "month": 5, "yield_kg": 2410000.00}'::JSONB, NOW() - INTERVAL '1 days'),
        ('water_usage', NULL::TEXT, 'UPDATE', '{"factory": "Kundasale Processing", "track_status": "on_track"}'::JSONB, NOW() - INTERVAL '6 hours')
    ) AS audit_data(table_name, record_id, action, new_data, changed_at);

-- =============================================================================
-- SUMMARY STATISTICS
-- =============================================================================

-- Display summary of inserted data
SELECT 'SAMPLE DATA LOADED SUCCESSFULLY' AS status;
SELECT 'Estates: ' || COUNT(*) FROM estate;
SELECT 'Users: ' || COUNT(*) FROM "user";
SELECT 'Blocks: ' || COUNT(*) FROM block;
SELECT 'Fertilizer Applications: ' || COUNT(*) FROM fertilizer_application;
SELECT 'Input Cost Records: ' || COUNT(*) FROM input_cost;
SELECT 'Yield Records: ' || COUNT(*) FROM yield_record;
SELECT 'Labour Plans: ' || COUNT(*) FROM labour_plan;
