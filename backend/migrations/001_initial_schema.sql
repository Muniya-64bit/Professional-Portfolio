-- =============================================================================
-- KVPL Input & Resource Optimization System
-- Database Schema — PostgreSQL
-- Initial Migration
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- CORE ENTITIES
-- =============================================================================

CREATE TABLE estate (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(150) NOT NULL,
    region          VARCHAR(100),
    total_blocks    INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE factory (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id   UUID NOT NULL REFERENCES estate(id) ON DELETE CASCADE,
    name        VARCHAR(150) NOT NULL,
    location    VARCHAR(200),
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE "user" (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id   UUID REFERENCES estate(id) ON DELETE SET NULL,
    name        VARCHAR(150) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    role        VARCHAR(50) NOT NULL CHECK (role IN (
                    'admin',
                    'estate_manager',
                    'field_supervisor',
                    'factory_manager',
                    'finance',
                    'agronomist'
                )),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE block (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id       UUID NOT NULL REFERENCES estate(id) ON DELETE CASCADE,
    block_code      VARCHAR(50) NOT NULL,
    soil_type       VARCHAR(100),
    growth_stage    VARCHAR(100),
    area_hectares   DECIMAL(8, 2),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (estate_id, block_code)
);

-- =============================================================================
-- MODULE 1: FERTILIZER ROTATION PLANNER
-- =============================================================================

CREATE TABLE fertilizer_type (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code                VARCHAR(50) NOT NULL UNIQUE,
    name                VARCHAR(150) NOT NULL,
    description         TEXT,
    default_dosage_kg   DECIMAL(8, 3),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE fertilizer_application (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    block_id            UUID NOT NULL REFERENCES block(id) ON DELETE CASCADE,
    fertilizer_type_id  UUID NOT NULL REFERENCES fertilizer_type(id),
    applied_by          UUID REFERENCES "user"(id) ON DELETE SET NULL,
    application_date    DATE NOT NULL,
    quantity_kg         DECIMAL(10, 3) NOT NULL CHECK (quantity_kg > 0),
    recommendation      VARCHAR(20) CHECK (recommendation IN ('apply_now', 'delay', 'increase_dosage')),
    notes               TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE fertilizer_recommendation (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    block_id        UUID NOT NULL REFERENCES block(id) ON DELETE CASCADE,
    generated_by    UUID REFERENCES "user"(id) ON DELETE SET NULL,
    recommended_for DATE NOT NULL,
    action          VARCHAR(20) NOT NULL CHECK (action IN ('apply_now', 'delay', 'increase_dosage')),
    rationale       TEXT,
    is_overridden   BOOLEAN NOT NULL DEFAULT FALSE,
    override_reason TEXT,
    overridden_by   UUID REFERENCES "user"(id) ON DELETE SET NULL,
    overridden_at   TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- MODULE 2: INPUT COST VS YIELD ROI CALCULATOR
-- =============================================================================

CREATE TABLE input_cost (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id               UUID NOT NULL REFERENCES estate(id) ON DELETE CASCADE,
    year                    SMALLINT NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    month                   SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    fertilizer_cost_lkr     DECIMAL(14, 2) NOT NULL DEFAULT 0,
    chemical_cost_lkr       DECIMAL(14, 2) NOT NULL DEFAULT 0,
    labour_input_cost_lkr   DECIMAL(14, 2) NOT NULL DEFAULT 0,
    other_cost_lkr          DECIMAL(14, 2) NOT NULL DEFAULT 0,
    total_cost_lkr          DECIMAL(14, 2) GENERATED ALWAYS AS (
                                fertilizer_cost_lkr +
                                chemical_cost_lkr +
                                labour_input_cost_lkr +
                                other_cost_lkr
                            ) STORED,
    source                  VARCHAR(100),
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (estate_id, year, month)
);

CREATE TABLE yield_record (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id   UUID NOT NULL REFERENCES estate(id) ON DELETE CASCADE,
    year        SMALLINT NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    month       SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    yield_kg    DECIMAL(14, 3) NOT NULL CHECK (yield_kg >= 0),
    source      VARCHAR(100),
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (estate_id, year, month)
);

CREATE TABLE roi_snapshot (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id       UUID NOT NULL REFERENCES estate(id) ON DELETE CASCADE,
    year            SMALLINT NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    month           SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    cost_per_kg     DECIMAL(10, 4),
    rank            SMALLINT,
    is_flagged      BOOLEAN NOT NULL DEFAULT FALSE,
    flag_reason     TEXT,
    computed_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (estate_id, year, month)
);

-- =============================================================================
-- MODULE 3: WATER USAGE EFFICIENCY REPORT
-- =============================================================================

CREATE TABLE water_baseline (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    factory_id          UUID NOT NULL REFERENCES factory(id) ON DELETE CASCADE,
    baseline_year       SMALLINT NOT NULL CHECK (baseline_year BETWEEN 2000 AND 2100),
    baseline_intensity  DECIMAL(10, 4) NOT NULL,
    annual_target_pct   DECIMAL(5, 2) NOT NULL DEFAULT 2.00,
    set_by              UUID REFERENCES "user"(id) ON DELETE SET NULL,
    set_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (factory_id)
);

CREATE TABLE water_usage (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    factory_id      UUID NOT NULL REFERENCES factory(id) ON DELETE CASCADE,
    year            SMALLINT NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    month           SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    water_m3        DECIMAL(12, 3) NOT NULL CHECK (water_m3 >= 0),
    yield_kg        DECIMAL(14, 3) NOT NULL CHECK (yield_kg >= 0),
    intensity       DECIMAL(10, 6) GENERATED ALWAYS AS (
                        CASE WHEN yield_kg = 0 THEN NULL
                             ELSE water_m3 / yield_kg
                        END
                    ) STORED,
    track_status    VARCHAR(20) CHECK (track_status IN ('on_track', 'at_risk', 'off_track')),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (factory_id, year, month)
);

-- =============================================================================
-- MODULE 4: LABOUR ALLOCATION OPTIMIZER
-- =============================================================================

CREATE TABLE labour_plan (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id       UUID NOT NULL REFERENCES estate(id) ON DELETE CASCADE,
    created_by      UUID REFERENCES "user"(id) ON DELETE SET NULL,
    week_start      DATE NOT NULL,
    total_workers   INTEGER NOT NULL CHECK (total_workers > 0),
    target_kg       DECIMAL(14, 3),
    status          VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'published', 'completed')),
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (estate_id, week_start)
);

CREATE TABLE block_allocation (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    labour_plan_id      UUID NOT NULL REFERENCES labour_plan(id) ON DELETE CASCADE,
    block_id            UUID NOT NULL REFERENCES block(id) ON DELETE CASCADE,
    allocated_workers   INTEGER NOT NULL CHECK (allocated_workers >= 0),
    expected_yield_kg   DECIMAL(10, 3),
    actual_yield_kg     DECIMAL(10, 3),
    plucking_rounds     SMALLINT NOT NULL DEFAULT 1 CHECK (plucking_rounds > 0),
    productivity_ratio  DECIMAL(8, 4),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (labour_plan_id, block_id)
);

-- =============================================================================
-- AUDIT LOG (cross-module)
-- =============================================================================

CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES "user"(id) ON DELETE SET NULL,
    table_name  VARCHAR(100) NOT NULL,
    record_id   UUID,
    action      VARCHAR(20) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_data    JSONB,
    new_data    JSONB,
    changed_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX idx_block_estate        ON block(estate_id);
CREATE INDEX idx_fert_app_block      ON fertilizer_application(block_id);
CREATE INDEX idx_fert_app_date       ON fertilizer_application(application_date DESC);
CREATE INDEX idx_fert_rec_block      ON fertilizer_recommendation(block_id);
CREATE INDEX idx_fert_rec_date       ON fertilizer_recommendation(recommended_for DESC);
CREATE INDEX idx_input_cost_period   ON input_cost(estate_id, year, month);
CREATE INDEX idx_yield_record_period ON yield_record(estate_id, year, month);
CREATE INDEX idx_roi_period          ON roi_snapshot(year, month);
CREATE INDEX idx_roi_flagged         ON roi_snapshot(is_flagged) WHERE is_flagged = TRUE;
CREATE INDEX idx_water_factory       ON water_usage(factory_id, year, month);
CREATE INDEX idx_water_status        ON water_usage(track_status);
CREATE INDEX idx_labour_plan_estate  ON labour_plan(estate_id, week_start DESC);
CREATE INDEX idx_block_alloc_plan    ON block_allocation(labour_plan_id);
CREATE INDEX idx_audit_table         ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_user          ON audit_log(user_id);
CREATE INDEX idx_audit_time          ON audit_log(changed_at DESC);

-- =============================================================================
-- SEED: KVPL FERTILIZER TYPES
-- =============================================================================

INSERT INTO fertilizer_type (code, name, description, default_dosage_kg) VALUES
    ('T0_200',  'T0 200',          'Straight nitrogen top-dress',           200.0),
    ('U750',    'U750',            'Urea blend 750 formulation',            750.0),
    ('EP_GOLD', 'EP Gold',         'Compound NPK estate blend',             150.0),
    ('MOP',     'Muriate of Potash','Potassium supplement',                 100.0),
    ('RPR',     'Rock Phosphate',  'Slow-release phosphate source',         250.0),
    ('DOLOMITE','Dolomite',        'Calcium-magnesium soil amendment',      300.0);

-- =============================================================================
-- HELPFUL VIEWS
-- =============================================================================

CREATE VIEW v_roi_current_month AS
SELECT
    e.name          AS estate,
    r.year,
    r.month,
    r.cost_per_kg,
    r.rank,
    r.is_flagged,
    r.flag_reason
FROM roi_snapshot r
JOIN estate e ON e.id = r.estate_id
WHERE (r.year, r.month) = (
    SELECT year, month FROM roi_snapshot
    ORDER BY year DESC, month DESC LIMIT 1
)
ORDER BY r.rank;

CREATE VIEW v_water_status_latest AS
SELECT
    f.name          AS factory,
    e.name          AS estate,
    w.year,
    w.month,
    w.water_m3,
    w.yield_kg,
    w.intensity     AS intensity_m3_per_kg,
    wb.baseline_intensity,
    w.track_status
FROM water_usage w
JOIN factory f  ON f.id = w.factory_id
JOIN estate e   ON e.id = f.estate_id
LEFT JOIN water_baseline wb ON wb.factory_id = w.factory_id
WHERE (w.year, w.month) = (
    SELECT year, month FROM water_usage
    ORDER BY year DESC, month DESC LIMIT 1
)
ORDER BY w.track_status, f.name;

CREATE VIEW v_block_fert_summary AS
SELECT
    b.block_code,
    e.name          AS estate,
    ft.code         AS fertilizer,
    COUNT(*)        AS applications,
    SUM(fa.quantity_kg) AS total_kg,
    MAX(fa.application_date) AS last_applied
FROM fertilizer_application fa
JOIN block b            ON b.id = fa.block_id
JOIN estate e           ON e.id = b.estate_id
JOIN fertilizer_type ft ON ft.id = fa.fertilizer_type_id
WHERE fa.application_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY b.block_code, e.name, ft.code;
