-- =============================================================================
-- Migration 021: Add rate_kg_per_ha to fertilizer_application
-- =============================================================================
-- The live DB was bootstrapped without the rate_kg_per_ha column that the
-- fertilizer.py blueprint expects (it originated in the superseded 011 migration,
-- like the columns reconciled in 020). Without it, POST /fertilizer/applications,
-- GET /fertilizer/applications and GET /fertilizer/history all 500.
--
-- This adds the column idempotently and backfills it from the recorded
-- quantity_kg divided by the block's area, where area is known and positive.
-- =============================================================================

BEGIN;

ALTER TABLE public.fertilizer_application
    ADD COLUMN IF NOT EXISTS rate_kg_per_ha NUMERIC(8,2) NULL;

-- Backfill rate from quantity / block area for existing rows that lack it.
UPDATE public.fertilizer_application fa
SET    rate_kg_per_ha = ROUND(fa.quantity_kg / b.area_hectares, 2)
FROM   public.block b
WHERE  b.id = fa.block_id
  AND  fa.rate_kg_per_ha IS NULL
  AND  b.area_hectares IS NOT NULL
  AND  b.area_hectares > 0;

COMMIT;
