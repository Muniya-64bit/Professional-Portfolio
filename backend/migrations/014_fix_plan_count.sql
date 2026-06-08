-- =============================================================================
-- KVPL — Fix plan count: keep exactly Jan–May 2026 per estate
-- Migration 014
--
-- Problem: the APScheduler (cron day=1 02:00) kept generating future plans
-- (June, July …) while the app was running, pushing each estate beyond the
-- 5 intended seed plans and advancing current_round past 6.
--
-- Fix:
--   1. Delete ALL labour_plans for the four estates (cascade → block_assignment).
--   2. Reset rotation current_round = 6 on every active cycle.
--   3. Re-insert the 5 clean monthly plans (Jan–May 2026) with their
--      block_assignments and yield-proportional allocated_workers.
--
-- This migration is fully idempotent — safe to run whether 013 succeeded,
-- partially ran, or left the database in any intermediate state.
-- =============================================================================


-- =============================================================================
-- 1. WIPE ALL PLANS FOR THESE ESTATES
--    ON DELETE CASCADE removes every linked block_assignment row.
-- =============================================================================

DELETE FROM labour_plan
WHERE estate_id IN (
    SELECT id FROM estate
    WHERE name IN ('Kundasale Estate','Ramboda Heights',
                   'Hunasgiriya Estate','Haputale Park')
);


-- =============================================================================
-- 2. RESET ROTATION current_round = 6
--    Scheduler-generated future plans had advanced the round counter.
--    Rounds 1–5 = Jan–May; round 6 is ready for the next real run.
-- =============================================================================

UPDATE rotation_cycle
SET    current_round = 6,
       updated_at    = NOW()
WHERE  is_active = TRUE
  AND  estate_id IN (
           SELECT id FROM estate
           WHERE name IN ('Kundasale Estate','Ramboda Heights',
                          'Hunasgiriya Estate','Haputale Park')
       );


-- =============================================================================
-- 3. RE-INSERT EXACTLY 5 MONTHLY PLANS (Jan–May 2026)
-- =============================================================================

INSERT INTO labour_plan
    (estate_id, created_by, period_start, total_workers, target_kg, status, notes)
WITH
    months AS (SELECT generate_series(1, 5) AS mo),
    mgrs AS (
        SELECT DISTINCT ON (e.id)
               e.id  AS estate_id,
               u.id  AS manager_id
        FROM   estate e
        JOIN   "user" u ON u.estate_id = e.id AND u.role = 'estate_manager'
        WHERE  e.name IN ('Kundasale Estate','Ramboda Heights',
                          'Hunasgiriya Estate','Haputale Park')
        ORDER  BY e.id, u.created_at
    ),
    emp_counts AS (
        SELECT estate_id, COUNT(*) AS total_emp
        FROM   employee WHERE is_active = TRUE
        GROUP  BY estate_id
    ),
    round_targets AS (
        SELECT m.estate_id, mo.mo,
               COALESCE(SUM(yp.predicted_yield_kg), 0) AS target_kg
        FROM   mgrs m
        CROSS  JOIN months mo
        JOIN   rotation_cycle rc ON rc.estate_id = m.estate_id AND rc.is_active = TRUE
        JOIN   rotation_round_block rrb
               ON rrb.rotation_cycle_id = rc.id AND rrb.round_number = mo.mo
        LEFT   JOIN yield_prediction yp
               ON yp.block_id = rrb.block_id AND yp.year = 2026 AND yp.month = mo.mo
        GROUP  BY m.estate_id, mo.mo
    )
SELECT
    m.estate_id,
    m.manager_id,
    MAKE_DATE(2026, mo.mo, 1)                               AS period_start,
    ec.total_emp                                             AS total_workers,
    COALESCE(rt.target_kg, 0)                               AS target_kg,
    CASE WHEN mo.mo <= 4 THEN 'completed' ELSE 'published' END AS status,
    'Monthly plan — round ' || mo.mo || ' — '
        || TO_CHAR(MAKE_DATE(2026, mo.mo, 1), 'Mon YYYY')   AS notes
FROM   mgrs m
CROSS  JOIN months mo
JOIN   emp_counts     ec ON ec.estate_id = m.estate_id
LEFT   JOIN round_targets rt
            ON rt.estate_id = m.estate_id AND rt.mo = mo.mo
ON CONFLICT (estate_id, period_start)
DO UPDATE SET
    total_workers = EXCLUDED.total_workers,
    target_kg     = EXCLUDED.target_kg,
    status        = EXCLUDED.status,
    notes         = EXCLUDED.notes;


-- =============================================================================
-- 4. RE-INSERT BLOCK_ASSIGNMENTS WITH SUPERVISOR-ANCHORED
--    YIELD-PROPORTIONAL allocated_workers
-- =============================================================================

