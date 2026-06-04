-- =============================================================================
-- KVPL — Remaining Estates Labour Sample Data
-- Migration 005
-- Covers: Ramboda Heights (8 blocks), Hunasgiriya Estate (15 blocks),
--         Haputale Park (10 blocks)
-- Adds:   blocks, workers, groups, rotation cycles, labour plans for all 3
-- =============================================================================

-- =============================================================================
-- 1. MISSING BLOCKS
-- =============================================================================

-- Ramboda Heights — already has E1, E2, F1 → add 5 more to reach 8
INSERT INTO block (estate_id, block_code, soil_type, growth_stage, area_hectares, worker_capacity, plucking_interval_days)
SELECT e.id, b.block_code, b.soil_type, b.growth_stage, 2.2, 12, 7
FROM estate e,
(VALUES
    ('F2', 'Red Loam',  'Mature'),
    ('G1', 'Laterite',  'Mature'),
    ('G2', 'Red Loam',  'Young'),
    ('H1', 'Laterite',  'Mature'),
    ('H2', 'Red Loam',  'Mature')
) AS b(block_code, soil_type, growth_stage)
WHERE e.name = 'Ramboda Heights';

-- Update existing Ramboda blocks to set worker_capacity
UPDATE block SET worker_capacity = 12, plucking_interval_days = 7
WHERE estate_id = (SELECT id FROM estate WHERE name = 'Ramboda Heights')
  AND worker_capacity = 15;  -- default was 15, correct to 12

-- Hunasgiriya Estate — 15 blocks
INSERT INTO block (estate_id, block_code, soil_type, growth_stage, area_hectares, worker_capacity, plucking_interval_days)
SELECT e.id, b.block_code, b.soil_type, b.growth_stage, 2.0, 10, 8
FROM estate e,
(VALUES
    ('I1', 'Red Loam',    'Mature'),   ('I2', 'Laterite',  'Mature'),   ('I3', 'Red Loam',  'Young'),
    ('J1', 'Laterite',    'Mature'),   ('J2', 'Red Loam',  'Mature'),   ('J3', 'Laterite',  'Immature'),
    ('K1', 'Red Loam',    'Mature'),   ('K2', 'Laterite',  'Mature'),   ('K3', 'Red Loam',  'Young'),
    ('L1', 'Laterite',    'Mature'),   ('L2', 'Red Loam',  'Mature'),   ('L3', 'Laterite',  'Mature'),
    ('M1', 'Red Loam',    'Mature'),   ('M2', 'Laterite',  'Young'),    ('M3', 'Red Loam',  'Mature')
) AS b(block_code, soil_type, growth_stage)
WHERE e.name = 'Hunasgiriya Estate';

-- Haputale Park — 10 blocks
INSERT INTO block (estate_id, block_code, soil_type, growth_stage, area_hectares, worker_capacity, plucking_interval_days)
SELECT e.id, b.block_code, b.soil_type, b.growth_stage, 2.3, 12, 7
FROM estate e,
(VALUES
    ('N1', 'Laterite',  'Mature'),   ('N2', 'Red Loam',  'Mature'),   ('N3', 'Laterite',  'Young'),
    ('O1', 'Red Loam',  'Mature'),   ('O2', 'Laterite',  'Mature'),   ('O3', 'Red Loam',  'Mature'),
    ('P1', 'Laterite',  'Mature'),   ('P2', 'Red Loam',  'Young'),
    ('Q1', 'Laterite',  'Mature'),   ('Q2', 'Red Loam',  'Mature')
) AS b(block_code, soil_type, growth_stage)
WHERE e.name = 'Haputale Park';

-- =============================================================================
-- 2. MISSING SYSTEM USER — Haputale Park manager
-- =============================================================================

INSERT INTO "user" (estate_id, name, email, role, is_active)
SELECT e.id, 'Estate Manager - Haputale', 'manager.haputale@kvpl.com', 'estate_manager', TRUE
FROM estate e WHERE e.name = 'Haputale Park';

-- =============================================================================
-- 3. EMPLOYEES — RAMBODA HEIGHTS
--    8 groups × 12 workers = 96 total  (1 supervisor + 11 pluckers per group)
-- =============================================================================

