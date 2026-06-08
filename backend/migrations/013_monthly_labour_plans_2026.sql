-- =============================================================================
-- KVPL — Rebuild monthly labour plans: 2026 Jan–May
-- Migration 013
--
-- Replaces the stale weekly-cadence seed plans from migrations 004 and 005
-- with correct monthly plans (period_start = first of month) for Jan–May 2026.
--
--   Jan–Apr  →  status = 'completed'  (with realistic actual yields)
--   May      →  status = 'published'
--
-- allocated_workers per block_assignment uses the same supervisor-anchored
-- largest-remainder algorithm as the Python generator:
--   1. Supervisors are fixed to their block (not redistributed).
--   2. Remaining (movable) workers are split proportionally to yield prediction.
--   3. Largest-remainder ensures the integer allocations sum exactly to
--      total active employees — nobody is left unallocated.
--
-- Rotation current_round reset to 6 for all four estates:
--   rounds 1–5 have been consumed by Jan–May; June will use round 6.
-- =============================================================================


-- =============================================================================
-- 0. FILL MISSING KUNDASALE D1 YIELD PREDICTIONS
--    Block D1 existed in 004 but was omitted from 010.
-- =============================================================================

INSERT INTO yield_prediction (block_id, year, month, predicted_yield_kg,
                              confidence_low, confidence_high, model_version)
SELECT b.id, d.yr, d.mo, d.pred_kg,
       ROUND(d.pred_kg * 0.85, 1),
       ROUND(d.pred_kg * 1.15, 1),
       'heuristic_v1'
FROM block b
JOIN estate e ON b.estate_id = e.id
JOIN (VALUES
    ('D1',2026, 1,58000), ('D1',2026, 2,61200), ('D1',2026, 3,64500),
    ('D1',2026, 4,62800), ('D1',2026, 5,63700), ('D1',2026, 6,59400),
    ('D1',2026, 7,55100), ('D1',2026, 8,52800), ('D1',2026, 9,57600),
    ('D1',2026,10,61100), ('D1',2026,11,63800), ('D1',2026,12,60200)
) AS d(bc, yr, mo, pred_kg) ON b.block_code = d.bc
WHERE e.name = 'Kundasale Estate'
ON CONFLICT DO NOTHING;


-- =============================================================================
-- 1. REMOVE STALE PLANS
--    ON DELETE CASCADE propagates to block_assignment for linked rows.
--    Unlinked historical rows (plan_id IS NULL) are left intact — they provide
--    productivity history for the dashboard queries.
-- =============================================================================

DELETE FROM labour_plan
WHERE estate_id IN (
    SELECT id FROM estate
    WHERE name IN ('Kundasale Estate','Ramboda Heights',
                   'Hunasgiriya Estate','Haputale Park')
);


-- =============================================================================
-- 2. RESET ROTATION CURRENT_ROUND = 6
--    Rounds 1–5 were consumed by Jan–May 2026.
--    The monthly cron will use round 6 when it next fires for June.
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
-- 3. INSERT MONTHLY LABOUR PLANS  (Jan–May 2026)
--    total_workers = COUNT of all active employees for the estate.
--    target_kg     = SUM of yield predictions for blocks in that round.
-- =============================================================================

INSERT INTO labour_plan
    (estate_id, created_by, period_start, total_workers, target_kg, status, notes)
WITH
    target_months AS (
        SELECT generate_series(1, 5) AS mo
    ),
    estate_managers AS (
        SELECT DISTINCT ON (e.id)
               e.id AS estate_id,
               u.id AS manager_id
        FROM estate e
        JOIN "user" u ON u.estate_id = e.id AND u.role = 'estate_manager'
        WHERE e.name IN ('Kundasale Estate','Ramboda Heights',
                         'Hunasgiriya Estate','Haputale Park')
        ORDER BY e.id, u.created_at
    ),
    emp_counts AS (
        SELECT estate_id, COUNT(*) AS total_emp
        FROM   employee
        WHERE  is_active = TRUE
        GROUP  BY estate_id
    ),
    round_targets AS (
        SELECT em.estate_id, tm.mo,
               COALESCE(SUM(yp.predicted_yield_kg), 0) AS target_kg
        FROM   estate_managers em
        CROSS  JOIN target_months tm
        JOIN   rotation_cycle rc
               ON rc.estate_id = em.estate_id AND rc.is_active = TRUE
        JOIN   rotation_round_block rrb
               ON rrb.rotation_cycle_id = rc.id AND rrb.round_number = tm.mo
        LEFT   JOIN yield_prediction yp
               ON yp.block_id = rrb.block_id
              AND yp.year     = 2026
              AND yp.month    = tm.mo
        GROUP  BY em.estate_id, tm.mo
    )
SELECT
    em.estate_id,
    em.manager_id,
    MAKE_DATE(2026, tm.mo, 1)                              AS period_start,
    ec.total_emp                                            AS total_workers,
    COALESCE(rt.target_kg, 0)                              AS target_kg,
    CASE WHEN tm.mo <= 4 THEN 'completed' ELSE 'published' END AS status,
    'Monthly plan — round ' || tm.mo || ' — '
        || TO_CHAR(MAKE_DATE(2026, tm.mo, 1), 'Mon YYYY')  AS notes
FROM   estate_managers  em
CROSS  JOIN target_months tm
JOIN   emp_counts        ec  ON ec.estate_id = em.estate_id
LEFT   JOIN round_targets rt ON rt.estate_id = em.estate_id AND rt.mo = tm.mo
ON CONFLICT (estate_id, period_start)
DO UPDATE SET
    total_workers = EXCLUDED.total_workers,
    target_kg     = EXCLUDED.target_kg,
    status        = EXCLUDED.status,
    notes         = EXCLUDED.notes;


