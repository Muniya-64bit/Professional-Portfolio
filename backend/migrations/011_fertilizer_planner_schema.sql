-- =============================================================================
-- Migration 011: Fertilizer Rotation Planner — schema modifications & new tables
-- =============================================================================
-- What this does:
--   1. ALTER fertilizer_type        → add npk_n, npk_p, npk_k columns
--   2. ALTER fertilizer_application → add rate_kg_per_ha (computed from
--                                     quantity_kg / block.area_hectares is
--                                     unreliable at insert time, so we store
--                                     it directly); also widen the
--                                     recommendation CHECK to include 'skipped'
--   3. ALTER fertilizer_recommendation → add fertilizer_type_id FK so every
--                                        recommendation knows which product it
--                                        refers to
--   4. CREATE fertilizer_programme  → per-estate schedule template
--   5. CREATE fertilizer_schedule   → generated rotation schedule per block
--
-- Safe to run multiple times: all ALTERs use IF NOT EXISTS / conditional logic.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. fertilizer_type — add NPK breakdown columns
-- ---------------------------------------------------------------------------

ALTER TABLE public.fertilizer_type
    ADD COLUMN IF NOT EXISTS npk_n  numeric(5,2)  NULL,  -- % Nitrogen
    ADD COLUMN IF NOT EXISTS npk_p  numeric(5,2)  NULL,  -- % Phosphorus (as P₂O₅)
    ADD COLUMN IF NOT EXISTS npk_k  numeric(5,2)  NULL;  -- % Potassium (as K₂O)

COMMENT ON COLUMN public.fertilizer_type.npk_n IS '% Nitrogen content by weight';
COMMENT ON COLUMN public.fertilizer_type.npk_p IS '% Phosphorus (P₂O₅) content by weight';
COMMENT ON COLUMN public.fertilizer_type.npk_k IS '% Potassium (K₂O) content by weight';

-- Backfill NPK values for the 6 seeded products
-- T0_200 — straight nitrogen top-dress (high N, no P/K)
UPDATE public.fertilizer_type SET npk_n = 46.00, npk_p = 0.00, npk_k = 0.00
    WHERE code = 'T0_200';

-- U750 — urea-heavy blend (TRI mid-country profile: ~29%N, 4%P, 15%K)
UPDATE public.fertilizer_type SET npk_n = 28.60, npk_p = 3.80, npk_k = 14.80
    WHERE code = 'U750';

-- EP Gold — compound NPK estate blend
UPDATE public.fertilizer_type SET npk_n = 15.00, npk_p = 15.00, npk_k = 15.00
    WHERE code = 'EP_GOLD';

-- MOP — pure potassium, no N or P
UPDATE public.fertilizer_type SET npk_n = 0.00, npk_p = 0.00, npk_k = 60.00
    WHERE code = 'MOP';

-- RPR — slow-release phosphate (Eppawala rock phosphate, ~28% P₂O₅)
UPDATE public.fertilizer_type SET npk_n = 0.00, npk_p = 28.00, npk_k = 0.00
    WHERE code = 'RPR';

-- Dolomite — calcium-magnesium amendment, no NPK
UPDATE public.fertilizer_type SET npk_n = 0.00, npk_p = 0.00, npk_k = 0.00
    WHERE code = 'DOLOMITE';


-- ---------------------------------------------------------------------------
-- 2. fertilizer_application — add rate_kg_per_ha
--    Also fix the recommendation CHECK: add 'skipped' as a valid value so the
--    schedule can mark applications that were intentionally skipped.
-- ---------------------------------------------------------------------------

ALTER TABLE public.fertilizer_application
    ADD COLUMN IF NOT EXISTS rate_kg_per_ha numeric(8,2) NULL;

COMMENT ON COLUMN public.fertilizer_application.rate_kg_per_ha IS
    'Application rate in kg per hectare. Stored explicitly; quantity_kg = rate_kg_per_ha × block.area_hectares.';