-- Supervisors (8)
INSERT INTO employee (estate_id, employee_code, full_name, gender, hire_date, employment_type, skill_type, daily_wage_lkr)
SELECT e.id, sup.code, sup.name, sup.gender, sup.hire_date::DATE, 'permanent', 'supervisor', 950.00
FROM estate e,
(VALUES
    ('RMB-SUP-01', 'Gayan Kumara',           'M', '2017-04-12'),
    ('RMB-SUP-02', 'Dilsha Seneviratne',      'F', '2018-09-03'),
    ('RMB-SUP-03', 'Nilantha Jayasekara',     'M', '2016-07-20'),
    ('RMB-SUP-04', 'Amantha Wickramasinghe',  'M', '2019-02-14'),
    ('RMB-SUP-05', 'Pushpa Mendis',           'F', '2017-11-30'),
    ('RMB-SUP-06', 'Roshan Bandara',          'M', '2020-05-18'),
    ('RMB-SUP-07', 'Damayanthi Fernando',     'F', '2015-10-07'),
    ('RMB-SUP-08', 'Chaminda Rathnayake',     'M', '2018-03-25')
) AS sup(code, name, gender, hire_date)
WHERE e.name = 'Ramboda Heights';

-- Pluckers (88) using generate_series — groups of 11
INSERT INTO employee (estate_id, employee_code, full_name, gender, hire_date, employment_type, skill_type, daily_wage_lkr)
SELECT
    e.id,
    'RMB-PLK-' || LPAD(gs::TEXT, 3, '0'),
    'Worker RMB-' || LPAD(gs::TEXT, 3, '0'),
    CASE WHEN gs % 4 = 0 THEN 'M' ELSE 'F' END,
    (DATE '2023-01-01' - ((gs * 47 + 120) % 1460) * INTERVAL '1 day')::DATE,
    CASE WHEN gs % 9 = 0 THEN 'casual' ELSE 'permanent' END,
    'plucker',
    700.00
FROM estate e, generate_series(1, 88) AS gs
WHERE e.name = 'Ramboda Heights';

-- =============================================================================
-- 4. EMPLOYEES — HUNASGIRIYA ESTATE
--    15 groups × 10 workers = 150 total  (1 supervisor + 9 pluckers per group)
-- =============================================================================

-- Supervisors (15)
INSERT INTO employee (estate_id, employee_code, full_name, gender, hire_date, employment_type, skill_type, daily_wage_lkr)
SELECT e.id, sup.code, sup.name, sup.gender, sup.hire_date::DATE, 'permanent', 'supervisor', 950.00
FROM estate e,
(VALUES
    ('HUN-SUP-01', 'Thilak Perera',           'M', '2016-02-08'),
    ('HUN-SUP-02', 'Sewwandi Jayawardena',     'F', '2017-07-14'),
    ('HUN-SUP-03', 'Lasith Gunaratne',         'M', '2018-01-22'),
    ('HUN-SUP-04', 'Raveena Dissanayake',      'F', '2015-09-05'),
    ('HUN-SUP-05', 'Pradeep Weerasinghe',      'M', '2019-06-30'),
    ('HUN-SUP-06', 'Chathu Samaraweera',       'F', '2017-03-17'),
    ('HUN-SUP-07', 'Dimuthu Kodikara',         'M', '2020-08-11'),
    ('HUN-SUP-08', 'Indrani Ranawaka',         'F', '2016-12-01'),
    ('HUN-SUP-09', 'Sanjeewa Hettiarachchi',   'M', '2018-05-28'),
    ('HUN-SUP-10', 'Niroshi Abeywickrama',     'F', '2019-10-15'),
    ('HUN-SUP-11', 'Ruwan Siriwardhana',       'M', '2017-04-04'),
    ('HUN-SUP-12', 'Malika Wickrama',          'F', '2021-01-20'),
    ('HUN-SUP-13', 'Danushka Rajapaksha',      'M', '2016-06-09'),
    ('HUN-SUP-14', 'Udara Karunarathna',       'F', '2020-11-03'),
    ('HUN-SUP-15', 'Asanka Liyanage',          'M', '2015-04-26')
) AS sup(code, name, gender, hire_date)
WHERE e.name = 'Hunasgiriya Estate';

