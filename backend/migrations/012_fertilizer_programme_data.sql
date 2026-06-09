-- =============================================================================
-- Migration 012: Fertilizer Rotation Planner — programme seed data
-- =============================================================================
-- Populates fertilizer_programme with schedule templates for all 4 estates.
--
-- Design basis:
--   - TRI SP03 mid-country programme (3 applications/year for VP mature tea)
--   - Zone modifiers: High-zone blocks get lower N rates (leaching is lower at
--     elevation); Low-zone blocks get higher N + shorter intervals (faster
--     leaching from heavy rainfall)
--   - growth_stage_filter = 'Immature' rows are excluded from N-heavy products;
--     Immature blocks get a lighter EP_GOLD-only programme
--   - interval_weeks for application_no=1 is weeks from crop year start (Apr 1)
--   - Dolomite applied once per year as a soil amendment across all zones
--
-- Estate zones:
--   Kundasale  (46f698d6) — Mid  (920–950 m)   → 3 apps T0_200 + 2 apps U750
--   Ramboda    (4ac7dfbd) — High (1380–1430 m)  → 3 apps T0_200 + 2 apps U750 (lower rates)
--   Hunasgiriya(b197ff2c) — Low  (575–640 m)    → 4 apps T0_200 + 2 apps U750 (higher rates, shorter intervals)
--   Haputale   (b4350958) — High (1470–1530 m)  → 3 apps T0_200 + 2 apps U750 (same as Ramboda High)
--
-- fertilizer_type UUIDs (from 001_initial_schema seed, unchanged):
--   T0_200   → 970a1914-7703-4e14-9a86-0dc3fc4398db
--   U750     → c6569d6f-4cb3-4a8b-b66f-e83f8197f267
--   EP_GOLD  → 6ab29529-2147-4707-b687-99ce36fbb4bd
--   MOP      → f44d3fbc-6377-49d3-95be-dab9fbfdc4f0
--   RPR      → 611d009b-213d-43f6-8b8b-2389a56d5e95
--   DOLOMITE → f88dad3d-87de-4575-87f4-a761654ab6da
--
-- Estate UUIDs (from 002_sample_data seed, unchanged):
--   Kundasale   → 46f698d6-55ba-4d0c-9402-58321361f3bc
--   Ramboda     → 4ac7dfbd-4628-481d-bfab-56ffde9d33bb
--   Hunasgiriya → b197ff2c-7063-473f-850d-190c9f9dd300
--   Haputale    → b4350958-2568-42c0-adfc-d1fa8d2f7a69
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- KUNDASALE ESTATE — Mid zone (920–950 m)
-- Standard 3-application T0_200 programme + 2-application U750 + annual MOP
-- Immature blocks (C1) get EP_GOLD only — no heavy N
-- ---------------------------------------------------------------------------

INSERT INTO public.fertilizer_programme (
    id, estate_id, fertilizer_type_id,
    application_no, interval_weeks, rate_kg_per_ha,
    zone_override, growth_stage_filter, notes
) VALUES

-- T0_200 × 3 per year, 8-week intervals, all zones, Mature + Young only
(public.uuid_generate_v4(), '46f698d6-55ba-4d0c-9402-58321361f3bc', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 1, 4,  200.00, NULL, 'Mature',   'First top-dress after crop year start (April)'),

(public.uuid_generate_v4(), '46f698d6-55ba-4d0c-9402-58321361f3bc', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 2, 8,  200.00, NULL, 'Mature',   'Second top-dress, mid-season'),

(public.uuid_generate_v4(), '46f698d6-55ba-4d0c-9402-58321361f3bc', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 3, 8,  175.00, NULL, 'Mature',   'Third top-dress, reduced rate pre-dry season'),

-- T0_200 for Young blocks — lighter rate, same schedule
(public.uuid_generate_v4(), '46f698d6-55ba-4d0c-9402-58321361f3bc', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 1, 4,  150.00, NULL, 'Young',    'Young block first top-dress — 75% of mature rate'),