-- Drop the old 3-value CHECK and replace with a 4-value one
ALTER TABLE public.fertilizer_application
    DROP CONSTRAINT IF EXISTS fertilizer_application_recommendation_check;

ALTER TABLE public.fertilizer_application
    ADD CONSTRAINT fertilizer_application_recommendation_check
    CHECK (recommendation IS NULL OR (recommendation)::text = ANY (
        (ARRAY[
            'apply_now'::character varying,
            'delay'::character varying,
            'increase_dosage'::character varying,
            'skipped'::character varying
        ])::text[]
    ));

-- Backfill rate_kg_per_ha for the single existing application row
-- Block A1 (df4ff5e5) has area_hectares = 2.50; quantity_kg = 150 → 60 kg/ha
UPDATE public.fertilizer_application
    SET rate_kg_per_ha = ROUND(quantity_kg / b.area_hectares, 2)
    FROM public.block b
    WHERE public.fertilizer_application.block_id = b.id
      AND public.fertilizer_application.rate_kg_per_ha IS NULL
      AND b.area_hectares IS NOT NULL
      AND b.area_hectares > 0;


-- ---------------------------------------------------------------------------
-- 3. fertilizer_recommendation — add fertilizer_type_id FK
-- ---------------------------------------------------------------------------

ALTER TABLE public.fertilizer_recommendation
    ADD COLUMN IF NOT EXISTS fertilizer_type_id uuid NULL;