-- =============================================================================
-- 4. BLOCK ASSIGNMENTS WITH YIELD-PROPORTIONAL ALLOCATED_WORKERS
--
--    Algorithm (mirrors Python _proportional_workers + supervisor anchoring):
--      a) sup_count  = active supervisors in the primary group for this block.
--      b) movable    = total_workers − SUM(sup_count) across all blocks in plan.
--      c) base_alloc = FLOOR(movable × block_yield / total_round_yield).
--      d) deficit    = movable − SUM(base_alloc).
--      e) Top-deficit blocks by fractional remainder each get +1.
--      f) allocated_workers = sup_count + base_alloc + remainder_bonus (0 or 1).
--
--    Result: SUM(allocated_workers) = total active employees, zero left behind.
-- =============================================================================

INSERT INTO block_assignment (
    labour_plan_id, block_id, worker_group_id, assignment_date,
    rotation_cycle_id, rotation_round,
    expected_yield_kg, actual_yield_kg,
    allocated_workers, status
)
WITH
    -- ── Plans created above ──────────────────────────────────────────────────
    plans AS (
        SELECT lp.id                                           AS plan_id,
               lp.estate_id,
               lp.period_start,
               lp.total_workers,
               lp.status                                       AS plan_status,
               EXTRACT(MONTH FROM lp.period_start)::INTEGER   AS mo
        FROM   labour_plan lp
        WHERE  lp.estate_id IN (
                   SELECT id FROM estate
                   WHERE name IN ('Kundasale Estate','Ramboda Heights',
                                  'Hunasgiriya Estate','Haputale Park')
               )
          AND  lp.period_start BETWEEN '2026-01-01' AND '2026-05-01'
    ),

    -- ── Supervisor count anchored per (plan, block) ──────────────────────────
    --    Only the PRIMARY rotation-assigned group contributes supervisors.
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

    -- ── Total supervisors anchored per plan ──────────────────────────────────
    plan_sup_totals AS (
        SELECT plan_id, SUM(sup_count) AS total_sups
        FROM   sup_per_block
        GROUP  BY plan_id
    ),

    -- ── Raw rotation assignments joined with yield predictions ────────────────
    round_data AS (
        SELECT
            p.plan_id,
            p.estate_id,
            p.period_start,
            p.total_workers,
            p.plan_status,
            p.mo,
            rc.id                                           AS cycle_id,
            rrb.block_id,
            rrb.worker_group_id,
            COALESCE(yp.predicted_yield_kg, 0)             AS pred_yield,
            COALESCE(spb.sup_count, 0)                     AS sup_count,
            (p.total_workers - COALESCE(pst.total_sups,0)) AS movable
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

    -- ── Total yield per plan (denominator for proportion) ─────────────────────
    plan_yield_totals AS (
        SELECT plan_id, SUM(pred_yield) AS total_yield
        FROM   round_data
        GROUP  BY plan_id
    ),

    -- ── Base proportional allocation (floor) + fractional remainder ───────────
    with_props AS (
        SELECT
            rd.*,
            pyt.total_yield,
            CASE
                WHEN pyt.total_yield > 0 THEN
                    FLOOR(rd.movable::NUMERIC * rd.pred_yield
                          / pyt.total_yield)::INTEGER
                ELSE
                    FLOOR(rd.movable::NUMERIC
                          / COUNT(*) OVER (PARTITION BY rd.plan_id))::INTEGER
            END AS base_alloc,
            CASE
                WHEN pyt.total_yield > 0 THEN
                    (rd.movable::NUMERIC * rd.pred_yield / pyt.total_yield)
                    - FLOOR(rd.movable::NUMERIC * rd.pred_yield / pyt.total_yield)
                ELSE
                    -- Equal-split fallback: spread remainder by block_id order
                    1.0 - (ROW_NUMBER() OVER (PARTITION BY rd.plan_id
                                              ORDER BY rd.block_id))::NUMERIC
                          / COUNT(*) OVER (PARTITION BY rd.plan_id)
            END AS rem_frac
        FROM  round_data rd
        JOIN  plan_yield_totals pyt ON pyt.plan_id = rd.plan_id
    ),

    -- ── Largest-remainder: rank by fractional part to assign the deficit +1s ──
    with_ranks AS (
        SELECT *,
            RANK() OVER (PARTITION BY plan_id
                         ORDER BY rem_frac DESC, block_id)   AS rem_rank,
            SUM(base_alloc) OVER (PARTITION BY plan_id)      AS sum_base
        FROM with_props
    )

SELECT
    plan_id                                                AS labour_plan_id,
    block_id,
    worker_group_id,
    period_start                                           AS assignment_date,
    cycle_id                                               AS rotation_cycle_id,
    mo                                                     AS rotation_round,

    NULLIF(pred_yield, 0)::NUMERIC(10,3)                   AS expected_yield_kg,

    -- Completed months: realistic actual yield 92–104 % of predicted
    CASE
        WHEN plan_status = 'completed' AND pred_yield > 0
        THEN ROUND(
            pred_yield *
            (0.92 + 0.12 *
             ((mo * 7 + rem_rank::INTEGER) % 10)::NUMERIC / 10.0
            ), 1)
        ELSE NULL
    END                                                    AS actual_yield_kg,

    -- Supervisor anchor + proportional movable workers + remainder bonus
    sup_count
        + base_alloc
        + CASE WHEN rem_rank <= GREATEST(0, movable - sum_base)
               THEN 1 ELSE 0 END                           AS allocated_workers,

    CASE WHEN plan_status = 'completed' THEN 'completed'
         ELSE 'scheduled'
    END                                                    AS status

FROM with_ranks
ON CONFLICT (block_id, assignment_date, worker_group_id) DO NOTHING;
