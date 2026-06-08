-- =============================================================================
-- KVPL — Labour Planner: Weekly → Monthly cadence
-- Migration 008
--
-- Moves the labour plan period from a week to a calendar month and lets the
-- monthly generator place every worker group (full coverage, doubling groups
-- onto blocks when there are more groups than blocks).
--
--  * labour_plan.week_start  →  labour_plan.period_start  (first day of month)
--  * each rotation_cycle.current_round now advances once per MONTH
--  * block_assignment uniqueness relaxed so two groups may share a block
--
-- NOTE: existing seeded weekly plans remain as harmless historical rows; their
--       period_start simply holds the old Monday date.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. RENAME labour_plan.week_start → period_start
--    The UNIQUE (estate_id, week_start) constraint follows the column.
-- ---------------------------------------------------------------------------

ALTER TABLE labour_plan RENAME COLUMN week_start TO period_start;

COMMENT ON COLUMN labour_plan.period_start IS
    'First day (YYYY-MM-01) of the calendar month this plan covers';

-- ---------------------------------------------------------------------------
-- 2. Rotation now advances monthly (one round per month)
-- ---------------------------------------------------------------------------

COMMENT ON COLUMN rotation_cycle.current_round IS
    'Round used when auto-generating the next MONTHLY labour plan; advances by 1 each month and wraps at total_rounds';

-- ---------------------------------------------------------------------------
-- 3. Relax block_assignment uniqueness for full-coverage doubling-up
--    Old: one group per block per date.
--    New: a block may host more than one group, but the same group cannot be
--         assigned to the same block twice in the same month.
-- ---------------------------------------------------------------------------

ALTER TABLE block_assignment
    DROP CONSTRAINT IF EXISTS block_assignment_block_id_assignment_date_key;

ALTER TABLE block_assignment
    ADD CONSTRAINT block_assignment_block_date_group_key
        UNIQUE (block_id, assignment_date, worker_group_id);