-- Pluckers (135 = 15 groups × 9 pluckers)
INSERT INTO employee (estate_id, employee_code, full_name, gender, hire_date, employment_type, skill_type, daily_wage_lkr)
SELECT
    e.id,
    'HUN-PLK-' || LPAD(gs::TEXT, 3, '0'),
    'Worker HUN-' || LPAD(gs::TEXT, 3, '0'),
    CASE WHEN gs % 5 = 0 THEN 'M' ELSE 'F' END,
    (DATE '2023-06-01' - ((gs * 53 + 90) % 1825) * INTERVAL '1 day')::DATE,
    CASE WHEN gs % 11 = 0 THEN 'casual' ELSE 'permanent' END,
    'plucker',
    700.00
FROM estate e, generate_series(1, 135) AS gs
WHERE e.name = 'Hunasgiriya Estate';

-- =============================================================================
-- 5. EMPLOYEES — HAPUTALE PARK
--    10 groups × 12 workers = 120 total  (1 supervisor + 11 pluckers per group)
-- =============================================================================

-- Supervisors (10)
INSERT INTO employee (estate_id, employee_code, full_name, gender, hire_date, employment_type, skill_type, daily_wage_lkr)
SELECT e.id, sup.code, sup.name, sup.gender, sup.hire_date::DATE, 'permanent', 'supervisor', 950.00
FROM estate e,
(VALUES
    ('HAP-SUP-01', 'Sulochana Jayasinghe',    'F', '2016-05-12'),
    ('HAP-SUP-02', 'Nuwan Pathirana',         'M', '2018-02-07'),
    ('HAP-SUP-03', 'Dilhani Ratnasiri',       'F', '2017-08-19'),
    ('HAP-SUP-04', 'Kusal Wijesekara',        'M', '2019-11-04'),
    ('HAP-SUP-05', 'Nayana Senerath',         'F', '2015-03-28'),
    ('HAP-SUP-06', 'Tharaka Koswatte',        'M', '2020-07-15'),
    ('HAP-SUP-07', 'Rashmi Athukorala',       'F', '2017-01-31'),
    ('HAP-SUP-08', 'Vimukthi Abeysekara',     'M', '2018-09-22'),
    ('HAP-SUP-09', 'Iresha Ranasinghe',       'F', '2021-04-06'),
    ('HAP-SUP-10', 'Chamara Edirisinghe',     'M', '2016-10-14')
) AS sup(code, name, gender, hire_date)
WHERE e.name = 'Haputale Park';

-- Pluckers (110 = 10 groups × 11 pluckers)
INSERT INTO employee (estate_id, employee_code, full_name, gender, hire_date, employment_type, skill_type, daily_wage_lkr)
SELECT
    e.id,
    'HAP-PLK-' || LPAD(gs::TEXT, 3, '0'),
    'Worker HAP-' || LPAD(gs::TEXT, 3, '0'),
    CASE WHEN gs % 4 = 0 THEN 'M' ELSE 'F' END,
    (DATE '2022-09-01' - ((gs * 61 + 150) % 1460) * INTERVAL '1 day')::DATE,
    CASE WHEN gs % 8 = 0 THEN 'seasonal' WHEN gs % 13 = 0 THEN 'casual' ELSE 'permanent' END,
    'plucker',
    700.00
FROM estate e, generate_series(1, 110) AS gs
WHERE e.name = 'Haputale Park';

-- =============================================================================
-- 6. WORKER GROUPS
-- =============================================================================

-- Ramboda Heights — 8 groups
INSERT INTO worker_group (estate_id, group_code, group_name, supervisor_id, capacity, is_active)
SELECT e.id, g.group_code, g.group_name, sup.id, 12, TRUE
FROM estate e
CROSS JOIN (VALUES
    ('G-RMB-01','Ramboda Group 1','RMB-SUP-01'),
    ('G-RMB-02','Ramboda Group 2','RMB-SUP-02'),
    ('G-RMB-03','Ramboda Group 3','RMB-SUP-03'),
    ('G-RMB-04','Ramboda Group 4','RMB-SUP-04'),
    ('G-RMB-05','Ramboda Group 5','RMB-SUP-05'),
    ('G-RMB-06','Ramboda Group 6','RMB-SUP-06'),
    ('G-RMB-07','Ramboda Group 7','RMB-SUP-07'),
    ('G-RMB-08','Ramboda Group 8','RMB-SUP-08')
) AS g(group_code, group_name, sup_code)
JOIN employee sup ON sup.employee_code = g.sup_code AND sup.estate_id = e.id
WHERE e.name = 'Ramboda Heights';