-- Add the FK constraint (deferred so existing NULL rows are not rejected)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fertilizer_recommendation_fertilizer_type_id_fkey'
    ) THEN
        ALTER TABLE public.fertilizer_recommendation
            ADD CONSTRAINT fertilizer_recommendation_fertilizer_type_id_fkey
            FOREIGN KEY (fertilizer_type_id)
            REFERENCES public.fertilizer_type(id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- Supporting index for FK lookups
CREATE INDEX IF NOT EXISTS idx_fert_rec_type
    ON public.fertilizer_recommendation (fertilizer_type_id)
    WHERE fertilizer_type_id IS NOT NULL;

COMMENT ON COLUMN public.fertilizer_recommendation.fertilizer_type_id IS
    'Which fertilizer product this recommendation is for. NULL means product-agnostic (e.g. a general delay instruction).';

-- Backfill the 3 existing recommendation rows (all for block A1, Kundasale)
-- They are generic nitrogen/potassium observations — link them to T0_200
UPDATE public.fertilizer_recommendation
    SET fertilizer_type_id = (
        SELECT id FROM public.fertilizer_type WHERE code = 'T0_200'
    )
    WHERE fertilizer_type_id IS NULL;


-- ---------------------------------------------------------------------------
-- 4. CREATE fertilizer_programme
--    Per-estate schedule template: which product, in which order, at what
--    interval and rate. Estate managers can edit via the UI.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.fertilizer_programme (
    id                  uuid    DEFAULT public.uuid_generate_v4() NOT NULL,
    estate_id           uuid    NOT NULL,
    fertilizer_type_id  uuid    NOT NULL,
    application_no      integer NOT NULL,      -- 1st, 2nd, 3rd application in annual cycle
    interval_weeks      integer NOT NULL,      -- weeks after the previous application in this programme
    rate_kg_per_ha      numeric(8,2) NOT NULL, -- standard rate for this step
    zone_override       character varying(20)  NULL, -- NULL = applies to all zones; 'Low'/'Mid'/'High' = zone-specific
    growth_stage_filter character varying(100) NULL, -- NULL = all stages; 'Mature' / 'Young' / 'Immature' = filtered
    notes               text    NULL,
    is_active           boolean NOT NULL DEFAULT true,
    created_at          timestamp without time zone NOT NULL DEFAULT now(),
    updated_at          timestamp without time zone NOT NULL DEFAULT now(),

    CONSTRAINT fertilizer_programme_pkey PRIMARY KEY (id),
    CONSTRAINT fertilizer_programme_estate_fkey
        FOREIGN KEY (estate_id) REFERENCES public.estate(id) ON DELETE CASCADE,
    CONSTRAINT fertilizer_programme_type_fkey
        FOREIGN KEY (fertilizer_type_id) REFERENCES public.fertilizer_type(id) ON DELETE RESTRICT,
    CONSTRAINT fertilizer_programme_application_no_check
        CHECK (application_no > 0),
    CONSTRAINT fertilizer_programme_interval_weeks_check
        CHECK (interval_weeks > 0),
    CONSTRAINT fertilizer_programme_rate_check
        CHECK (rate_kg_per_ha > 0),
    CONSTRAINT fertilizer_programme_zone_check
        CHECK (zone_override IS NULL OR zone_override = ANY (ARRAY['Low', 'Mid', 'High'])),
    -- One programme step per estate/product/application_no/zone combination
    CONSTRAINT fertilizer_programme_unique_step
        UNIQUE (estate_id, fertilizer_type_id, application_no, zone_override)
);

COMMENT ON TABLE public.fertilizer_programme IS
    'Per-estate fertilizer schedule template. Defines which product is applied, in which order, at what interval and rate. Used by the scheduler to auto-generate fertilizer_schedule entries.';
COMMENT ON COLUMN public.fertilizer_programme.application_no IS
    'Sequence number within the annual cycle for this product on this estate (1 = first application of the year).';
COMMENT ON COLUMN public.fertilizer_programme.interval_weeks IS
    'Weeks to wait after the previous application_no step before this one is due. For application_no=1 this is measured from the start of the crop year (April 1).';
COMMENT ON COLUMN public.fertilizer_programme.zone_override IS
    'If set, this programme step overrides the estate default for blocks in this zone only. NULL means the step applies to all blocks on the estate.';

CREATE INDEX IF NOT EXISTS idx_fert_prog_estate
    ON public.fertilizer_programme (estate_id, is_active);

CREATE INDEX IF NOT EXISTS idx_fert_prog_type
    ON public.fertilizer_programme (fertilizer_type_id);


-- ---------------------------------------------------------------------------
-- 5. CREATE fertilizer_schedule
--    Generated rotation schedule: one row per block per programme step per
--    cycle. The scheduler populates this; field staff mark it done by creating
--    a fertilizer_application record and linking it here.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.fertilizer_schedule (
    id                      uuid    DEFAULT public.uuid_generate_v4() NOT NULL,
    block_id                uuid    NOT NULL,
    programme_id            uuid    NOT NULL,
    due_date                date    NOT NULL,
    status                  character varying(20) NOT NULL DEFAULT 'pending',
    actual_application_id   uuid    NULL,        -- set when a fertilizer_application is recorded
    scheduled_rate_kg_per_ha numeric(8,2) NOT NULL, -- copied from programme at generation time
    generated_at            timestamp without time zone NOT NULL DEFAULT now(),
    updated_at              timestamp without time zone NOT NULL DEFAULT now(),

    CONSTRAINT fertilizer_schedule_pkey PRIMARY KEY (id),
    CONSTRAINT fertilizer_schedule_block_fkey
        FOREIGN KEY (block_id) REFERENCES public.block(id) ON DELETE CASCADE,
    CONSTRAINT fertilizer_schedule_programme_fkey
        FOREIGN KEY (programme_id) REFERENCES public.fertilizer_programme(id) ON DELETE CASCADE,
    CONSTRAINT fertilizer_schedule_application_fkey
        FOREIGN KEY (actual_application_id) REFERENCES public.fertilizer_application(id) ON DELETE SET NULL,
    CONSTRAINT fertilizer_schedule_status_check
        CHECK (status = ANY (ARRAY[
            'pending',      -- due in the future, not yet applied
            'due',          -- due_date <= today, not yet applied
            'overdue',      -- due_date < today - grace_days, still not applied
            'done',         -- fertilizer_application recorded and linked
            'skipped'       -- intentionally skipped this cycle
        ])),
    -- Prevent duplicate schedule entries for the same block + programme step
    CONSTRAINT fertilizer_schedule_block_programme_unique
        UNIQUE (block_id, programme_id, due_date)
);

COMMENT ON TABLE public.fertilizer_schedule IS
    'Auto-generated fertilizer rotation schedule. One row per block per programme step. Status transitions: pending → due → overdue / done / skipped.';
COMMENT ON COLUMN public.fertilizer_schedule.scheduled_rate_kg_per_ha IS
    'Rate copied from fertilizer_programme at generation time. Preserved even if the programme is later edited, so history is accurate.';
COMMENT ON COLUMN public.fertilizer_schedule.actual_application_id IS
    'FK to fertilizer_application. Set by the API when a real application is recorded; also sets status = done.';

CREATE INDEX IF NOT EXISTS idx_fert_sched_block
    ON public.fertilizer_schedule (block_id, due_date DESC);

CREATE INDEX IF NOT EXISTS idx_fert_sched_status
    ON public.fertilizer_schedule (status)
    WHERE status IN ('pending', 'due', 'overdue');

CREATE INDEX IF NOT EXISTS idx_fert_sched_due
    ON public.fertilizer_schedule (due_date);

CREATE INDEX IF NOT EXISTS idx_fert_sched_programme
    ON public.fertilizer_schedule (programme_id);


-- ---------------------------------------------------------------------------
-- 6. Refresh the v_block_fert_summary view so it picks up rate_kg_per_ha
-- ---------------------------------------------------------------------------

-- Must DROP first: CREATE OR REPLACE cannot reorder or rename existing columns.
DROP VIEW IF EXISTS public.v_block_fert_summary;
CREATE VIEW public.v_block_fert_summary AS
SELECT
    b.block_code,
    e.name                          AS estate,
    ft.code                         AS fertilizer,
    ft.npk_n,
    ft.npk_p,
    ft.npk_k,
    count(*)                        AS applications,
    sum(fa.quantity_kg)             AS total_kg,
    round(avg(fa.rate_kg_per_ha), 2) AS avg_rate_kg_per_ha,
    max(fa.application_date)        AS last_applied
FROM public.fertilizer_application fa
JOIN public.block b           ON b.id  = fa.block_id
JOIN public.estate e          ON e.id  = b.estate_id
JOIN public.fertilizer_type ft ON ft.id = fa.fertilizer_type_id
WHERE fa.application_date >= (CURRENT_DATE - INTERVAL '1 year')
GROUP BY b.block_code, e.name, ft.code, ft.npk_n, ft.npk_p, ft.npk_k;

COMMENT ON VIEW public.v_block_fert_summary IS
    'Rolling 12-month summary of fertilizer applications per block, including NPK composition and average application rate.';


-- ---------------------------------------------------------------------------
-- 7. New view: v_fertilizer_schedule_alerts
--    The /api/fertilizer/alerts endpoint drives this — shows what needs
--    attention right now across all four estates.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW public.v_fertilizer_schedule_alerts AS
SELECT
    e.name                              AS estate,
    b.block_code,
    b.zone,
    b.growth_stage,
    b.area_hectares,
    ft.code                             AS fertilizer,
    ft.npk_n,
    ft.npk_k,
    fs.due_date,
    fs.status,
    fs.scheduled_rate_kg_per_ha,
    round(fs.scheduled_rate_kg_per_ha * b.area_hectares, 1) AS total_kg_needed,
    (CURRENT_DATE - fs.due_date)        AS days_overdue   -- negative = days until due
FROM public.fertilizer_schedule fs
JOIN public.block b                  ON b.id  = fs.block_id
JOIN public.estate e                 ON e.id  = b.estate_id
JOIN public.fertilizer_programme fp  ON fp.id = fs.programme_id
JOIN public.fertilizer_type ft       ON ft.id = fp.fertilizer_type_id
WHERE fs.status IN ('pending', 'due', 'overdue')
ORDER BY fs.due_date ASC, e.name, b.block_code;

COMMENT ON VIEW public.v_fertilizer_schedule_alerts IS
    'All pending/due/overdue fertilizer schedule entries across all estates, ordered by urgency. Used by the alerts API endpoint.';

COMMIT;