(public.uuid_generate_v4(), '46f698d6-55ba-4d0c-9402-58321361f3bc', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 2, 8,  150.00, NULL, 'Young',    'Young block second top-dress'),

(public.uuid_generate_v4(), '46f698d6-55ba-4d0c-9402-58321361f3bc', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 3, 8,  125.00, NULL, 'Young',    'Young block third top-dress — reduced pre-dry'),

-- U750 × 2 per year (heavier compound blend, Mature only)
(public.uuid_generate_v4(), '46f698d6-55ba-4d0c-9402-58321361f3bc', 'c6569d6f-4cb3-4a8b-b66f-e83f8197f267',
 1, 6,  750.00, NULL, 'Mature',   'U750 first application, 6 weeks after crop year'),

(public.uuid_generate_v4(), '46f698d6-55ba-4d0c-9402-58321361f3bc', 'c6569d6f-4cb3-4a8b-b66f-e83f8197f267',
 2, 16, 750.00, NULL, 'Mature',   'U750 second application, 16 weeks later'),

-- EP_GOLD for Immature blocks only (no heavy N on young root systems)
(public.uuid_generate_v4(), '46f698d6-55ba-4d0c-9402-58321361f3bc', '6ab29529-2147-4707-b687-99ce36fbb4bd',
 1, 6,  100.00, NULL, 'Immature', 'EP Gold first application for immature blocks'),

(public.uuid_generate_v4(), '46f698d6-55ba-4d0c-9402-58321361f3bc', '6ab29529-2147-4707-b687-99ce36fbb4bd',
 2, 12, 100.00, NULL, 'Immature', 'EP Gold second application for immature blocks'),

-- MOP × 1 per year, all growth stages (potassium supplement)
(public.uuid_generate_v4(), '46f698d6-55ba-4d0c-9402-58321361f3bc', 'f44d3fbc-6377-49d3-95be-dab9fbfdc4f0',
 1, 8,  100.00, NULL, NULL,       'Annual MOP potassium supplement'),

-- Dolomite × 1 per year, soil pH correction
(public.uuid_generate_v4(), '46f698d6-55ba-4d0c-9402-58321361f3bc', 'f88dad3d-87de-4575-87f4-a761654ab6da',
 1, 2,  300.00, NULL, NULL,       'Annual dolomite application for pH correction');


-- ---------------------------------------------------------------------------
-- RAMBODA HEIGHTS ESTATE — High zone (1380–1430 m)
-- High elevation = lower leaching, slightly lower N rates, same 3-app cadence
-- ---------------------------------------------------------------------------

INSERT INTO public.fertilizer_programme (
    id, estate_id, fertilizer_type_id,
    application_no, interval_weeks, rate_kg_per_ha,
    zone_override, growth_stage_filter, notes
) VALUES