-- Hunasgiriya Estate — 15 groups
INSERT INTO worker_group (estate_id, group_code, group_name, supervisor_id, capacity, is_active)
SELECT e.id, g.group_code, g.group_name, sup.id, 10, TRUE
FROM estate e
CROSS JOIN (VALUES
    ('G-HUN-01', 'Hunasgiriya Group 1',  'HUN-SUP-01'),
    ('G-HUN-02', 'Hunasgiriya Group 2',  'HUN-SUP-02'),
    ('G-HUN-03', 'Hunasgiriya Group 3',  'HUN-SUP-03'),
    ('G-HUN-04', 'Hunasgiriya Group 4',  'HUN-SUP-04'),
    ('G-HUN-05', 'Hunasgiriya Group 5',  'HUN-SUP-05'),
    ('G-HUN-06', 'Hunasgiriya Group 6',  'HUN-SUP-06'),
    ('G-HUN-07', 'Hunasgiriya Group 7',  'HUN-SUP-07'),
    ('G-HUN-08', 'Hunasgiriya Group 8',  'HUN-SUP-08'),
    ('G-HUN-09', 'Hunasgiriya Group 9',  'HUN-SUP-09'),
    ('G-HUN-10', 'Hunasgiriya Group 10', 'HUN-SUP-10'),
    ('G-HUN-11', 'Hunasgiriya Group 11', 'HUN-SUP-11'),
    ('G-HUN-12', 'Hunasgiriya Group 12', 'HUN-SUP-12'),
    ('G-HUN-13', 'Hunasgiriya Group 13', 'HUN-SUP-13'),
    ('G-HUN-14', 'Hunasgiriya Group 14', 'HUN-SUP-14'),
    ('G-HUN-15', 'Hunasgiriya Group 15', 'HUN-SUP-15')
) AS g(group_code, group_name, sup_code)
JOIN employee sup ON sup.employee_code = g.sup_code AND sup.estate_id = e.id
WHERE e.name = 'Hunasgiriya Estate';

-- Haputale Park — 10 groups
INSERT INTO worker_group (estate_id, group_code, group_name, supervisor_id, capacity, is_active)
SELECT e.id, g.group_code, g.group_name, sup.id, 12, TRUE
FROM estate e
CROSS JOIN (VALUES
    ('G-HAP-01', 'Haputale Group 1',  'HAP-SUP-01'),
    ('G-HAP-02', 'Haputale Group 2',  'HAP-SUP-02'),
    ('G-HAP-03', 'Haputale Group 3',  'HAP-SUP-03'),
    ('G-HAP-04', 'Haputale Group 4',  'HAP-SUP-04'),
    ('G-HAP-05', 'Haputale Group 5',  'HAP-SUP-05'),
    ('G-HAP-06', 'Haputale Group 6',  'HAP-SUP-06'),
    ('G-HAP-07', 'Haputale Group 7',  'HAP-SUP-07'),
    ('G-HAP-08', 'Haputale Group 8',  'HAP-SUP-08'),
    ('G-HAP-09', 'Haputale Group 9',  'HAP-SUP-09'),
    ('G-HAP-10', 'Haputale Group 10', 'HAP-SUP-10')
) AS g(group_code, group_name, sup_code)
JOIN employee sup ON sup.employee_code = g.sup_code AND sup.estate_id = e.id
WHERE e.name = 'Haputale Park';

-- =============================================================================
-- 7. WORKER GROUP MEMBERS
-- =============================================================================

