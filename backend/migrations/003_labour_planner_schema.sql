-- =============================================================================
-- KVPL — Labour Planner Schema Enhancement
-- Migration 003
-- Adds: employee, worker_group, rotation_cycle, block_assignment
-- Replaces: block_allocation (dropped at end)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. EXTEND block TABLE
--    worker_capacity   → standard workers needed to cover this block in one day
--    plucking_interval → days between plucking rounds for this block
-- ---------------------------------------------------------------------------

ALTER TABLE block
    ADD COLUMN IF NOT EXISTS worker_capacity       INTEGER NOT NULL DEFAULT 15 CHECK (worker_capacity > 0),
    ADD COLUMN IF NOT EXISTS plucking_interval_days SMALLINT NOT NULL DEFAULT 7  CHECK (plucking_interval_days > 0);

COMMENT ON COLUMN block.worker_capacity        IS 'Standard workers needed to fully cover this block per plucking day';
COMMENT ON COLUMN block.plucking_interval_days IS 'Days between successive plucking rounds for this block';

-- ---------------------------------------------------------------------------
-- 2. EMPLOYEE
--    Individual field worker.  Distinct from the system "user" table which
--    holds managers/supervisors/admins.  An employee may also be a supervisor
--    (skill_type = supervisor) but never needs a login.
-- ---------------------------------------------------------------------------

CREATE TABLE employee (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id           UUID        NOT NULL REFERENCES estate(id) ON DELETE CASCADE,
    employee_code       VARCHAR(50) NOT NULL,
    full_name           VARCHAR(150) NOT NULL,
    gender              CHAR(1)     CHECK (gender IN ('M', 'F', 'O')),
    national_id         VARCHAR(50),
    hire_date           DATE        NOT NULL DEFAULT CURRENT_DATE,
    employment_type     VARCHAR(20) NOT NULL DEFAULT 'permanent'
                            CHECK (employment_type IN ('permanent', 'casual', 'seasonal')),
    skill_type          VARCHAR(30) NOT NULL DEFAULT 'plucker'
                            CHECK (skill_type IN ('plucker', 'general', 'supervisor', 'driver')),
    daily_wage_lkr      DECIMAL(10, 2),
    is_active           BOOLEAN     NOT NULL DEFAULT TRUE,
    notes               TEXT,
    created_at          TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP   NOT NULL DEFAULT NOW(),
    UNIQUE (estate_id, employee_code)
);

COMMENT ON TABLE employee IS 'Field-level workers (pluckers, supervisors, general labour). Not system users.';

-- ---------------------------------------------------------------------------
-- 3. WORKER GROUP  (a "gang" or team)
--    Each group is sized to match the worker_capacity of one block.
--    One supervisor per group — must be an employee with skill_type = supervisor.
-- ---------------------------------------------------------------------------

CREATE TABLE worker_group (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id       UUID        NOT NULL REFERENCES estate(id) ON DELETE CASCADE,
    group_code      VARCHAR(50) NOT NULL,
    group_name      VARCHAR(150) NOT NULL,
    supervisor_id   UUID        REFERENCES employee(id) ON DELETE SET NULL,
    capacity        INTEGER     NOT NULL DEFAULT 15 CHECK (capacity > 0),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP   NOT NULL DEFAULT NOW(),
    UNIQUE (estate_id, group_code)
);

COMMENT ON COLUMN worker_group.capacity IS 'Target headcount; should match the worker_capacity of the blocks this group covers';

-- ---------------------------------------------------------------------------
-- 4. WORKER GROUP MEMBER
--    Many-to-many between employee and worker_group with effective dates.
--    left_date NULL means the employee is still in the group.
--    A single employee can only be in one active group at a time (enforced by
--    the partial unique index below).
-- ---------------------------------------------------------------------------

CREATE TABLE worker_group_member (
    id              UUID      PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id        UUID      NOT NULL REFERENCES worker_group(id) ON DELETE CASCADE,
    employee_id     UUID      NOT NULL REFERENCES employee(id)    ON DELETE CASCADE,
    joined_date     DATE      NOT NULL DEFAULT CURRENT_DATE,
    left_date       DATE,
    is_active       BOOLEAN   NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    CHECK (left_date IS NULL OR left_date > joined_date)
);

-- One employee in only one active group at any time
CREATE UNIQUE INDEX uq_worker_group_member_active
    ON worker_group_member (employee_id)
    WHERE is_active = TRUE;

-- ---------------------------------------------------------------------------
-- 5. ROTATION CYCLE
--    Defines one full rotation pattern for an estate.
--    total_rounds = number of blocks in the estate (so every group visits
--    every block exactly once per cycle before it restarts).
--    current_round is incremented by the application each week.
-- ---------------------------------------------------------------------------

