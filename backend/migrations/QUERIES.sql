-- =============================================================================
-- KVPL Database - Common Queries Reference
-- Quick access to frequently needed SQL queries for KVPL operations
-- =============================================================================

-- =============================================================================
-- MODULE 1: FERTILIZER ROTATION PLANNER
-- =============================================================================

-- Get fertilizer types
SELECT id, code, name, default_dosage_kg 
FROM fertilizer_type 
ORDER BY code;

-- Get application history for a block (last 30 days)
SELECT 
    fa.application_date,
    ft.code,
    ft.name,
    fa.quantity_kg,
    u.name AS applied_by,
    fa.notes
FROM fertilizer_application fa
JOIN block b ON fa.block_id = b.id
JOIN fertilizer_type ft ON fa.fertilizer_type_id = ft.id
LEFT JOIN "user" u ON fa.applied_by = u.id
WHERE b.block_code = 'A1'
  AND fa.application_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY fa.application_date DESC;

-- Get pending fertilizer recommendations
SELECT 
    fr.recommended_for,
    fr.action,
    b.block_code,
    e.name AS estate,
    fr.rationale,
    u.name AS generated_by
FROM fertilizer_recommendation fr
JOIN block b ON fr.block_id = b.id
JOIN estate e ON b.estate_id = e.id
LEFT JOIN "user" u ON fr.generated_by = u.id
WHERE NOT fr.is_overridden
  AND fr.recommended_for <= CURRENT_DATE
ORDER BY fr.recommended_for;

-- Override a recommendation
UPDATE fertilizer_recommendation 
SET 
    is_overridden = TRUE,
    override_reason = 'Delayed due to rain forecast',
    overridden_by = (SELECT id FROM "user" WHERE email = 'agronomist@kvpl.com' LIMIT 1),
    overridden_at = NOW()
WHERE id = 'RECOMMENDATION_UUID_HERE';

-- =============================================================================
-- MODULE 2: INPUT COST VS YIELD ROI CALCULATOR
-- =============================================================================

-- View ROI rankings for current month
SELECT * FROM v_roi_current_month;

-- Get cost breakdown for an estate (specific month)
SELECT 
    year,
    month,
    fertilizer_cost_lkr,
    chemical_cost_lkr,
    labour_input_cost_lkr,
    other_cost_lkr,
    total_cost_lkr
FROM input_cost
WHERE estate_id = (SELECT id FROM estate WHERE name = 'Kundasale Estate')
  AND year = 2026
  AND month = 5;

-- Calculate ROI for an estate over time
SELECT 
    ic.year,
    ic.month,
    ic.total_cost_lkr,
    yr.yield_kg,
    ROUND((ic.total_cost_lkr / yr.yield_kg)::NUMERIC, 4) AS cost_per_kg,
    ROUND((yr.yield_kg / (ic.total_cost_lkr / 1000))::NUMERIC, 2) AS kg_per_1000_lkr
FROM input_cost ic
JOIN yield_record yr ON ic.estate_id = yr.estate_id 
    AND ic.year = yr.year 
    AND ic.month = yr.month
WHERE ic.estate_id = (SELECT id FROM estate WHERE name = 'Kundasale Estate')
ORDER BY ic.year DESC, ic.month DESC;

-- Get flagged ROI snapshots (anomalies)
SELECT 
    e.name AS estate,
    r.year,
    r.month,
    r.cost_per_kg,
    r.rank,
    r.flag_reason
FROM roi_snapshot r
JOIN estate e ON r.estate_id = e.id
WHERE r.is_flagged = TRUE
ORDER BY r.computed_at DESC;

-- =============================================================================
-- MODULE 3: WATER USAGE EFFICIENCY REPORT
-- =============================================================================

-- View water status for all factories (latest month)
SELECT * FROM v_water_status_latest;

-- Get water usage trend for a factory
SELECT 
    f.name,
    w.year,
    w.month,
    w.water_m3,
    w.yield_kg,
    w.intensity AS m3_per_kg,
    wb.baseline_intensity,
    ROUND(((w.intensity - wb.baseline_intensity) / wb.baseline_intensity * 100)::NUMERIC, 2) AS pct_vs_baseline,
    w.track_status
FROM water_usage w
JOIN factory f ON w.factory_id = f.id
LEFT JOIN water_baseline wb ON w.factory_id = wb.factory_id
WHERE f.name = 'Kundasale Processing Plant'
ORDER BY w.year DESC, w.month DESC;

-- Set water baseline for a factory
INSERT INTO water_baseline (factory_id, baseline_year, baseline_intensity, annual_target_pct, set_by)
SELECT 
    f.id,
    2023,
    3.5,
    2.0,
    u.id
FROM factory f
JOIN estate e ON f.estate_id = e.id
JOIN "user" u ON u.role = 'factory_manager' AND u.estate_id = e.id
WHERE f.name = 'Kundasale Processing Plant'
ON CONFLICT (factory_id) DO UPDATE
SET 
    baseline_intensity = EXCLUDED.baseline_intensity,
    set_at = NOW();