-- ── RAMBODA: assign supervisors ──
INSERT INTO worker_group_member (group_id, employee_id, joined_date, is_active)
SELECT wg.id, emp.id, emp.hire_date, TRUE
FROM worker_group wg
JOIN estate e ON e.id = wg.estate_id AND e.name = 'Ramboda Heights'
JOIN (VALUES
    ('G-RMB-01','RMB-SUP-01'),('G-RMB-02','RMB-SUP-02'),
    ('G-RMB-03','RMB-SUP-03'),('G-RMB-04','RMB-SUP-04'),
    ('G-RMB-05','RMB-SUP-05'),('G-RMB-06','RMB-SUP-06'),
    ('G-RMB-07','RMB-SUP-07'),('G-RMB-08','RMB-SUP-08')
) AS m(gc, ec) ON m.gc = wg.group_code
JOIN employee emp ON emp.employee_code = m.ec AND emp.estate_id = e.id;

-- ── RAMBODA: assign pluckers — 11 per group ──
-- Use row position modulo to evenly distribute 88 pluckers across 8 groups
INSERT INTO worker_group_member (group_id, employee_id, joined_date, is_active)
WITH
    ordered_groups AS (
        SELECT id, ROW_NUMBER() OVER (ORDER BY group_code) - 1 AS gidx  -- 0-based
        FROM worker_group
        WHERE estate_id = (SELECT id FROM estate WHERE name = 'Ramboda Heights')
    ),
    ordered_pluckers AS (
        SELECT id, hire_date, ROW_NUMBER() OVER (ORDER BY employee_code) - 1 AS pidx  -- 0-based
        FROM employee
        WHERE estate_id = (SELECT id FROM estate WHERE name = 'Ramboda Heights')
          AND skill_type = 'plucker'
    )
SELECT og.id, op.id, op.hire_date, TRUE
FROM ordered_pluckers op
JOIN ordered_groups og ON og.gidx = (op.pidx / 11)  -- integer division: 0-10→g0, 11-21→g1, …
WHERE op.pidx < 88;  -- 8 groups × 11 pluckers

-- ── HUNASGIRIYA: assign supervisors ──
INSERT INTO worker_group_member (group_id, employee_id, joined_date, is_active)
SELECT wg.id, emp.id, emp.hire_date, TRUE
FROM worker_group wg
JOIN estate e ON e.id = wg.estate_id AND e.name = 'Hunasgiriya Estate'
JOIN (VALUES
    ('G-HUN-01','HUN-SUP-01'),('G-HUN-02','HUN-SUP-02'),('G-HUN-03','HUN-SUP-03'),
    ('G-HUN-04','HUN-SUP-04'),('G-HUN-05','HUN-SUP-05'),('G-HUN-06','HUN-SUP-06'),
    ('G-HUN-07','HUN-SUP-07'),('G-HUN-08','HUN-SUP-08'),('G-HUN-09','HUN-SUP-09'),
    ('G-HUN-10','HUN-SUP-10'),('G-HUN-11','HUN-SUP-11'),('G-HUN-12','HUN-SUP-12'),
    ('G-HUN-13','HUN-SUP-13'),('G-HUN-14','HUN-SUP-14'),('G-HUN-15','HUN-SUP-15')
) AS m(gc, ec) ON m.gc = wg.group_code
JOIN employee emp ON emp.employee_code = m.ec AND emp.estate_id = e.id;

-- ── HUNASGIRIYA: assign pluckers — 9 per group (135 pluckers ÷ 15 groups) ──
INSERT INTO worker_group_member (group_id, employee_id, joined_date, is_active)
WITH
    ordered_groups AS (
        SELECT id, ROW_NUMBER() OVER (ORDER BY group_code) - 1 AS gidx
        FROM worker_group
        WHERE estate_id = (SELECT id FROM estate WHERE name = 'Hunasgiriya Estate')
    ),
    ordered_pluckers AS (
        SELECT id, hire_date, ROW_NUMBER() OVER (ORDER BY employee_code) - 1 AS pidx
        FROM employee
        WHERE estate_id = (SELECT id FROM estate WHERE name = 'Hunasgiriya Estate')
          AND skill_type = 'plucker'
    )
SELECT og.id, op.id, op.hire_date, TRUE
FROM ordered_pluckers op
JOIN ordered_groups og ON og.gidx = (op.pidx / 9)
WHERE op.pidx < 135;