CREATE TABLE rotation_cycle (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id       UUID        NOT NULL REFERENCES estate(id) ON DELETE CASCADE,
    cycle_name      VARCHAR(150) NOT NULL,
    total_rounds    INTEGER     NOT NULL CHECK (total_rounds > 0),
    current_round   INTEGER     NOT NULL DEFAULT 1,
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_by      UUID        REFERENCES "user"(id) ON DELETE SET NULL,
    created_at      TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP   NOT NULL DEFAULT NOW(),
    CHECK (current_round BETWEEN 1 AND total_rounds)
);

COMMENT ON COLUMN rotation_cycle.total_rounds  IS 'Equal to the number of blocks — ensures every group covers every block once per cycle';
COMMENT ON COLUMN rotation_cycle.current_round IS 'Which round to use when auto-generating the next labour plan';

-- Only one active cycle per estate
CREATE UNIQUE INDEX uq_rotation_cycle_active
    ON rotation_cycle (estate_id)
    WHERE is_active = TRUE;

-- ---------------------------------------------------------------------------
-- 6. ROTATION ROUND BLOCK
--    For each (round, block) pair, record which worker_group is assigned.
--    Example for estate with 4 blocks:
--      Round 1: G1→A1, G2→A2, G3→B1, G4→B2
--      Round 2: G1→A2, G2→B1, G3→B2, G4→A1   ← each group shifts one block
--      ...and so on until every group has visited every block.
-- ---------------------------------------------------------------------------

CREATE TABLE rotation_round_block (
    id                  UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    rotation_cycle_id   UUID    NOT NULL REFERENCES rotation_cycle(id) ON DELETE CASCADE,
    round_number        INTEGER NOT NULL CHECK (round_number > 0),
    block_id            UUID    NOT NULL REFERENCES block(id)         ON DELETE CASCADE,
    worker_group_id     UUID    NOT NULL REFERENCES worker_group(id)  ON DELETE CASCADE,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (rotation_cycle_id, round_number, block_id),
    UNIQUE (rotation_cycle_id, round_number, worker_group_id)
);

COMMENT ON TABLE rotation_round_block IS 'Lookup table: for a given cycle round, which group covers which block. Defines the full rotation matrix.';

-- ---------------------------------------------------------------------------
-- 7. BLOCK ASSIGNMENT
--    Actual per-date assignment generated from the rotation.
--    One row per (block, date).  Linked to a labour_plan for the week.
--    When a manager overrides the rotation, is_manual_override = TRUE and
--    the original group is stored in original_group_id for audit purposes.
-- ---------------------------------------------------------------------------

CREATE TABLE block_assignment (
    id                      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    labour_plan_id          UUID        REFERENCES labour_plan(id) ON DELETE CASCADE,
    block_id                UUID        NOT NULL REFERENCES block(id)         ON DELETE CASCADE,
    worker_group_id         UUID        REFERENCES worker_group(id)           ON DELETE SET NULL,
    assignment_date         DATE        NOT NULL,

    -- rotation tracking
    rotation_cycle_id       UUID        REFERENCES rotation_cycle(id) ON DELETE SET NULL,
    rotation_round          INTEGER,

    -- manual override
    is_manual_override      BOOLEAN     NOT NULL DEFAULT FALSE,
    original_group_id       UUID        REFERENCES worker_group(id)  ON DELETE SET NULL,
    override_reason         TEXT,
    overridden_by           UUID        REFERENCES "user"(id)        ON DELETE SET NULL,
    overridden_at           TIMESTAMP,

    -- outcomes
    expected_yield_kg       DECIMAL(10, 3),
    actual_yield_kg         DECIMAL(10, 3),
    plucking_round_number   SMALLINT    CHECK (plucking_round_number > 0),

    status                  VARCHAR(20) NOT NULL DEFAULT 'scheduled'
                                CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled')),
    notes                   TEXT,
    created_at              TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP   NOT NULL DEFAULT NOW(),

    UNIQUE (block_id, assignment_date)
);

COMMENT ON COLUMN block_assignment.is_manual_override IS 'TRUE when manager changed the rotation-generated assignment';
COMMENT ON COLUMN block_assignment.original_group_id  IS 'Group the rotation would have assigned; populated when is_manual_override = TRUE';

-- ---------------------------------------------------------------------------
-- 8. EMPLOYEE DAY ASSIGNMENT
--    Individual-level overrides on top of a block_assignment.
--    'group'         → member was present through normal group membership
--    'manual_add'    → manager explicitly added this employee (e.g., extra support)
--    'manual_remove' → manager explicitly removed this employee (e.g., leave)
--    Absence/leave tracking uses manual_remove with a reason.
-- ---------------------------------------------------------------------------

CREATE TABLE employee_day_assignment (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    block_assignment_id UUID        NOT NULL REFERENCES block_assignment(id) ON DELETE CASCADE,
    employee_id         UUID        NOT NULL REFERENCES employee(id)         ON DELETE CASCADE,
    assignment_type     VARCHAR(20) NOT NULL DEFAULT 'group'
                            CHECK (assignment_type IN ('group', 'manual_add', 'manual_remove')),
    kg_collected        DECIMAL(8, 3),
    added_by            UUID        REFERENCES "user"(id) ON DELETE SET NULL,
    reason              TEXT,
    created_at          TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP   NOT NULL DEFAULT NOW(),

    UNIQUE (block_assignment_id, employee_id)
);

