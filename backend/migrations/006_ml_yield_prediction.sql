-- =============================================================================
-- KVPL Input & Resource Optimization System
-- Migration 006: ML Yield Prediction Module
-- Adds: elevation_m, bush_age_yrs, zone to block
--       block_yield_record, estate_weather, yield_prediction tables
--       Sample data for all 4 estates
-- =============================================================================

-- =============================================================================
-- STEP 1: Extend block table with ML features
-- =============================================================================

ALTER TABLE block
    ADD COLUMN IF NOT EXISTS elevation_m      SMALLINT,
    ADD COLUMN IF NOT EXISTS bush_age_yrs     SMALLINT,
    ADD COLUMN IF NOT EXISTS zone             VARCHAR(20)
        CHECK (zone IN ('Low', 'Mid', 'High'));

-- =============================================================================
-- STEP 2: Block-level monthly yield records
-- =============================================================================

CREATE TABLE block_yield_record (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    block_id    UUID NOT NULL REFERENCES block(id) ON DELETE CASCADE,
    year        SMALLINT NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    month       SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    yield_kg    DECIMAL(10, 3) NOT NULL CHECK (yield_kg >= 0),
    source      VARCHAR(100),
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (block_id, year, month)
);

-- =============================================================================
-- STEP 3: Monthly weather data per estate
-- =============================================================================

CREATE TABLE estate_weather (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id           UUID NOT NULL REFERENCES estate(id) ON DELETE CASCADE,
    year                SMALLINT NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    month               SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    rainfall_mm         DECIMAL(8, 2),
    avg_temp_c          DECIMAL(5, 2),
    avg_humidity_pct    DECIMAL(5, 2),
    source              VARCHAR(100) DEFAULT 'manual_entry',
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (estate_id, year, month)
);

-- =============================================================================
-- STEP 4: ML model predictions (output table)
-- =============================================================================

CREATE TABLE yield_prediction (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    block_id            UUID NOT NULL REFERENCES block(id) ON DELETE CASCADE,
    labour_plan_id      UUID REFERENCES labour_plan(id) ON DELETE SET NULL,
    year                SMALLINT NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    month               SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    predicted_yield_kg  DECIMAL(10, 3) NOT NULL CHECK (predicted_yield_kg >= 0),
    confidence_low      DECIMAL(10, 3),
    confidence_high     DECIMAL(10, 3),
    model_version       VARCHAR(50),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (block_id, year, month)
);

-- =============================================================================
-- STEP 5: Indexes
-- =============================================================================

CREATE INDEX idx_block_yield_block   ON block_yield_record(block_id, year, month);
CREATE INDEX idx_block_yield_estate  ON block_yield_record(block_id);
CREATE INDEX idx_estate_weather      ON estate_weather(estate_id, year, month);
CREATE INDEX idx_yield_pred_block    ON yield_prediction(block_id, year, month);
CREATE INDEX idx_yield_pred_plan     ON yield_prediction(labour_plan_id);

-- =============================================================================
-- STEP 6: Populate new block columns for all 4 estates
-- =============================================================================

-- Kundasale Estate (Central, Mid elevation ~900-950m)
UPDATE block SET
    zone          = 'Mid',
    elevation_m   = CASE block_code
                        WHEN 'A1' THEN 920
                        WHEN 'A2' THEN 910
                        WHEN 'B1' THEN 935
                        WHEN 'B2' THEN 940
                        WHEN 'C1' THEN 905
                        WHEN 'D1' THEN 950
                    END,
    bush_age_yrs  = CASE block_code
                        WHEN 'A1' THEN 25
                        WHEN 'A2' THEN 8
                        WHEN 'B1' THEN 30
                        WHEN 'B2' THEN 22
                        WHEN 'C1' THEN 4
                        WHEN 'D1' THEN 28
                    END
WHERE estate_id = (SELECT id FROM estate WHERE name = 'Kundasale Estate');