-- T0_200 × 3, High zone rates (175/175/150 vs Kundasale's 200/200/175)
(public.uuid_generate_v4(), '4ac7dfbd-4628-481d-bfab-56ffde9d33bb', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 1, 4,  175.00, NULL, 'Mature',   'High-zone first top-dress — reduced N vs mid-country'),

(public.uuid_generate_v4(), '4ac7dfbd-4628-481d-bfab-56ffde9d33bb', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 2, 9,  175.00, NULL, 'Mature',   'High-zone second top-dress, 9-week interval (slower growth)'),

(public.uuid_generate_v4(), '4ac7dfbd-4628-481d-bfab-56ffde9d33bb', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 3, 9,  150.00, NULL, 'Mature',   'High-zone third top-dress, reduced rate'),

-- T0_200 Young blocks
(public.uuid_generate_v4(), '4ac7dfbd-4628-481d-bfab-56ffde9d33bb', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 1, 4,  130.00, NULL, 'Young',    'High-zone young block first top-dress'),

(public.uuid_generate_v4(), '4ac7dfbd-4628-481d-bfab-56ffde9d33bb', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 2, 9,  130.00, NULL, 'Young',    'High-zone young block second top-dress'),

(public.uuid_generate_v4(), '4ac7dfbd-4628-481d-bfab-56ffde9d33bb', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 3, 9,  110.00, NULL, 'Young',    'High-zone young block third top-dress'),

-- U750 × 2
(public.uuid_generate_v4(), '4ac7dfbd-4628-481d-bfab-56ffde9d33bb', 'c6569d6f-4cb3-4a8b-b66f-e83f8197f267',
 1, 6,  700.00, NULL, 'Mature',   'High-zone U750 first — slightly reduced rate'),

(public.uuid_generate_v4(), '4ac7dfbd-4628-481d-bfab-56ffde9d33bb', 'c6569d6f-4cb3-4a8b-b66f-e83f8197f267',
 2, 18, 700.00, NULL, 'Mature',   'High-zone U750 second — longer interval at elevation'),

-- EP_GOLD for Immature
(public.uuid_generate_v4(), '4ac7dfbd-4628-481d-bfab-56ffde9d33bb', '6ab29529-2147-4707-b687-99ce36fbb4bd',
 1, 6,   90.00, NULL, 'Immature', 'High-zone immature EP Gold first'),

(public.uuid_generate_v4(), '4ac7dfbd-4628-481d-bfab-56ffde9d33bb', '6ab29529-2147-4707-b687-99ce36fbb4bd',
 2, 12,  90.00, NULL, 'Immature', 'High-zone immature EP Gold second'),

-- MOP annual
(public.uuid_generate_v4(), '4ac7dfbd-4628-481d-bfab-56ffde9d33bb', 'f44d3fbc-6377-49d3-95be-dab9fbfdc4f0',
 1, 8,   90.00, NULL, NULL,       'Annual MOP — high zone, slightly lower K demand'),

-- Dolomite annual
(public.uuid_generate_v4(), '4ac7dfbd-4628-481d-bfab-56ffde9d33bb', 'f88dad3d-87de-4575-87f4-a761654ab6da',
 1, 2,  300.00, NULL, NULL,       'Annual dolomite, same rate as other estates');


-- ---------------------------------------------------------------------------
-- HUNASGIRIYA ESTATE — Low zone (575–640 m)
-- Low elevation = heavy rainfall, faster leaching → 4 T0_200 applications,
-- shorter intervals, higher rates. 8-day plucking round (vs 7-day at others).
-- ---------------------------------------------------------------------------

INSERT INTO public.fertilizer_programme (
    id, estate_id, fertilizer_type_id,
    application_no, interval_weeks, rate_kg_per_ha,
    zone_override, growth_stage_filter, notes
) VALUES

-- T0_200 × 4 per year (extra application to counter leaching)
(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 1, 4,  225.00, NULL, 'Mature',   'Low-zone first top-dress — increased rate for leaching'),

(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 2, 6,  225.00, NULL, 'Mature',   'Low-zone second top-dress, 6-week interval'),

(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 3, 6,  200.00, NULL, 'Mature',   'Low-zone third top-dress'),

(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 4, 6,  200.00, NULL, 'Mature',   'Low-zone fourth top-dress — extra application'),

-- T0_200 Young blocks (low zone)
(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 1, 4,  170.00, NULL, 'Young',    'Low-zone young block first top-dress'),

(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 2, 6,  170.00, NULL, 'Young',    'Low-zone young block second top-dress'),

(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 3, 6,  150.00, NULL, 'Young',    'Low-zone young block third top-dress'),

(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 4, 6,  150.00, NULL, 'Young',    'Low-zone young block fourth top-dress'),

-- U750 × 2 (higher rate to compensate leaching)
(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', 'c6569d6f-4cb3-4a8b-b66f-e83f8197f267',
 1, 5,  750.00, NULL, 'Mature',   'Low-zone U750 first, earlier start'),

(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', 'c6569d6f-4cb3-4a8b-b66f-e83f8197f267',
 2, 14, 750.00, NULL, 'Mature',   'Low-zone U750 second'),

-- RPR × 1 per year (low zone soils have higher Al/Fe coupling — needs rock phosphate)
(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', '611d009b-213d-43f6-8b8b-2389a56d5e95',
 1, 8,  250.00, NULL, 'Mature',   'Annual RPR — low-zone soils benefit from slow-release P'),

-- EP_GOLD Immature
(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', '6ab29529-2147-4707-b687-99ce36fbb4bd',
 1, 5,  110.00, NULL, 'Immature', 'Low-zone immature EP Gold first'),

(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', '6ab29529-2147-4707-b687-99ce36fbb4bd',
 2, 10, 110.00, NULL, 'Immature', 'Low-zone immature EP Gold second'),

-- MOP annual (higher rate — heavy rainfall depletes K faster)
(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', 'f44d3fbc-6377-49d3-95be-dab9fbfdc4f0',
 1, 6,  125.00, NULL, NULL,       'Annual MOP — higher K rate for low-zone leaching'),

-- Dolomite annual
(public.uuid_generate_v4(), 'b197ff2c-7063-473f-850d-190c9f9dd300', 'f88dad3d-87de-4575-87f4-a761654ab6da',
 1, 2,  300.00, NULL, NULL,       'Annual dolomite pH correction');


-- ---------------------------------------------------------------------------
-- HAPUTALE PARK ESTATE — High zone (1470–1530 m)
-- Highest elevation across all estates. Same profile as Ramboda (High),
-- but slightly longer intervals (slower growth at 1500 m+).
-- ---------------------------------------------------------------------------

INSERT INTO public.fertilizer_programme (
    id, estate_id, fertilizer_type_id,
    application_no, interval_weeks, rate_kg_per_ha,
    zone_override, growth_stage_filter, notes
) VALUES

-- T0_200 × 3, slightly longer intervals than Ramboda
(public.uuid_generate_v4(), 'b4350958-2568-42c0-adfc-d1fa8d2f7a69', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 1, 4,  175.00, NULL, 'Mature',   'Uva high-zone first top-dress'),

(public.uuid_generate_v4(), 'b4350958-2568-42c0-adfc-d1fa8d2f7a69', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 2, 10, 175.00, NULL, 'Mature',   'Uva high-zone second top-dress, 10-week interval'),

(public.uuid_generate_v4(), 'b4350958-2568-42c0-adfc-d1fa8d2f7a69', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 3, 10, 150.00, NULL, 'Mature',   'Uva high-zone third top-dress, reduced rate'),

-- T0_200 Young blocks
(public.uuid_generate_v4(), 'b4350958-2568-42c0-adfc-d1fa8d2f7a69', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 1, 4,  130.00, NULL, 'Young',    'Uva high-zone young first top-dress'),

(public.uuid_generate_v4(), 'b4350958-2568-42c0-adfc-d1fa8d2f7a69', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 2, 10, 130.00, NULL, 'Young',    'Uva high-zone young second top-dress'),

(public.uuid_generate_v4(), 'b4350958-2568-42c0-adfc-d1fa8d2f7a69', '970a1914-7703-4e14-9a86-0dc3fc4398db',
 3, 10, 110.00, NULL, 'Young',    'Uva high-zone young third top-dress'),

-- U750 × 2 (same profile as Ramboda)
(public.uuid_generate_v4(), 'b4350958-2568-42c0-adfc-d1fa8d2f7a69', 'c6569d6f-4cb3-4a8b-b66f-e83f8197f267',
 1, 6,  700.00, NULL, 'Mature',   'Uva high-zone U750 first'),

(public.uuid_generate_v4(), 'b4350958-2568-42c0-adfc-d1fa8d2f7a69', 'c6569d6f-4cb3-4a8b-b66f-e83f8197f267',
 2, 20, 700.00, NULL, 'Mature',   'Uva high-zone U750 second — longest interval, coolest estate'),

-- EP_GOLD Immature
(public.uuid_generate_v4(), 'b4350958-2568-42c0-adfc-d1fa8d2f7a69', '6ab29529-2147-4707-b687-99ce36fbb4bd',
 1, 6,   90.00, NULL, 'Immature', 'Uva high-zone immature EP Gold first'),

(public.uuid_generate_v4(), 'b4350958-2568-42c0-adfc-d1fa8d2f7a69', '6ab29529-2147-4707-b687-99ce36fbb4bd',
 2, 12,  90.00, NULL, 'Immature', 'Uva high-zone immature EP Gold second'),

-- MOP annual
(public.uuid_generate_v4(), 'b4350958-2568-42c0-adfc-d1fa8d2f7a69', 'f44d3fbc-6377-49d3-95be-dab9fbfdc4f0',
 1, 8,   90.00, NULL, NULL,       'Annual MOP — high zone Uva'),

-- Dolomite annual — Uva soils are notably acidic, same rate
(public.uuid_generate_v4(), 'b4350958-2568-42c0-adfc-d1fa8d2f7a69', 'f88dad3d-87de-4575-87f4-a761654ab6da',
 1, 2,  300.00, NULL, NULL,       'Annual dolomite — Uva acid soil correction');


-- ---------------------------------------------------------------------------
-- Verify row counts — expected totals per estate:
--   Kundasale   : 12 rows (6 T0_200 + 2 U750 + 2 EP_GOLD + 1 MOP + 1 DOLOMITE)
--   Ramboda     : 12 rows (same structure, high-zone rates)
--   Hunasgiriya : 15 rows (8 T0_200 + 2 U750 + 1 RPR + 2 EP_GOLD + 1 MOP + 1 DOLOMITE) -- extra T0 app + RPR
--   Haputale    : 12 rows (same as Ramboda)
--   TOTAL       : 51 rows
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    v_total   integer;
    v_kun     integer;
    v_rmb     integer;
    v_hun     integer;
    v_hap     integer;
BEGIN
    SELECT COUNT(*) INTO v_total FROM public.fertilizer_programme;
    SELECT COUNT(*) INTO v_kun   FROM public.fertilizer_programme WHERE estate_id = '46f698d6-55ba-4d0c-9402-58321361f3bc';
    SELECT COUNT(*) INTO v_rmb   FROM public.fertilizer_programme WHERE estate_id = '4ac7dfbd-4628-481d-bfab-56ffde9d33bb';
    SELECT COUNT(*) INTO v_hun   FROM public.fertilizer_programme WHERE estate_id = 'b197ff2c-7063-473f-850d-190c9f9dd300';
    SELECT COUNT(*) INTO v_hap   FROM public.fertilizer_programme WHERE estate_id = 'b4350958-2568-42c0-adfc-d1fa8d2f7a69';

    RAISE NOTICE 'fertilizer_programme rows — Total: %, Kundasale: %, Ramboda: %, Hunasgiriya: %, Haputale: %',
        v_total, v_kun, v_rmb, v_hun, v_hap;

    IF v_kun != 12 THEN RAISE EXCEPTION 'Kundasale row count mismatch: expected 12, got %', v_kun; END IF;
    IF v_rmb != 12 THEN RAISE EXCEPTION 'Ramboda row count mismatch: expected 12, got %', v_rmb; END IF;
    IF v_hun != 15 THEN RAISE EXCEPTION 'Hunasgiriya row count mismatch: expected 15, got %', v_hun; END IF;
    IF v_hap != 12 THEN RAISE EXCEPTION 'Haputale row count mismatch: expected 12, got %', v_hap; END IF;
END $$;

COMMIT;