-- ── HAPUTALE: assign supervisors ──
INSERT INTO worker_group_member (group_id, employee_id, joined_date, is_active)
SELECT wg.id, emp.id, emp.hire_date, TRUE
FROM worker_group wg
JOIN estate e ON e.id = wg.estate_id AND e.name = 'Haputale Park'
JOIN (VALUES
    ('G-HAP-01','HAP-SUP-01'),('G-HAP-02','HAP-SUP-02'),('G-HAP-03','HAP-SUP-03'),
    ('G-HAP-04','HAP-SUP-04'),('G-HAP-05','HAP-SUP-05'),('G-HAP-06','HAP-SUP-06'),
    ('G-HAP-07','HAP-SUP-07'),('G-HAP-08','HAP-SUP-08'),('G-HAP-09','HAP-SUP-09'),
    ('G-HAP-10','HAP-SUP-10')
) AS m(gc, ec) ON m.gc = wg.group_code
JOIN employee emp ON emp.employee_code = m.ec AND emp.estate_id = e.id;

-- ── HAPUTALE: assign pluckers — 11 per group ──
INSERT INTO worker_group_member (group_id, employee_id, joined_date, is_active)
WITH
    ordered_groups AS (
        SELECT id, ROW_NUMBER() OVER (ORDER BY group_code) - 1 AS gidx
        FROM worker_group
        WHERE estate_id = (SELECT id FROM estate WHERE name = 'Haputale Park')
    ),
    ordered_pluckers AS (
        SELECT id, hire_date, ROW_NUMBER() OVER (ORDER BY employee_code) - 1 AS pidx
        FROM employee
        WHERE estate_id = (SELECT id FROM estate WHERE name = 'Haputale Park')
          AND skill_type = 'plucker'
    )
SELECT og.id, op.id, op.hire_date, TRUE
FROM ordered_pluckers op
JOIN ordered_groups og ON og.gidx = (op.pidx / 11)
WHERE op.pidx < 110;

-- =============================================================================
-- 8. ROTATION CYCLES
--    current_round set mid-cycle to simulate an ongoing season
-- =============================================================================

INSERT INTO rotation_cycle (estate_id, cycle_name, total_rounds, current_round, is_active, created_by)
SELECT e.id, r.cycle_name, r.total_rounds, r.current_round, TRUE, u.id
FROM (VALUES
    ('Ramboda Heights',    'Ramboda Standard Rotation 2026',    8,  5),
    ('Hunasgiriya Estate', 'Hunasgiriya Standard Rotation 2026',15, 9),
    ('Haputale Park',      'Haputale Standard Rotation 2026',   10, 4)
) AS r(estate_name, cycle_name, total_rounds, current_round)
JOIN estate e ON e.name = r.estate_name
JOIN "user" u ON u.estate_id = e.id AND u.role = 'estate_manager'
LIMIT 3;

-- =============================================================================
-- 9. ROTATION ROUND BLOCK MATRIX (cyclic shift formula)
--
--    For each estate with N blocks and N groups:
--      group_position_for_round_r_block_p = ((p - r + N) mod N) + 1
--
--    This guarantees every group visits every block exactly once per cycle.
-- =============================================================================

-- ── Ramboda Heights (8 blocks × 8 groups × 8 rounds = 64 assignments) ──
INSERT INTO rotation_round_block (rotation_cycle_id, round_number, block_id, worker_group_id)
WITH
    cycle  AS (SELECT id, total_rounds FROM rotation_cycle WHERE cycle_name = 'Ramboda Standard Rotation 2026'),
    blocks AS (
        SELECT b.id, ROW_NUMBER() OVER (ORDER BY b.block_code) AS pos
        FROM block b JOIN estate e ON e.id = b.estate_id WHERE e.name = 'Ramboda Heights'
    ),
    grps   AS (
        SELECT wg.id, ROW_NUMBER() OVER (ORDER BY wg.group_code) AS pos
        FROM worker_group wg JOIN estate e ON e.id = wg.estate_id WHERE e.name = 'Ramboda Heights'
    ),
    rounds AS (SELECT generate_series(1, (SELECT total_rounds FROM cycle)) AS rn),
    matrix AS (
        SELECT r.rn, b.id AS block_id,
               ((b.pos - r.rn + (SELECT total_rounds FROM cycle)) % (SELECT total_rounds FROM cycle)) + 1 AS gpos
        FROM rounds r, blocks b
    )
SELECT (SELECT id FROM cycle), m.rn, m.block_id, g.id
FROM matrix m JOIN grps g ON g.pos = m.gpos;

