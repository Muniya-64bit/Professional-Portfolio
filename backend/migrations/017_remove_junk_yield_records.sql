-- =============================================================================
-- KVPL — Remove junk June 2026 yield records
-- Migration 017
--
-- Four block_yield_record rows (source 'labour_plan') held implausible June 2026
-- "actuals" — 100 / 2500 / 6700 / 3000 kg for blocks whose normal monthly yield
-- is ~70,000–95,000 kg.  They were placeholder/garbage data.
--
-- Combined with the (now-fixed) forecast data-leakage, they zeroed June
-- predictions for Haputale N1/N2/N3 and Kundasale A1.  The forecaster no longer
-- peeks at the target month, but these rows would still corrupt JULY forecasts
-- for those blocks, so they are removed.
--
-- Idempotent: deletes by the same predicate; re-running is a no-op.
-- =============================================================================

DELETE FROM block_yield_record
WHERE  source   = 'labour_plan'
  AND  year     = 2026
  AND  month    = 6
  AND  yield_kg < 10000;