-- Ramboda Heights (Central, High elevation ~1380-1420m)
UPDATE block SET
    zone          = 'High',
    elevation_m   = CASE block_code
                        WHEN 'E1' THEN 1380
                        WHEN 'E2' THEN 1400
                        WHEN 'F1' THEN 1420
                        WHEN 'F2' THEN 1390
                        WHEN 'G1' THEN 1410
                        WHEN 'G2' THEN 1395
                        WHEN 'H1' THEN 1430
                        WHEN 'H2' THEN 1415
                    END,
    bush_age_yrs  = CASE block_code
                        WHEN 'E1' THEN 20
                        WHEN 'E2' THEN 15
                        WHEN 'F1' THEN 6
                        WHEN 'F2' THEN 18
                        WHEN 'G1' THEN 25
                        WHEN 'G2' THEN 9
                        WHEN 'H1' THEN 22
                        WHEN 'H2' THEN 30
                    END
WHERE estate_id = (SELECT id FROM estate WHERE name = 'Ramboda Heights');

-- Hunasgiriya Estate (Western, Low elevation ~575-640m)
UPDATE block SET
    zone          = 'Low',
    elevation_m   = CASE block_code
                        WHEN 'I1' THEN 580  WHEN 'I2' THEN 590  WHEN 'I3' THEN 575
                        WHEN 'J1' THEN 600  WHEN 'J2' THEN 610  WHEN 'J3' THEN 595
                        WHEN 'K1' THEN 620  WHEN 'K2' THEN 615  WHEN 'K3' THEN 605
                        WHEN 'L1' THEN 630  WHEN 'L2' THEN 625  WHEN 'L3' THEN 618
                        WHEN 'M1' THEN 640  WHEN 'M2' THEN 635  WHEN 'M3' THEN 628
                    END,
    bush_age_yrs  = CASE block_code
                        WHEN 'I1' THEN 22   WHEN 'I2' THEN 18   WHEN 'I3' THEN 7
                        WHEN 'J1' THEN 25   WHEN 'J2' THEN 20   WHEN 'J3' THEN 3
                        WHEN 'K1' THEN 28   WHEN 'K2' THEN 24   WHEN 'K3' THEN 9
                        WHEN 'L1' THEN 30   WHEN 'L2' THEN 26   WHEN 'L3' THEN 32
                        WHEN 'M1' THEN 19   WHEN 'M2' THEN 6    WHEN 'M3' THEN 21
                    END
WHERE estate_id = (SELECT id FROM estate WHERE name = 'Hunasgiriya Estate');

-- Haputale Park (Uva, High elevation ~1470-1530m)
UPDATE block SET
    zone          = 'High',
    elevation_m   = CASE block_code
                        WHEN 'N1' THEN 1480 WHEN 'N2' THEN 1490 WHEN 'N3' THEN 1470
                        WHEN 'O1' THEN 1500 WHEN 'O2' THEN 1510 WHEN 'O3' THEN 1495
                        WHEN 'P1' THEN 1520 WHEN 'P2' THEN 1505
                        WHEN 'Q1' THEN 1530 WHEN 'Q2' THEN 1515
                    END,
    bush_age_yrs  = CASE block_code
                        WHEN 'N1' THEN 20   WHEN 'N2' THEN 25   WHEN 'N3' THEN 8
                        WHEN 'O1' THEN 30   WHEN 'O2' THEN 22   WHEN 'O3' THEN 27
                        WHEN 'P1' THEN 18   WHEN 'P2' THEN 5
                        WHEN 'Q1' THEN 35   WHEN 'Q2' THEN 15
                    END
WHERE estate_id = (SELECT id FROM estate WHERE name = 'Haputale Park');

-- =============================================================================
-- STEP 7: Sample block yield records (Kundasale, Jan–May 2026)
-- =============================================================================

