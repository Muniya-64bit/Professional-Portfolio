-- =============================================================================
-- KVPL — Limit rotation cycles to exactly 5 rounds (Jan–May 2026)
-- Migration 015
--
-- Problem: the rotation tab kept showing more than 5 rounds even after the
-- monthly plans were trimmed to 5 (migrations 013/014).  Two stale-data sources
-- survived those migrations:
--
--   a) rotation_round_block still held the FULL cycle per estate
--      (6 / 8 / 10 / 15 rounds = block count).  This table drives the matrix.
--
--   b) Orphaned block_assignment rows (labour_plan_id IS NULL) left behind by
--      the old weekly seed (004/005).  013/014 deleted plans and cascaded to
--      LINKED assignments only — orphans survived carrying rounds 6,7,8,10.
--
-- Fix (idempotent):
--   1. Delete orphan block_assignment rows for the four active cycles.
--   2. Truncate rotation_round_block to rounds 1–5.
--   3. Resize each cycle: total_rounds = 5, current_round = 5 (May = current).
--      Both columns set in one UPDATE to satisfy
--      CHECK (current_round BETWEEN 1 AND total_rounds).
--
-- Result: every estate has exactly 5 rounds, 5 plans, one round per month.
--
-- Trade-off: total_rounds was originally "block count" so every group visits
-- every block once per cycle.  Estates with >5 blocks (Ramboda 8, Haputale 10,
-- Hunasgiriya 15) no longer form a complete coverage cycle.  Acceptable for the
-- Jan–May 2026 demo data this migration targets.
-- =============================================================================

DO $$
DECLARE
    v_cycle_ids UUID[];
BEGIN
    -- Active cycles for the four seeded estates
    SELECT ARRAY_AGG(rc.id)
    INTO   v_cycle_ids
    FROM   rotation_cycle rc
    JOIN   estate e ON e.id = rc.estate_id
    WHERE  rc.is_active = TRUE
      AND  e.name IN ('Kundasale Estate','Ramboda Heights',
                      'Hunasgiriya Estate','Haputale Park');

    IF v_cycle_ids IS NULL THEN
        RAISE NOTICE 'No active rotation cycles found — nothing to do.';
        RETURN;
    END IF;

    -- 1. Drop orphan assignments (stale weekly-seed leftovers, plan_id NULL)
    DELETE FROM block_assignment
    WHERE  rotation_cycle_id = ANY(v_cycle_ids)
      AND  labour_plan_id IS NULL;

    -- 2. Truncate the rotation matrix to rounds 1–5
    DELETE FROM rotation_round_block
    WHERE  rotation_cycle_id = ANY(v_cycle_ids)
      AND  round_number > 5;

    -- 3. Resize cycles: 5 rounds, currently on round 5 (May)
    UPDATE rotation_cycle
    SET    total_rounds  = 5,
           current_round = 5,
           updated_at    = NOW()
    WHERE  id = ANY(v_cycle_ids);

    RAISE NOTICE 'Limited % cycle(s) to 5 rounds.', array_length(v_cycle_ids, 1);
END $$;