-- Calculate expected intensity based on baseline and target
SELECT 
    w.year,
    w.month,
    w.intensity,
    wb.baseline_intensity,
    (wb.baseline_intensity * POWER(1 - wb.annual_target_pct/100, w.year - wb.baseline_year + (w.month/12))) AS expected_intensity
FROM water_usage w
JOIN factory f ON w.factory_id = f.id
LEFT JOIN water_baseline wb ON w.factory_id = wb.factory_id
WHERE f.name = 'Kundasale Processing Plant';

-- =============================================================================
-- MODULE 4: LABOUR ALLOCATION OPTIMIZER (updated schema)
-- =============================================================================

-- Weekly labour plan summary with group headcount
SELECT
    lp.week_start,
    e.name                          AS estate,
    lp.total_workers,
    lp.target_kg,
    lp.status,
    COUNT(ba.id)                    AS blocks_assigned,
    SUM(ba.expected_yield_kg)       AS expected_total_yield,
    SUM(ba.actual_yield_kg)         AS actual_total_yield,
    rc.cycle_name,
    rc.current_round                AS rotation_round
FROM labour_plan lp
JOIN estate e           ON e.id  = lp.estate_id
LEFT JOIN block_assignment ba ON ba.labour_plan_id = lp.id
LEFT JOIN rotation_cycle rc   ON rc.estate_id = lp.estate_id AND rc.is_active = TRUE
WHERE lp.week_start = DATE_TRUNC('week', CURRENT_DATE)::DATE
GROUP BY lp.id, e.name, lp.week_start, lp.total_workers,
         lp.target_kg, lp.status, rc.cycle_name, rc.current_round;

-- Block assignments for a week: group, workers, yield
SELECT
    b.block_code,
    wg.group_name,
    wg.capacity                     AS group_size,
    ba.assignment_date,
    ba.rotation_round,
    ba.is_manual_override,
    ba.expected_yield_kg,
    ba.actual_yield_kg,
    ROUND(ba.actual_yield_kg / NULLIF(ba.expected_yield_kg, 0) * 100, 1) AS efficiency_pct,
    ba.status
FROM block_assignment ba
JOIN block b            ON b.id  = ba.block_id
JOIN worker_group wg    ON wg.id = ba.worker_group_id
WHERE ba.labour_plan_id = (
    SELECT id FROM labour_plan lp
    JOIN estate e ON e.id = lp.estate_id
    WHERE e.name = 'Kundasale Estate'
      AND lp.week_start = DATE_TRUNC('week', CURRENT_DATE)::DATE
)
ORDER BY b.block_code;

-- Rotation matrix: who goes where for all 6 rounds
SELECT
    rrb.round_number,
    b.block_code,
    wg.group_name,
    CASE WHEN rc.current_round = rrb.round_number THEN 'CURRENT' ELSE '' END AS current_week
FROM rotation_round_block rrb
JOIN rotation_cycle rc  ON rc.id  = rrb.rotation_cycle_id
JOIN block b            ON b.id   = rrb.block_id
JOIN worker_group wg    ON wg.id  = rrb.worker_group_id
WHERE rc.cycle_name = 'Kundasale Standard Rotation 2026'
ORDER BY rrb.round_number, b.block_code;

-- Active employees per group with headcount vs capacity
SELECT
    wg.group_code,
    wg.group_name,
    wg.capacity,
    COUNT(wgm.id)                               AS current_headcount,
    wg.capacity - COUNT(wgm.id)                 AS vacancy,
    sup.full_name                               AS supervisor
FROM worker_group wg
JOIN estate e               ON e.id  = wg.estate_id
LEFT JOIN worker_group_member wgm ON wgm.group_id   = wg.id AND wgm.is_active = TRUE
LEFT JOIN employee sup       ON sup.id = wg.supervisor_id
WHERE e.name = 'Kundasale Estate' AND wg.is_active = TRUE
GROUP BY wg.group_code, wg.group_name, wg.capacity, sup.full_name
ORDER BY wg.group_code;

-- Manual override: move a group to a different block
-- (API will execute this; shown here for reference)
UPDATE block_assignment
SET
    original_group_id  = worker_group_id,     -- save who was supposed to be here
    worker_group_id    = '<new_group_uuid>',
    is_manual_override = TRUE,
    override_reason    = 'Group 2 supervisor absent — swapping with Group 4',
    overridden_by      = '<manager_user_uuid>',
    overridden_at      = NOW(),
    updated_at         = NOW()
WHERE id = '<block_assignment_uuid>';

-- Manual add/remove individual employee from a block assignment
-- Add an extra worker
INSERT INTO employee_day_assignment (block_assignment_id, employee_id, assignment_type, added_by, reason)
VALUES ('<block_assignment_uuid>', '<employee_uuid>', 'manual_add', '<manager_uuid>', 'Replacing sick colleague');