INSERT INTO block_yield_record (block_id, year, month, yield_kg, source)
SELECT b.id, d.yr, d.mo, d.yield_kg, 'weighing_system'
FROM block b
JOIN estate e ON b.estate_id = e.id
JOIN (VALUES
    ('A1', 2026, 1, 84500.0), ('A1', 2026, 2, 89200.0), ('A1', 2026, 3, 94100.0),
    ('A1', 2026, 4, 91500.0), ('A1', 2026, 5, 93000.0),
    ('A2', 2026, 1, 67800.0), ('A2', 2026, 2, 71200.0), ('A2', 2026, 3, 75400.0),
    ('A2', 2026, 4, 73100.0), ('A2', 2026, 5, 74500.0),
    ('B1', 2026, 1, 95200.0), ('B1', 2026, 2, 100800.0), ('B1', 2026, 3, 106500.0),
    ('B1', 2026, 4, 103200.0), ('B1', 2026, 5, 105000.0),
    ('B2', 2026, 1, 88900.0), ('B2', 2026, 2, 94100.0), ('B2', 2026, 3, 99300.0),
    ('B2', 2026, 4, 96400.0), ('B2', 2026, 5, 98000.0),
    ('C1', 2026, 1, 45200.0), ('C1', 2026, 2, 47800.0), ('C1', 2026, 3, 50400.0),
    ('C1', 2026, 4, 48900.0), ('C1', 2026, 5, 49700.0),
    ('D1', 2026, 1, 111300.0), ('D1', 2026, 2, 117800.0), ('D1', 2026, 3, 124400.0),
    ('D1', 2026, 4, 120700.0), ('D1', 2026, 5, 122800.0)
) AS d(bc, yr, mo, yield_kg) ON b.block_code = d.bc
WHERE e.name = 'Kundasale Estate';

-- =============================================================================
-- STEP 8: Sample estate weather (all 4 estates, Jan–May 2026)
-- =============================================================================

-- Kundasale (Central, Mid elevation — moderate rainfall)
INSERT INTO estate_weather (estate_id, year, month, rainfall_mm, avg_temp_c, avg_humidity_pct, source)
SELECT e.id, w.yr, w.mo, w.rainfall, w.temp, w.humidity, 'manual_entry'
FROM estate e,
(VALUES
    (2026, 1, 185.5, 22.4, 78.2),
    (2026, 2, 210.3, 23.1, 80.5),
    (2026, 3, 245.8, 23.8, 82.1),
    (2026, 4, 198.2, 23.5, 81.3),
    (2026, 5, 220.6, 22.9, 79.8)
) AS w(yr, mo, rainfall, temp, humidity)
WHERE e.name = 'Kundasale Estate';

-- Ramboda Heights (Central, High elevation — cooler, higher rainfall)
INSERT INTO estate_weather (estate_id, year, month, rainfall_mm, avg_temp_c, avg_humidity_pct, source)
SELECT e.id, w.yr, w.mo, w.rainfall, w.temp, w.humidity, 'manual_entry'
FROM estate e,
(VALUES
    (2026, 1, 220.0, 18.2, 85.0),
    (2026, 2, 248.5, 18.9, 87.2),
    (2026, 3, 290.1, 19.5, 88.5),
    (2026, 4, 235.4, 19.1, 86.8),
    (2026, 5, 260.3, 18.7, 86.0)
) AS w(yr, mo, rainfall, temp, humidity)
WHERE e.name = 'Ramboda Heights';

-- Hunasgiriya (Western, Low elevation — warmer, less rainfall)
INSERT INTO estate_weather (estate_id, year, month, rainfall_mm, avg_temp_c, avg_humidity_pct, source)
SELECT e.id, w.yr, w.mo, w.rainfall, w.temp, w.humidity, 'manual_entry'
FROM estate e,
(VALUES
    (2026, 1, 145.2, 26.8, 72.5),
    (2026, 2, 162.8, 27.4, 74.1),
    (2026, 3, 198.5, 28.1, 76.3),
    (2026, 4, 175.3, 27.8, 75.0),
    (2026, 5, 185.9, 27.2, 73.8)
) AS w(yr, mo, rainfall, temp, humidity)
WHERE e.name = 'Hunasgiriya Estate';

-- Haputale Park (Uva, High elevation — dry zone, cooler)
INSERT INTO estate_weather (estate_id, year, month, rainfall_mm, avg_temp_c, avg_humidity_pct, source)
SELECT e.id, w.yr, w.mo, w.rainfall, w.temp, w.humidity, 'manual_entry'
FROM estate e,
(VALUES
    (2026, 1, 98.5,  17.5, 76.2),
    (2026, 2, 112.3, 18.1, 78.0),
    (2026, 3, 135.7, 18.8, 79.5),
    (2026, 4, 108.4, 18.4, 77.8),
    (2026, 5, 120.2, 17.9, 77.0)
) AS w(yr, mo, rainfall, temp, humidity)
WHERE e.name = 'Haputale Park';