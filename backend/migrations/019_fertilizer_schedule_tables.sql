-- Migration 019: Fertilizer programme, schedule and schedule-entry tables
-- These tables back the fertilizer.py blueprint (fertilizer rotation tab).

-- Extension already enabled in 001, but guard anyway
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── fertilizer_programme ────────────────────────────────────────────────────
-- One row per (estate, fertilizer type, application round).
-- Defines how often and at what rate each fertilizer should be applied.
CREATE TABLE IF NOT EXISTS fertilizer_programme (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id           UUID NOT NULL REFERENCES estate(id) ON DELETE CASCADE,
    fertilizer_type_id  UUID NOT NULL REFERENCES fertilizer_type(id),
    application_no      SMALLINT NOT NULL CHECK (application_no > 0),
    interval_weeks      SMALLINT NOT NULL CHECK (interval_weeks > 0),
    rate_kg_per_ha      DECIMAL(10,3) NOT NULL CHECK (rate_kg_per_ha > 0),
    zone_override       VARCHAR(50),        -- NULL = applies to all zones
    growth_stage_filter VARCHAR(50),        -- NULL = applies to all stages
    notes               TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (estate_id, fertilizer_type_id, application_no)
);

-- ── fertilizer_schedule ─────────────────────────────────────────────────────
-- One header row per (estate, calendar month). Generated monthly by the scheduler.
CREATE TABLE IF NOT EXISTS fertilizer_schedule (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id       UUID NOT NULL REFERENCES estate(id) ON DELETE CASCADE,
    period_start    DATE NOT NULL,          -- first day of the month
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'closed')),
    generated_by    UUID REFERENCES "user"(id) ON DELETE SET NULL,
    generated_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (estate_id, period_start)
);

-- ── fertilizer_schedule_entry ───────────────────────────────────────────────
-- One row per block × programme step within a schedule.
CREATE TABLE IF NOT EXISTS fertilizer_schedule_entry (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_id             UUID NOT NULL REFERENCES fertilizer_schedule(id) ON DELETE CASCADE,
    block_id                UUID NOT NULL REFERENCES block(id) ON DELETE CASCADE,
    programme_id            UUID NOT NULL REFERENCES fertilizer_programme(id) ON DELETE CASCADE,
    due_date                DATE NOT NULL,
    status                  VARCHAR(20) NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'due', 'overdue', 'done', 'skipped')),
    scheduled_rate_kg_per_ha DECIMAL(10,3),
    actual_rate_kg_per_ha   DECIMAL(10,3),
    completed_at            TIMESTAMP,
    completed_by            UUID REFERENCES "user"(id) ON DELETE SET NULL,
    notes                   TEXT,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (schedule_id, block_id, programme_id)
);

-- ── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_fert_prog_estate    ON fertilizer_programme(estate_id);
CREATE INDEX IF NOT EXISTS idx_fert_sched_estate   ON fertilizer_schedule(estate_id);
CREATE INDEX IF NOT EXISTS idx_fert_sched_period   ON fertilizer_schedule(period_start DESC);
CREATE INDEX IF NOT EXISTS idx_fert_entry_schedule ON fertilizer_schedule_entry(schedule_id);
CREATE INDEX IF NOT EXISTS idx_fert_entry_block    ON fertilizer_schedule_entry(block_id);
CREATE INDEX IF NOT EXISTS idx_fert_entry_due      ON fertilizer_schedule_entry(due_date);
CREATE INDEX IF NOT EXISTS idx_fert_entry_status   ON fertilizer_schedule_entry(status);

-- ── Seed: programme steps for each estate ───────────────────────────────────
-- 4 application rounds (T0→U750→EP_GOLD→MOP) every 12 weeks for every estate.
INSERT INTO fertilizer_programme
    (estate_id, fertilizer_type_id, application_no, interval_weeks, rate_kg_per_ha, notes)
SELECT
    e.id,
    ft.id,
    round_no,
    12,
    ft.default_dosage_kg,
    'Auto-seeded programme step'
FROM estate e
CROSS JOIN fertilizer_type ft
CROSS JOIN (VALUES (1),(2),(3),(4)) AS r(round_no)
WHERE ft.code IN ('T0_200', 'U750', 'EP_GOLD', 'MOP')
ON CONFLICT (estate_id, fertilizer_type_id, application_no) DO NOTHING;