INSERT INTO block_assignment (
    labour_plan_id, block_id, worker_group_id, assignment_date,
    rotation_cycle_id, rotation_round,
    expected_yield_kg, actual_yield_kg,
    allocated_workers, status
)
WITH
    plans AS (
        SELECT lp.id                                          AS plan_id,
               lp.estate_id,
               lp.period_start,
               lp.total_workers,
               lp.status                                      AS plan_status,
               EXTRACT(MONTH FROM lp.period_start)::INTEGER  AS mo
        FROM   labour_plan lp
        WHERE  lp.estate_id IN (
                   SELECT id FROM estate
                   WHERE name IN ('Kundasale Estate','Ramboda Heights',
                                  'Hunasgiriya Estate','Haputale Park')
               )
          AND  lp.period_start BETWEEN '2026-01-01' AND '2026-05-01'
    ),

    -- Supervisor count anchored to their primary block in each round
    sup_per_block AS (
        SELECT  p.plan_id,
                rrb.block_id,
                COUNT(e.id) AS sup_count
        FROM    plans p
        JOIN    rotation_cycle rc
                ON rc.estate_id = p.estate_id AND rc.is_active = TRUE
        JOIN    rotation_round_block rrb
                ON rrb.rotation_cycle_id = rc.id AND rrb.round_number = p.mo
        LEFT    JOIN worker_group_member wgm
                ON wgm.group_id = rrb.worker_group_id AND wgm.is_active = TRUE
        LEFT    JOIN employee e
                ON e.id = wgm.employee_id
               AND e.skill_type = 'supervisor'
               AND e.is_active  = TRUE
        GROUP   BY p.plan_id, rrb.block_id
    ),
    plan_sup_totals AS (
        SELECT plan_id, SUM(sup_count) AS total_sups
        FROM   sup_per_block
        GROUP  BY plan_id
    ),

    -- Raw assignments with yield predictions
    round_data AS (
        SELECT
            p.plan_id, p.estate_id, p.period_start,
            p.total_workers, p.plan_status, p.mo,
            rc.id                                            AS cycle_id,
            rrb.block_id,
            rrb.worker_group_id,
            COALESCE(yp.predicted_yield_kg, 0)              AS pred_yield,
            COALESCE(spb.sup_count, 0)                      AS sup_count,
            (p.total_workers - COALESCE(pst.total_sups, 0)) AS movable
        FROM   plans p
        JOIN   rotation_cycle rc
               ON rc.estate_id = p.estate_id AND rc.is_active = TRUE
        JOIN   rotation_round_block rrb
               ON rrb.rotation_cycle_id = rc.id AND rrb.round_number = p.mo
        LEFT   JOIN yield_prediction yp
               ON yp.block_id = rrb.block_id
              AND yp.year     = 2026
              AND yp.month    = p.mo
        LEFT   JOIN sup_per_block spb
               ON spb.plan_id = p.plan_id AND spb.block_id = rrb.block_id
        JOIN   plan_sup_totals pst ON pst.plan_id = p.plan_id
    ),
    plan_yield_totals AS (
        SELECT plan_id, SUM(pred_yield) AS total_yield
        FROM   round_data GROUP BY plan_id
    ),

    -- Floor allocation + fractional remainder per block
    with_props AS (
        SELECT
            rd.*,
            pyt.total_yield,
            CASE
                WHEN pyt.total_yield > 0 THEN
                    FLOOR(rd.movable::NUMERIC * rd.pred_yield / pyt.total_yield)::INTEGER
                ELSE
                    FLOOR(rd.movable::NUMERIC
                          / COUNT(*) OVER (PARTITION BY rd.plan_id))::INTEGER
            END AS base_alloc,
            CASE
                WHEN pyt.total_yield > 0 THEN
                    (rd.movable::NUMERIC * rd.pred_yield / pyt.total_yield)
                    - FLOOR(rd.movable::NUMERIC * rd.pred_yield / pyt.total_yield)
                ELSE
                    1.0 - (ROW_NUMBER() OVER (PARTITION BY rd.plan_id
                                              ORDER BY rd.block_id))::NUMERIC
                          / COUNT(*) OVER (PARTITION BY rd.plan_id)
            END AS rem_frac
        FROM  round_data rd
        JOIN  plan_yield_totals pyt ON pyt.plan_id = rd.plan_id
    ),

    -- Rank by remainder descending → top-deficit rows each get +1
    with_ranks AS (
        SELECT *,
            RANK() OVER (PARTITION BY plan_id
                         ORDER BY rem_frac DESC, block_id)  AS rem_rank,
            SUM(base_alloc) OVER (PARTITION BY plan_id)     AS sum_base
        FROM with_props
    )

SELECT
    plan_id                                              AS labour_plan_id,
    block_id,
    worker_group_id,
    period_start                                         AS assignment_date,
    cycle_id                                             AS rotation_cycle_id,
    mo                                                   AS rotation_round,
    NULLIF(pred_yield, 0)::NUMERIC(10,3)                 AS expected_yield_kg,
    CASE
        WHEN plan_status = 'completed' AND pred_yield > 0
        THEN ROUND(
            pred_yield *
            (0.92 + 0.12 * ((mo * 7 + rem_rank::INTEGER) % 10)::NUMERIC / 10.0),
            1)
        ELSE NULL
    END                                                  AS actual_yield_kg,
    sup_count
        + base_alloc
        + CASE WHEN rem_rank <= GREATEST(0, movable - sum_base)
               THEN 1 ELSE 0 END                         AS allocated_workers,
    CASE WHEN plan_status = 'completed' THEN 'completed'
         ELSE 'scheduled' END                            AS status
FROM with_ranks
ON CONFLICT (block_id, assignment_date, worker_group_id) DO NOTHING;
