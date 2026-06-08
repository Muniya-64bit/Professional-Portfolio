-- =============================================================================
-- KVPL — Yield-proportional worker allocation
-- Migration 012
--
-- Adds allocated_workers to block_assignment so the monthly generator can
-- record exactly how many workers are deployed per block, scaled to yield
-- prediction.  The primary assignment for a block carries the full headcount;
-- doubled-up (full-coverage) rows carry 0.
-- =============================================================================

ALTER TABLE block_assignment
    ADD COLUMN IF NOT EXISTS allocated_workers INTEGER NOT NULL DEFAULT 0
        CHECK (allocated_workers >= 0);

COMMENT ON COLUMN block_assignment.allocated_workers IS
    'Workers deployed to this block this period, proportional to yield prediction.
     Primary rotation assignment carries the full block headcount; any extra
     full-coverage rows on the same block carry 0.';