-- Remove a worker (mark as absent)
INSERT INTO employee_day_assignment (block_assignment_id, employee_id, assignment_type, added_by, reason)
VALUES ('<block_assignment_uuid>', '<employee_uuid>', 'manual_remove', '<manager_uuid>', 'Medical leave');

-- Per-block productivity over past 4 weeks
SELECT
    b.block_code,
    COUNT(ba.id)                            AS weeks_plucked,
    ROUND(AVG(ba.actual_yield_kg), 0)       AS avg_actual_kg,
    ROUND(AVG(ba.expected_yield_kg), 0)     AS avg_target_kg,
    ROUND(AVG(ba.actual_yield_kg / NULLIF(ba.expected_yield_kg, 0)) * 100, 1) AS avg_efficiency_pct,
    SUM(ba.actual_yield_kg)                 AS total_kg_4_weeks
FROM block_assignment ba
JOIN block b ON b.id = ba.block_id
WHERE ba.assignment_date >= CURRENT_DATE - INTERVAL '4 weeks'
  AND ba.status = 'completed'
GROUP BY b.block_code
ORDER BY avg_efficiency_pct DESC;

-- =============================================================================
-- CROSS-MODULE QUERIES
-- =============================================================================

-- Get complete monthly summary for an estate
SELECT 
    e.name,
    ic.year,
    ic.month,
    ic.total_cost_lkr,
    yr.yield_kg,
    ROUND((ic.total_cost_lkr / yr.yield_kg)::NUMERIC, 4) AS cost_per_kg,
    COUNT(DISTINCT fa.id) AS fertilizer_applications,
    COUNT(DISTINCT lp.id) AS labour_plans,
    r.rank AS roi_rank,
    r.is_flagged
FROM estate e
LEFT JOIN input_cost ic ON e.id = ic.estate_id
LEFT JOIN yield_record yr ON e.id = yr.estate_id 
    AND ic.year = yr.year AND ic.month = yr.month
LEFT JOIN fertilizer_application fa ON e.id IN (
    SELECT estate_id FROM block WHERE block.id = fa.block_id
) AND fa.application_date >= MAKE_DATE(ic.year, ic.month, 1)
    AND fa.application_date < MAKE_DATE(ic.year, ic.month, 1) + INTERVAL '1 month'
LEFT JOIN labour_plan lp ON e.id = lp.estate_id 
    AND lp.week_start >= MAKE_DATE(ic.year, ic.month, 1)
    AND lp.week_start < MAKE_DATE(ic.year, ic.month, 1) + INTERVAL '1 month'
LEFT JOIN roi_snapshot r ON e.id = r.estate_id 
    AND ic.year = r.year AND ic.month = r.month
WHERE e.name = 'Kundasale Estate'
  AND ic.year = 2026
GROUP BY e.name, ic.year, ic.month, ic.total_cost_lkr, yr.yield_kg, r.rank, r.is_flagged;

-- =============================================================================
-- AUDIT & COMPLIANCE
-- =============================================================================

-- Get audit trail for a specific user
SELECT 
    al.changed_at,
    al.table_name,
    al.action,
    al.old_data,
    al.new_data
FROM audit_log al
WHERE al.user_id = (SELECT id FROM "user" WHERE email = 'admin@kvpl.com' LIMIT 1)
ORDER BY al.changed_at DESC
LIMIT 50;

-- Get changes to a specific record
SELECT 
    al.changed_at,
    u.name AS changed_by,
    al.action,
    al.old_data,
    al.new_data
FROM audit_log al
LEFT JOIN "user" u ON al.user_id = u.id
WHERE al.table_name = 'input_cost'
  AND al.record_id = 'RECORD_UUID_HERE'
ORDER BY al.changed_at DESC;

-- =============================================================================
-- USER MANAGEMENT
-- =============================================================================

-- Get active users by role
SELECT 
    role,
    COUNT(*) AS count,
    COUNT(*) FILTER (WHERE is_active = TRUE) AS active
FROM "user"
GROUP BY role
ORDER BY role;

-- Get users and their assigned estates
SELECT 
    u.name,
    u.email,
    u.role,
    e.name AS estate,
    u.is_active
FROM "user" u
LEFT JOIN estate e ON u.estate_id = e.id
ORDER BY u.role, u.name;

-- Deactivate a user
UPDATE "user" 
SET is_active = FALSE 
WHERE email = 'user@kvpl.com';

-- =============================================================================
-- MAINTENANCE QUERIES
-- =============================================================================

-- Get database size statistics
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Count records in each table
SELECT 
    schemaname,
    tablename,
    n_live_tup AS row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;

-- Check for missing data
SELECT 
    'fertilizer_applications missing fertilizer_type' AS issue
FROM fertilizer_application fa
WHERE fertilizer_type_id NOT IN (SELECT id FROM fertilizer_type)
UNION ALL
SELECT 'users with invalid roles'
FROM "user" u
WHERE u.role NOT IN ('admin', 'estate_manager', 'field_supervisor', 'factory_manager', 'finance', 'agronomist');
