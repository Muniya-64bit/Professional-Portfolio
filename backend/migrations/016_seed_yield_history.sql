-- =============================================================================
-- KVPL — Seed historical yield records so the forecaster works for all estates
-- Migration 016
--
-- Problem: the heuristic forecaster (predictions._forecast) derives each block's
-- predicted yield from its block_yield_record history.  Only Kundasale had
-- history seeded — Hunasgiriya, Ramboda and 7 of Haputale's blocks had none, so
-- every live-generated month (anything the scheduler produces beyond the
-- hand-seeded Jan–May plans) fell back to the flat constant
-- worker_capacity * 600.  That made every block in those estates get the SAME
-- predicted yield and therefore the SAME worker count.
--
-- Fix: backfill block_yield_record (Jan–May 2026) for the three estates from the
-- already-differentiated yield_prediction rows that drive the Jan–May plans.
-- This gives the forecaster real, varied signal, so future months (June+) get
-- differentiated predictions and yield-proportional worker allocation.
--
-- Idempotent: ON CONFLICT (block_id, year, month) DO NOTHING.
-- =============================================================================

INSERT INTO block_yield_record (block_id, year, month, yield_kg, source)
SELECT yp.block_id,
       yp.year,
       yp.month,
       yp.predicted_yield_kg,
       'seeded_from_prediction_v1'
FROM   yield_prediction yp
JOIN   block  b ON b.id = yp.block_id
JOIN   estate e ON e.id = b.estate_id
WHERE  e.name IN ('Hunasgiriya Estate','Ramboda Heights','Haputale Park')
  AND  yp.year  = 2026
  AND  yp.month BETWEEN 1 AND 5
ON CONFLICT (block_id, year, month) DO NOTHING;