-- ── Hunasgiriya Estate (15 blocks × 15 groups × 15 rounds = 225 assignments) ──
INSERT INTO rotation_round_block (rotation_cycle_id, round_number, block_id, worker_group_id)
WITH
    cycle  AS (SELECT id, total_rounds FROM rotation_cycle WHERE cycle_name = 'Hunasgiriya Standard Rotation 2026'),
    blocks AS (
        SELECT b.id, ROW_NUMBER() OVER (ORDER BY b.block_code) AS pos
        FROM block b JOIN estate e ON e.id = b.estate_id WHERE e.name = 'Hunasgiriya Estate'
    ),
    grps   AS (
        SELECT wg.id, ROW_NUMBER() OVER (ORDER BY wg.group_code) AS pos
        FROM worker_group wg JOIN estate e ON e.id = wg.estate_id WHERE e.name = 'Hunasgiriya Estate'
    ),
    rounds AS (SELECT generate_series(1, (SELECT total_rounds FROM cycle)) AS rn),
    matrix AS (
        SELECT r.rn, b.id AS block_id,
               ((b.pos - r.rn + (SELECT total_rounds FROM cycle)) % (SELECT total_rounds FROM cycle)) + 1 AS gpos
        FROM rounds r, blocks b
    )
SELECT (SELECT id FROM cycle), m.rn, m.block_id, g.id
FROM matrix m JOIN grps g ON g.pos = m.gpos;

-- ── Haputale Park (10 blocks × 10 groups × 10 rounds = 100 assignments) ──
INSERT INTO rotation_round_block (rotation_cycle_id, round_number, block_id, worker_group_id)
WITH
    cycle  AS (SELECT id, total_rounds FROM rotation_cycle WHERE cycle_name = 'Haputale Standard Rotation 2026'),
    blocks AS (
        SELECT b.id, ROW_NUMBER() OVER (ORDER BY b.block_code) AS pos
        FROM block b JOIN estate e ON e.id = b.estate_id WHERE e.name = 'Haputale Park'
    ),
    grps   AS (
        SELECT wg.id, ROW_NUMBER() OVER (ORDER BY wg.group_code) AS pos
        FROM worker_group wg JOIN estate e ON e.id = wg.estate_id WHERE e.name = 'Haputale Park'
    ),
    rounds AS (SELECT generate_series(1, (SELECT total_rounds FROM cycle)) AS rn),
    matrix AS (
        SELECT r.rn, b.id AS block_id,
               ((b.pos - r.rn + (SELECT total_rounds FROM cycle)) % (SELECT total_rounds FROM cycle)) + 1 AS gpos
        FROM rounds r, blocks b
    )
SELECT (SELECT id FROM cycle), m.rn, m.block_id, g.id
FROM matrix m JOIN grps g ON g.pos = m.gpos;

-- =============================================================================
-- 10. LABOUR PLANS — current week for all 3 remaining estates
-- =============================================================================

INSERT INTO labour_plan (estate_id, created_by, week_start, total_workers, target_kg, status, notes)
SELECT e.id, u.id,
       DATE_TRUNC('week', CURRENT_DATE)::DATE,
       p.total_workers, p.target_kg, 'published', p.notes
FROM (VALUES
    ('Ramboda Heights',    96,   46080, 'Auto-generated from rotation cycle — Round 5'),
    ('Hunasgiriya Estate', 150,  60000, 'Auto-generated from rotation cycle — Round 9'),
    ('Haputale Park',      120,  57600, 'Auto-generated from rotation cycle — Round 4')
) AS p(estate_name, total_workers, target_kg, notes)
JOIN estate e ON e.name = p.estate_name
JOIN "user" u ON u.estate_id = e.id AND u.role = 'estate_manager'
ON CONFLICT (estate_id, week_start) DO NOTHING;

-- =============================================================================
-- 11. BLOCK ASSIGNMENTS — current week from active rotation round
--     One assignment per block per estate, using the cycle's current_round
-- =============================================================================