COMMENT ON TABLE employee_day_assignment IS 'Per-employee record for a single block assignment day. Supports individual overrides on top of group-level assignments.';

-- ---------------------------------------------------------------------------
-- 9. DROP OLD block_allocation TABLE (replaced by block_assignment)
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS block_allocation;

-- ---------------------------------------------------------------------------
-- 10. INDEXES
-- ---------------------------------------------------------------------------

-- employee
CREATE INDEX idx_employee_estate        ON employee (estate_id);
CREATE INDEX idx_employee_active        ON employee (estate_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_employee_type          ON employee (skill_type);

-- worker_group
CREATE INDEX idx_worker_group_estate    ON worker_group (estate_id);
CREATE INDEX idx_worker_group_active    ON worker_group (estate_id, is_active) WHERE is_active = TRUE;

-- worker_group_member
CREATE INDEX idx_wgm_group              ON worker_group_member (group_id);
CREATE INDEX idx_wgm_employee           ON worker_group_member (employee_id);

-- rotation
CREATE INDEX idx_rrb_cycle              ON rotation_round_block (rotation_cycle_id, round_number);
CREATE INDEX idx_rrb_block              ON rotation_round_block (block_id);

-- block_assignment
CREATE INDEX idx_bassign_plan           ON block_assignment (labour_plan_id);
CREATE INDEX idx_bassign_block_date     ON block_assignment (block_id, assignment_date DESC);
CREATE INDEX idx_bassign_group          ON block_assignment (worker_group_id);
CREATE INDEX idx_bassign_status         ON block_assignment (status);
CREATE INDEX idx_bassign_override       ON block_assignment (is_manual_override) WHERE is_manual_override = TRUE;

-- employee_day_assignment
CREATE INDEX idx_eda_assignment         ON employee_day_assignment (block_assignment_id);
CREATE INDEX idx_eda_employee           ON employee_day_assignment (employee_id);
CREATE INDEX idx_eda_type               ON employee_day_assignment (assignment_type);

-- ---------------------------------------------------------------------------
-- 11. HELPER VIEWS
-- ---------------------------------------------------------------------------

-- Current active group members per estate
CREATE VIEW v_active_group_members AS
SELECT
    e.name              AS estate,
    wg.group_code,
    wg.group_name,
    wg.capacity         AS group_capacity,
    COUNT(wgm.id)       AS current_headcount,
    wg.capacity - COUNT(wgm.id) AS vacancy,
    sup.full_name       AS supervisor
FROM worker_group wg
JOIN estate e           ON e.id  = wg.estate_id
LEFT JOIN worker_group_member wgm
                        ON wgm.group_id = wg.id AND wgm.is_active = TRUE
LEFT JOIN employee sup  ON sup.id = wg.supervisor_id
WHERE wg.is_active = TRUE
GROUP BY e.name, wg.group_code, wg.group_name, wg.capacity, sup.full_name
ORDER BY e.name, wg.group_code;

-- This week's block assignments with group headcount
CREATE VIEW v_current_week_assignments AS
SELECT
    e.name              AS estate,
    b.block_code,
    b.worker_capacity   AS block_capacity,
    wg.group_name,
    ba.assignment_date,
    ba.rotation_round,
    ba.is_manual_override,
    COUNT(wgm.id)       AS assigned_workers,
    ba.expected_yield_kg,
    ba.actual_yield_kg,
    ROUND(
        CASE WHEN ba.expected_yield_kg > 0
             THEN (ba.actual_yield_kg / ba.expected_yield_kg) * 100
             ELSE NULL
        END, 1
    )                   AS efficiency_pct,
    ba.status
FROM block_assignment ba
JOIN block b            ON b.id  = ba.block_id
JOIN estate e           ON e.id  = b.estate_id
LEFT JOIN worker_group wg
                        ON wg.id = ba.worker_group_id
LEFT JOIN worker_group_member wgm
                        ON wgm.group_id = wg.id AND wgm.is_active = TRUE
WHERE ba.assignment_date BETWEEN
        DATE_TRUNC('week', CURRENT_DATE) AND
        DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '6 days'
GROUP BY e.name, b.block_code, b.worker_capacity,
         wg.group_name, ba.assignment_date, ba.rotation_round,
         ba.is_manual_override, ba.expected_yield_kg, ba.actual_yield_kg, ba.status
ORDER BY ba.assignment_date, e.name, b.block_code;

-- Rotation progress per estate
CREATE VIEW v_rotation_progress AS
SELECT
    e.name                                  AS estate,
    rc.cycle_name,
    rc.current_round,
    rc.total_rounds,
    ROUND((rc.current_round::DECIMAL / rc.total_rounds) * 100, 1) AS cycle_completion_pct,
    rc.total_rounds - rc.current_round      AS rounds_remaining
FROM rotation_cycle rc
JOIN estate e ON e.id = rc.estate_id
WHERE rc.is_active = TRUE;
