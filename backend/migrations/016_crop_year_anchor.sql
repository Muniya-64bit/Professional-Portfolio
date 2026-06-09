-- =============================================================================
-- Migration 016: Crop Year Anchor + Growth Stage at Generation
-- =============================================================================
-- 1. Adds crop_year_start_month / crop_year_start_day to estate so the
--    scheduler can anchor application_no chains to the estate's crop year
--    rather than collapsing everything to today.
-- 2. Adds growth_stage_at_generation to fertilizer_schedule_entry so the
--    growth stage recorded at schedule generation time is preserved even if
--    the block's stage changes later.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Estate: crop year anchor columns
-- ---------------------------------------------------------------------------

ALTER TABLE public.estate
    ADD COLUMN IF NOT EXISTS crop_year_start_month SMALLINT NOT NULL DEFAULT 4,
    ADD COLUMN IF NOT EXISTS crop_year_start_day   SMALLINT NOT NULL DEFAULT 1;

COMMENT ON COLUMN public.estate.crop_year_start_month IS
    'Month (1–12) when this estate''s crop year begins. Default 4 = April (Sri Lanka standard).';
COMMENT ON COLUMN public.estate.crop_year_start_day IS
    'Day of month when this estate''s crop year begins. Default 1.';

-- ---------------------------------------------------------------------------
-- 2. Fertilizer schedule entry: growth stage captured at generation
-- ---------------------------------------------------------------------------

ALTER TABLE public.fertilizer_schedule_entry
    ADD COLUMN IF NOT EXISTS growth_stage_at_generation VARCHAR(50);

COMMENT ON COLUMN public.fertilizer_schedule_entry.growth_stage_at_generation IS
    'Growth stage of the block at the time this entry was generated. Preserved even if the block stage changes later.';

COMMIT;