INSERT INTO block_assignment (
    labour_plan_id, block_id, worker_group_id,
    assignment_date, rotation_cycle_id, rotation_round,
    expected_yield_kg, plucking_round_number, status
)
WITH
    current_plans AS (
        SELECT lp.id AS plan_id, lp.estate_id, e.name AS estate_name
        FROM labour_plan lp
        JOIN estate e ON e.id = lp.estate_id
        WHERE lp.week_start = DATE_TRUNC('week', CURRENT_DATE)::DATE
          AND e.name IN ('Ramboda Heights', 'Hunasgiriya Estate', 'Haputale Park')
    ),
    active_cycles AS (
        SELECT rc.id AS cycle_id, rc.estate_id, rc.current_round
        FROM rotation_cycle rc WHERE rc.is_active = TRUE
    ),
    round_assignments AS (
        SELECT
            cp.plan_id,
            cp.estate_id,
            ac.cycle_id,
            ac.current_round,
            rrb.block_id,
            rrb.worker_group_id,
            b.worker_capacity
        FROM current_plans cp
        JOIN active_cycles ac ON ac.estate_id = cp.estate_id
        JOIN rotation_round_block rrb
             ON rrb.rotation_cycle_id = ac.cycle_id
             AND rrb.round_number = ac.current_round
        JOIN block b ON b.id = rrb.block_id
    )
SELECT
    ra.plan_id,
    ra.block_id,
    ra.worker_group_id,
    DATE_TRUNC('week', CURRENT_DATE)::DATE,
    ra.cycle_id,
    ra.current_round,
    ra.worker_capacity * 600.0,   -- expected yield: capacity × 600 g/worker/day
    CEIL(EXTRACT(DOY FROM CURRENT_DATE) / 7.0)::SMALLINT,  -- plucking round = week-of-year
    'scheduled'
FROM round_assignments ra
ON CONFLICT (block_id, assignment_date) DO NOTHING;

-- =============================================================================
-- 12. HISTORICAL BLOCK ASSIGNMENTS — past 4 weeks for productivity queries
--     Adds realistic completed assignments so reports have data to show
-- =============================================================================

INSERT INTO block_assignment (
    labour_plan_id, block_id, worker_group_id,
    assignment_date, rotation_cycle_id, rotation_round,
    expected_yield_kg, actual_yield_kg, plucking_round_number, status
)
WITH
    weeks AS (SELECT generate_series(1, 4) AS w),
    week_dates AS (
        SELECT w, (DATE_TRUNC('week', CURRENT_DATE) - (w * 7) * INTERVAL '1 day')::DATE AS wdate
        FROM weeks
    ),
    past_rounds AS (
        SELECT
            rc.id AS cycle_id, rc.estate_id, rc.total_rounds,
            -- walk back the current_round for each past week
            ((rc.current_round - w.w - 1 + rc.total_rounds * 10) % rc.total_rounds) + 1 AS round_num,
            wd.wdate
        FROM rotation_cycle rc, weeks w
        JOIN week_dates wd ON wd.w = w.w
        WHERE rc.is_active = TRUE
          AND rc.estate_id IN (
                SELECT id FROM estate
                WHERE name IN ('Ramboda Heights', 'Hunasgiriya Estate', 'Haputale Park')
          )
    ),
    past_assignments AS (
        SELECT
            NULL::UUID AS plan_id,
            pr.cycle_id, pr.estate_id, pr.round_num, pr.wdate,
            rrb.block_id, rrb.worker_group_id, b.worker_capacity
        FROM past_rounds pr
        JOIN rotation_round_block rrb
             ON rrb.rotation_cycle_id = pr.cycle_id
             AND rrb.round_number = pr.round_num
        JOIN block b ON b.id = rrb.block_id
    )
SELECT
    pa.plan_id,
    pa.block_id,
    pa.worker_group_id,
    pa.wdate,
    pa.cycle_id,
    pa.round_num,
    pa.worker_capacity * 600.0   AS expected_yield_kg,
    -- actual yield: 90–105% of expected, deterministic from block+date hash
    pa.worker_capacity * 600.0 *
        (0.90 + 0.15 * ((EXTRACT(DOY FROM pa.wdate)::INT + pa.round_num) % 10) / 10.0) AS actual_yield_kg,
    CEIL(EXTRACT(DOY FROM pa.wdate) / 7.0)::SMALLINT,
    'completed'
FROM past_assignments pa
ON CONFLICT (block_id, assignment_date) DO NOTHING;
