-- =============================================================================
-- Migration 020: Reconcile fertilizer schema with the application code
-- =============================================================================
-- The live DB was bootstrapped from 019_fertilizer_schedule_tables.sql, a
-- minimal table set that omitted several columns the fertilizer.py blueprint
-- expects (they originated in the 011/015 fertilizer migrations that were
-- superseded). This migration adds the missing columns idempotently so the
-- read endpoints (/fertilizer/types, /fertilizer/schedules, block history) and
-- the alerts view all work against the same schema the code targets.
--
-- Net additions:
--   fertilizer_type            + npk_n, npk_p, npk_k (with backfill)
--   fertilizer_schedule        + notes, created_at
--   fertilizer_schedule_entry  + actual_application_id (FK -> fertilizer_application)
--   v_fertilizer_schedule_alerts rebuilt to the canonical (npk-aware) form
-- =============================================================================

BEGIN;

-- 1. fertilizer_type — NPK breakdown columns (from old migration 011) ----------
ALTER TABLE public.fertilizer_type
    ADD COLUMN IF NOT EXISTS npk_n numeric(5,2) NULL,   -- % Nitrogen
    ADD COLUMN IF NOT EXISTS npk_p numeric(5,2) NULL,   -- % Phosphorus (P2O5)
    ADD COLUMN IF NOT EXISTS npk_k numeric(5,2) NULL;   -- % Potassium (K2O)

UPDATE public.fertilizer_type SET npk_n = 46.00, npk_p =  0.00, npk_k =  0.00 WHERE code = 'T0_200'  AND npk_n IS NULL;
UPDATE public.fertilizer_type SET npk_n = 28.60, npk_p =  3.80, npk_k = 14.80 WHERE code = 'U750'    AND npk_n IS NULL;
UPDATE public.fertilizer_type SET npk_n = 15.00, npk_p = 15.00, npk_k = 15.00 WHERE code = 'EP_GOLD' AND npk_n IS NULL;
UPDATE public.fertilizer_type SET npk_n =  0.00, npk_p =  0.00, npk_k = 60.00 WHERE code = 'MOP'     AND npk_n IS NULL;
UPDATE public.fertilizer_type SET npk_n =  0.00, npk_p = 28.00, npk_k =  0.00 WHERE code = 'RPR'     AND npk_n IS NULL;
UPDATE public.fertilizer_type SET npk_n =  0.00, npk_p =  0.00, npk_k =  0.00 WHERE code = 'DOLOMITE' AND npk_n IS NULL;

-- 2. fertilizer_schedule — header columns the list endpoint selects ------------
ALTER TABLE public.fertilizer_schedule
    ADD COLUMN IF NOT EXISTS notes      TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();

-- 3. fertilizer_schedule_entry — link to the application that fulfilled it -----
ALTER TABLE public.fertilizer_schedule_entry
    ADD COLUMN IF NOT EXISTS actual_application_id UUID NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fse_application_fkey'
          AND table_name = 'fertilizer_schedule_entry'
    ) THEN
        ALTER TABLE public.fertilizer_schedule_entry
            ADD CONSTRAINT fse_application_fkey
            FOREIGN KEY (actual_application_id)
            REFERENCES public.fertilizer_application(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 4. Rebuild the alerts view in its canonical (npk-aware) form -----------------
DROP VIEW IF EXISTS public.v_fertilizer_schedule_alerts;

CREATE VIEW public.v_fertilizer_schedule_alerts AS
SELECT
    e.name                                          AS estate,
    e.id                                            AS estate_id,
    b.id                                            AS block_id,
    b.block_code,
    b.zone,
    b.growth_stage,
    b.area_hectares,
    ft.id                                           AS fertilizer_type_id,
    ft.code                                         AS fertilizer,
    ft.npk_n,
    ft.npk_k,
    fs.id                                           AS schedule_id,
    fse.id                                          AS entry_id,
    fs.period_start,
    fse.due_date,
    fse.status,
    fse.scheduled_rate_kg_per_ha,
    ROUND(fse.scheduled_rate_kg_per_ha * b.area_hectares, 1) AS total_kg_needed,
    (CURRENT_DATE - fse.due_date)                   AS days_overdue
FROM public.fertilizer_schedule_entry fse
JOIN public.fertilizer_schedule   fs  ON fs.id  = fse.schedule_id
JOIN public.block                 b   ON b.id   = fse.block_id
JOIN public.estate                e   ON e.id   = b.estate_id
JOIN public.fertilizer_programme  fp  ON fp.id  = fse.programme_id
JOIN public.fertilizer_type       ft  ON ft.id  = fp.fertilizer_type_id
WHERE fse.status IN ('pending', 'due', 'overdue')
ORDER BY fse.due_date ASC, e.name, b.block_code;

COMMIT;
