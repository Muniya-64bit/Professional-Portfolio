-- =============================================================================
-- Migration 015: Fertilizer Schedule Two-Table Refactor
-- =============================================================================
-- Splits the flat fertilizer_schedule table into:
--   fertilizer_schedule         → monthly header (one per estate per month)
--   fertilizer_schedule_entry   → block-level entries (renamed from fertilizer_schedule)
--
-- Existing data: TRUNCATE + start clean (fertilizer_application rows kept).
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Wipe existing schedule rows (application records are untouched)
-- ---------------------------------------------------------------------------

TRUNCATE public.fertilizer_schedule CASCADE;

-- ---------------------------------------------------------------------------
-- 2. Rename old fertilizer_schedule → fertilizer_schedule_entry
--    Drop its old unique constraint and indexes first.
-- ---------------------------------------------------------------------------

ALTER TABLE public.fertilizer_schedule
    DROP CONSTRAINT fertilizer_schedule_block_programme_unique;

DROP INDEX IF EXISTS public.idx_fert_sched_block;
DROP INDEX IF EXISTS public.idx_fert_sched_status;
DROP INDEX IF EXISTS public.idx_fert_sched_due;
DROP INDEX IF EXISTS public.idx_fert_sched_programme;

ALTER TABLE public.fertilizer_schedule
    RENAME TO fertilizer_schedule_entry;

-- Rename the PK and FK constraints to reflect the new table name
ALTER TABLE public.fertilizer_schedule_entry
    RENAME CONSTRAINT fertilizer_schedule_pkey              TO fse_pkey;
ALTER TABLE public.fertilizer_schedule_entry
    RENAME CONSTRAINT fertilizer_schedule_block_fkey        TO fse_block_fkey;
ALTER TABLE public.fertilizer_schedule_entry
    RENAME CONSTRAINT fertilizer_schedule_programme_fkey    TO fse_programme_fkey;
ALTER TABLE public.fertilizer_schedule_entry
    RENAME CONSTRAINT fertilizer_schedule_application_fkey  TO fse_application_fkey;
ALTER TABLE public.fertilizer_schedule_entry
    RENAME CONSTRAINT fertilizer_schedule_status_check      TO fse_status_check;

-- ---------------------------------------------------------------------------
-- 3. Create the new fertilizer_schedule header table
-- ---------------------------------------------------------------------------

CREATE TABLE public.fertilizer_schedule (
    id              UUID        NOT NULL DEFAULT uuid_generate_v4(),
    estate_id       UUID        NOT NULL,
    period_start    DATE        NOT NULL,   -- always 1st of month
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'closed')),
    generated_by    UUID,                   -- FK added below
    generated_at    TIMESTAMP   NOT NULL DEFAULT NOW(),
    notes           TEXT,
    created_at      TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP   NOT NULL DEFAULT NOW(),

    CONSTRAINT fertilizer_schedule_pkey
        PRIMARY KEY (id),
    CONSTRAINT fertilizer_schedule_estate_fkey
        FOREIGN KEY (estate_id) REFERENCES public.estate(id) ON DELETE CASCADE,
    CONSTRAINT fertilizer_schedule_generated_by_fkey
        FOREIGN KEY (generated_by) REFERENCES public."user"(id) ON DELETE SET NULL,
    CONSTRAINT fertilizer_schedule_estate_period_unique
        UNIQUE (estate_id, period_start)
);

CREATE INDEX idx_fert_sched_estate_period
    ON public.fertilizer_schedule (estate_id, period_start DESC);

COMMENT ON TABLE public.fertilizer_schedule IS
    'Monthly fertilizer schedule header — one row per estate per month. Entries live in fertilizer_schedule_entry.';
COMMENT ON COLUMN public.fertilizer_schedule.period_start IS
    'Always the 1st of the month. Normalised by the application layer before insert.';

-- ---------------------------------------------------------------------------
-- 4. Add schedule_id FK to fertilizer_schedule_entry
-- ---------------------------------------------------------------------------

ALTER TABLE public.fertilizer_schedule_entry
    ADD COLUMN schedule_id UUID NOT NULL
        REFERENCES public.fertilizer_schedule(id) ON DELETE CASCADE;

-- New unique constraint: one entry per block per programme step per schedule run
ALTER TABLE public.fertilizer_schedule_entry
    ADD CONSTRAINT fse_schedule_block_programme_unique
        UNIQUE (schedule_id, block_id, programme_id);

CREATE INDEX idx_fse_schedule
    ON public.fertilizer_schedule_entry (schedule_id);

CREATE INDEX idx_fse_block_due
    ON public.fertilizer_schedule_entry (block_id, due_date DESC);

CREATE INDEX idx_fse_status
    ON public.fertilizer_schedule_entry (status)
    WHERE status IN ('pending', 'due', 'overdue');

COMMENT ON TABLE public.fertilizer_schedule_entry IS
    'Block-level fertilizer schedule entries. Each row belongs to a fertilizer_schedule (monthly run). Replaces the old fertilizer_schedule table.';
COMMENT ON COLUMN public.fertilizer_schedule_entry.schedule_id IS
    'FK to the monthly schedule header. Cascade-deleted when the schedule is deleted.';

-- ---------------------------------------------------------------------------
-- 5. Rebuild views to reference the new table structure
-- ---------------------------------------------------------------------------

-- v_fertilizer_schedule_alerts: query through fertilizer_schedule_entry, join to header
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

COMMENT ON VIEW public.v_fertilizer_schedule_alerts IS
    'All pending/due/overdue fertilizer schedule entries across all estates, ordered by urgency. Used by the /alerts API endpoint.';

COMMIT;
