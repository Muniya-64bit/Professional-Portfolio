-- =============================================================================
-- KVPL — Labour Planner Sample Data
-- Migration 004
-- Seeds: block worker_capacity, employees, worker_groups, rotation_cycle,
--        block_assignments for the current week
-- Scope: Kundasale Estate (6 blocks, 6 groups, 6-round rotation)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. SET worker_capacity ON EXISTING BLOCKS
--    All blocks in an estate are the same physical size, so same capacity.
--    Kundasale standard = 15 workers per block per plucking day.
--    plucking_interval_days = 7 (weekly rotation).
-- ---------------------------------------------------------------------------

UPDATE block
SET
    worker_capacity        = 15,
    plucking_interval_days = 7
WHERE estate_id = (SELECT id FROM estate WHERE name = 'Kundasale Estate');

-- ---------------------------------------------------------------------------
-- 2. EMPLOYEES
--    6 blocks × 1 supervisor + 14 pluckers = 90 employees for Kundasale.
--    employee_code pattern: KUN-SUP-01 (supervisors), KUN-PLK-001 (pluckers)
-- ---------------------------------------------------------------------------

-- Supervisors (6, one per group)
INSERT INTO employee (estate_id, employee_code, full_name, gender, hire_date, employment_type, skill_type, daily_wage_lkr)
SELECT e.id, emp.code, emp.name, emp.gender, emp.hire_date::DATE, 'permanent', 'supervisor', emp.wage
FROM estate e,
(VALUES
    ('KUN-SUP-01', 'Sunil Perera',        'M', '2018-03-15', 950.00),
    ('KUN-SUP-02', 'Kamala Fernando',     'F', '2017-06-01', 950.00),
    ('KUN-SUP-03', 'Nimal Jayawardena',   'M', '2019-01-10', 950.00),
    ('KUN-SUP-04', 'Priya Wickramasinghe','F', '2016-11-20', 950.00),
    ('KUN-SUP-05', 'Ruwan Bandara',       'M', '2020-04-05', 950.00),
    ('KUN-SUP-06', 'Lalitha Dissanayake', 'F', '2015-08-30', 950.00)
) AS emp(code, name, gender, hire_date, wage)
WHERE e.name = 'Kundasale Estate';

-- Pluckers (14 per group × 6 groups = 84 employees)
-- Group 1 pluckers
INSERT INTO employee (estate_id, employee_code, full_name, gender, hire_date, employment_type, skill_type, daily_wage_lkr)
SELECT e.id, emp.code, emp.name, emp.gender, emp.hire_date::DATE, 'permanent', 'plucker', 700.00
FROM estate e,
(VALUES
    ('KUN-PLK-001','Amara Silva',      'F','2021-01-05'),('KUN-PLK-002','Thilini Rathnayake','F','2020-06-15'),
    ('KUN-PLK-003','Kumari Senanayake','F','2022-03-10'),('KUN-PLK-004','Nadee Jayasena',   'F','2021-09-20'),
    ('KUN-PLK-005','Chamari Gunasekara','F','2020-11-01'),('KUN-PLK-006','Dilani Mendis',   'F','2023-01-15'),
    ('KUN-PLK-007','Seetha Weerasinghe','F','2019-07-22'),('KUN-PLK-008','Rupa Dharmasiri', 'F','2022-08-30'),
    ('KUN-PLK-009','Piyumi Liyanage',  'F','2021-04-12'),('KUN-PLK-010','Nadeeka Siriwardana','F','2020-02-28'),
    ('KUN-PLK-011','Hasini Ratnasiri', 'F','2023-05-18'),('KUN-PLK-012','Lakmini Tennakoon','F','2022-10-07'),
    ('KUN-PLK-013','Ayesha Rajapaksa', 'F','2021-12-01'),('KUN-PLK-014','Chathu Hewage',   'F','2019-04-16')
) AS emp(code, name, gender, hire_date)
WHERE e.name = 'Kundasale Estate';

-- Group 2 pluckers
INSERT INTO employee (estate_id, employee_code, full_name, gender, hire_date, employment_type, skill_type, daily_wage_lkr)
SELECT e.id, emp.code, emp.name, emp.gender, emp.hire_date::DATE, 'permanent', 'plucker', 700.00
FROM estate e,
(VALUES
    ('KUN-PLK-015','Sanduni Karunaratne','F','2021-02-10'),('KUN-PLK-016','Nilmini Wimalasiri','F','2020-07-25'),
    ('KUN-PLK-017','Dilrukshi Pathirana','F','2022-04-05'),('KUN-PLK-018','Sumedha Gunaratne', 'F','2021-10-18'),
    ('KUN-PLK-019','Malsha Marasinghe',  'F','2020-12-08'),('KUN-PLK-020','Renuka Athukorala', 'F','2023-02-22'),
    ('KUN-PLK-021','Samadhi Jayakody',   'F','2019-08-14'),('KUN-PLK-022','Pramila Koswatte',  'F','2022-09-03'),
    ('KUN-PLK-023','Ishara Samarakoon',  'F','2021-05-27'),('KUN-PLK-024','Nipuni Kodikara',   'F','2020-03-16'),
    ('KUN-PLK-025','Dulani Seneviratne', 'F','2023-06-11'),('KUN-PLK-026','Himasha Wickrama',  'F','2022-11-29'),
    ('KUN-PLK-027','Anusha Hettiarachchi','F','2021-01-20'),('KUN-PLK-028','Thushara Dissanayake','F','2019-05-08')
) AS emp(code, name, gender, hire_date)
WHERE e.name = 'Kundasale Estate';

-- Group 3 pluckers
INSERT INTO employee (estate_id, employee_code, full_name, gender, hire_date, employment_type, skill_type, daily_wage_lkr)
SELECT e.id, emp.code, emp.name, emp.gender, emp.hire_date::DATE, 'permanent', 'plucker', 700.00
FROM estate e,
(VALUES
    ('KUN-PLK-029','Kavindi Ratnaweera', 'F','2021-03-14'),('KUN-PLK-030','Dilhani Bandara',    'F','2020-08-22'),
    ('KUN-PLK-031','Chathuri Perera',    'F','2022-05-09'),('KUN-PLK-032','Madhavi Fernando',   'F','2021-11-03'),
    ('KUN-PLK-033','Sachini Rajapaksha', 'F','2020-01-17'),('KUN-PLK-034','Yolanda Weeraratne', 'F','2023-03-28'),
    ('KUN-PLK-035','Inoka Jayawardena',  'F','2019-09-06'),('KUN-PLK-036','Nirosha Dissanayake','F','2022-10-21'),
    ('KUN-PLK-037','Manori Kumari',      'F','2021-06-15'),('KUN-PLK-038','Pavithra Siriwardhana','F','2020-04-30'),
    ('KUN-PLK-039','Champa Karunasena',  'F','2023-07-12'),('KUN-PLK-040','Roshini Abeysekara', 'F','2022-12-04'),
    ('KUN-PLK-041','Nethra Wickramanayake','F','2021-02-08'),('KUN-PLK-042','Vindya Samarasekara','F','2019-06-19')
) AS emp(code, name, gender, hire_date)
WHERE e.name = 'Kundasale Estate';

-- Group 4 pluckers
INSERT INTO employee (estate_id, employee_code, full_name, gender, hire_date, employment_type, skill_type, daily_wage_lkr)
SELECT e.id, emp.code, emp.name, emp.gender, emp.hire_date::DATE, 'permanent', 'plucker', 700.00
FROM estate e,
(VALUES
    ('KUN-PLK-043','Udari Gunathilake',  'F','2021-04-18'),('KUN-PLK-044','Madushika Pathirana','F','2020-09-27'),
    ('KUN-PLK-045','Gayani Wimalasena',  'F','2022-06-13'),('KUN-PLK-046','Ruwanthika Mendis',  'F','2021-12-07'),
    ('KUN-PLK-047','Sanduni Wijesekara', 'F','2020-02-21'),('KUN-PLK-048','Hasala Perera',      'F','2023-04-15'),
    ('KUN-PLK-049','Dinushka Rajapaksa', 'F','2019-10-11'),('KUN-PLK-050','Nishadi Karunarathna','F','2022-11-06'),
    ('KUN-PLK-051','Upeksha Herath',     'F','2021-07-22'),('KUN-PLK-052','Pooja Kuruppu',      'F','2020-05-14'),
    ('KUN-PLK-053','Thilanka Senerath',  'F','2023-08-09'),('KUN-PLK-054','Imesha Jayakody',    'F','2023-01-25'),
    ('KUN-PLK-055','Chamali Athukorala', 'F','2021-03-01'),('KUN-PLK-056','Bhagya Dissanayake', 'F','2019-07-30')
) AS emp(code, name, gender, hire_date)
WHERE e.name = 'Kundasale Estate';

-- Group 5 pluckers
INSERT INTO employee (estate_id, employee_code, full_name, gender, hire_date, employment_type, skill_type, daily_wage_lkr)
SELECT e.id, emp.code, emp.name, emp.gender, emp.hire_date::DATE, 'permanent', 'plucker', 700.00
FROM estate e,
(VALUES
    ('KUN-PLK-057','Rasika Ranaweera',   'F','2021-05-20'),('KUN-PLK-058','Nadeesha Kumari',    'F','2020-10-15'),
    ('KUN-PLK-059','Kumudini Jayasekara','F','2022-07-04'),('KUN-PLK-060','Pradeepika Bandara', 'F','2022-01-09'),
    ('KUN-PLK-061','Wishmi Gunawardena', 'F','2020-03-25'),('KUN-PLK-062','Lakmali Senanayake', 'F','2023-05-20'),
    ('KUN-PLK-063','Tharushi Ratnasiri', 'F','2019-11-07'),('KUN-PLK-064','Subashi Weerasinghe','F','2022-12-18'),
    ('KUN-PLK-065','Dasuni Liyanage',    'F','2021-08-14'),('KUN-PLK-066','Amali Rodrigo',      'F','2020-06-29'),
    ('KUN-PLK-067','Shenali Kahatapitiya','F','2023-09-01'),('KUN-PLK-068','Iresha Kotelawala',  'F','2023-02-14'),
    ('KUN-PLK-069','Vinodha Marasinghe', 'F','2021-04-07'),('KUN-PLK-070','Nisansala Silva',    'F','2019-08-23')
) AS emp(code, name, gender, hire_date)
WHERE e.name = 'Kundasale Estate';

-- Group 6 pluckers
INSERT INTO employee (estate_id, employee_code, full_name, gender, hire_date, employment_type, skill_type, daily_wage_lkr)
SELECT e.id, emp.code, emp.name, emp.gender, emp.hire_date::DATE, 'permanent', 'plucker', 700.00
FROM estate e,
(VALUES
    ('KUN-PLK-071','Mihiri Wickramaratne','F','2021-06-25'),('KUN-PLK-072','Dulini Dharmasena',  'F','2020-11-10'),
    ('KUN-PLK-073','Shanudi Jayawardena', 'F','2022-08-17'),('KUN-PLK-074','Priyanka Ratnaweera','F','2022-02-03'),
    ('KUN-PLK-075','Achala Dissanayake',  'F','2020-04-29'),('KUN-PLK-076','Saduni Karunarathna','F','2023-06-08'),
    ('KUN-PLK-077','Niluka Weeraratne',   'F','2019-12-01'),('KUN-PLK-078','Kasuni Perera',      'F','2023-01-12'),
    ('KUN-PLK-079','Dilanka Rajapaksha',  'F','2021-09-19'),('KUN-PLK-080','Amsha Kumarasiri',   'F','2020-07-05'),
    ('KUN-PLK-081','Thamali Herath',      'F','2023-10-03'),('KUN-PLK-082','Ridma Fernando',     'F','2023-03-22'),
    ('KUN-PLK-083','Sewwandi Edirisinghe','F','2021-05-11'),('KUN-PLK-084','Isuri Samaraweera',  'F','2019-09-16')
) AS emp(code, name, gender, hire_date)
WHERE e.name = 'Kundasale Estate';

-- ---------------------------------------------------------------------------
-- 3. WORKER GROUPS (6 groups for 6 blocks)
-- ---------------------------------------------------------------------------

INSERT INTO worker_group (estate_id, group_code, group_name, supervisor_id, capacity, is_active)
SELECT
    e.id,
    g.group_code,
    g.group_name,
    sup.id,
    15,
    TRUE
FROM estate e
CROSS JOIN (VALUES
    ('G-KUN-01', 'Kundasale Group 1', 'KUN-SUP-01'),
    ('G-KUN-02', 'Kundasale Group 2', 'KUN-SUP-02'),
    ('G-KUN-03', 'Kundasale Group 3', 'KUN-SUP-03'),
    ('G-KUN-04', 'Kundasale Group 4', 'KUN-SUP-04'),
    ('G-KUN-05', 'Kundasale Group 5', 'KUN-SUP-05'),
    ('G-KUN-06', 'Kundasale Group 6', 'KUN-SUP-06')
) AS g(group_code, group_name, sup_code)
JOIN employee sup ON sup.employee_code = g.sup_code AND sup.estate_id = e.id
WHERE e.name = 'Kundasale Estate';

-- ---------------------------------------------------------------------------
-- 4. WORKER GROUP MEMBERS — assign supervisor + 14 pluckers to each group
-- ---------------------------------------------------------------------------

-- Supervisors
INSERT INTO worker_group_member (group_id, employee_id, joined_date, is_active)
SELECT wg.id, emp.id, emp.hire_date, TRUE
FROM worker_group wg
JOIN estate e ON e.id = wg.estate_id AND e.name = 'Kundasale Estate'
JOIN (VALUES
    ('G-KUN-01','KUN-SUP-01'), ('G-KUN-02','KUN-SUP-02'),
    ('G-KUN-03','KUN-SUP-03'), ('G-KUN-04','KUN-SUP-04'),
    ('G-KUN-05','KUN-SUP-05'), ('G-KUN-06','KUN-SUP-06')
) AS m(group_code, emp_code) ON m.group_code = wg.group_code
JOIN employee emp ON emp.employee_code = m.emp_code AND emp.estate_id = e.id;

-- Pluckers: Groups 1-6 get PLK-001..014, 015..028, 029..042, 043..056, 057..070, 071..084
INSERT INTO worker_group_member (group_id, employee_id, joined_date, is_active)
SELECT wg.id, emp.id, emp.hire_date, TRUE
FROM worker_group wg
JOIN estate e ON e.id = wg.estate_id AND e.name = 'Kundasale Estate'
JOIN employee emp ON emp.estate_id = e.id AND emp.skill_type = 'plucker'
WHERE (
    (wg.group_code = 'G-KUN-01' AND emp.employee_code BETWEEN 'KUN-PLK-001' AND 'KUN-PLK-014') OR
    (wg.group_code = 'G-KUN-02' AND emp.employee_code BETWEEN 'KUN-PLK-015' AND 'KUN-PLK-028') OR
    (wg.group_code = 'G-KUN-03' AND emp.employee_code BETWEEN 'KUN-PLK-029' AND 'KUN-PLK-042') OR
    (wg.group_code = 'G-KUN-04' AND emp.employee_code BETWEEN 'KUN-PLK-043' AND 'KUN-PLK-056') OR
    (wg.group_code = 'G-KUN-05' AND emp.employee_code BETWEEN 'KUN-PLK-057' AND 'KUN-PLK-070') OR
    (wg.group_code = 'G-KUN-06' AND emp.employee_code BETWEEN 'KUN-PLK-071' AND 'KUN-PLK-084')
);

-- ---------------------------------------------------------------------------
-- 5. ROTATION CYCLE — 6-round cycle for Kundasale (one round per block)
-- ---------------------------------------------------------------------------

INSERT INTO rotation_cycle (estate_id, cycle_name, total_rounds, current_round, is_active, created_by)
SELECT
    e.id,
    'Kundasale Standard Rotation 2026',
    6,      -- 6 blocks = 6 rounds before cycle restarts
    3,      -- currently on round 3 (mid-cycle for demo)
    TRUE,
    u.id
FROM estate e
JOIN "user" u ON u.estate_id = e.id AND u.role = 'estate_manager'
WHERE e.name = 'Kundasale Estate'
LIMIT 1;

-- ---------------------------------------------------------------------------
-- 6. ROTATION ROUND BLOCK MATRIX
--
--    6 blocks: A1, A2, B1, B2, C1, D1
--    6 groups: G-KUN-01 … G-KUN-06
--
--    Round | A1  | A2  | B1  | B2  | C1  | D1
--    ------+-----+-----+-----+-----+-----+-----
--      1   | G01 | G02 | G03 | G04 | G05 | G06
--      2   | G06 | G01 | G02 | G03 | G04 | G05   (shift right)
--      3   | G05 | G06 | G01 | G02 | G03 | G04
--      4   | G04 | G05 | G06 | G01 | G02 | G03
--      5   | G03 | G04 | G05 | G06 | G01 | G02
--      6   | G02 | G03 | G04 | G05 | G06 | G01
--
--    After 6 rounds every group has been on every block exactly once.
-- ---------------------------------------------------------------------------

INSERT INTO rotation_round_block (rotation_cycle_id, round_number, block_id, worker_group_id)
WITH
    cycle AS (SELECT id FROM rotation_cycle WHERE cycle_name = 'Kundasale Standard Rotation 2026'),
    blocks AS (
        SELECT b.id, b.block_code,
               ROW_NUMBER() OVER (ORDER BY b.block_code) AS pos  -- 1=A1,2=A2,3=B1,4=B2,5=C1,6=D1
        FROM block b
        JOIN estate e ON e.id = b.estate_id
        WHERE e.name = 'Kundasale Estate'
          AND b.block_code IN ('A1','A2','B1','B2','C1','D1')
    ),
    groups AS (
        SELECT wg.id, wg.group_code,
               ROW_NUMBER() OVER (ORDER BY wg.group_code) AS pos  -- 1=G-KUN-01 … 6=G-KUN-06
        FROM worker_group wg
        JOIN estate e ON e.id = wg.estate_id
        WHERE e.name = 'Kundasale Estate'
          AND wg.is_active = TRUE
    ),
    rounds AS (SELECT generate_series(1, 6) AS round_number),
    matrix AS (
        SELECT
            r.round_number,
            b.id                         AS block_id,
            b.pos                        AS block_pos,
            -- cyclic shift: group assigned to block pos p in round r
            -- = group at position ((p - r) mod 6) + 1
            ((b.pos - r.round_number + 6) % 6) + 1 AS group_pos
        FROM rounds r
        CROSS JOIN blocks b
    )
SELECT
    (SELECT id FROM cycle),
    m.round_number,
    m.block_id,
    g.id AS worker_group_id
FROM matrix m
JOIN groups g ON g.pos = m.group_pos;

-- ---------------------------------------------------------------------------
-- 7. LABOUR PLAN for current week
-- ---------------------------------------------------------------------------

INSERT INTO labour_plan (estate_id, created_by, week_start, total_workers, target_kg, status, notes)
SELECT
    e.id,
    u.id,
    DATE_TRUNC('week', CURRENT_DATE)::DATE,
    90,     -- 6 groups × 15 workers
    54000,  -- 6 blocks × 9000 kg target per block
    'published',
    'Auto-generated from rotation cycle — Round 3'
FROM estate e
JOIN "user" u ON u.estate_id = e.id AND u.role = 'estate_manager'
WHERE e.name = 'Kundasale Estate'
LIMIT 1
ON CONFLICT (estate_id, week_start) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 8. BLOCK ASSIGNMENTS for current week (one per block, Mon–Sat)
--    Uses Round 3 of the rotation cycle.
-- ---------------------------------------------------------------------------

INSERT INTO block_assignment (
    labour_plan_id, block_id, worker_group_id,
    assignment_date, rotation_cycle_id, rotation_round,
    expected_yield_kg, plucking_round_number, status
)
WITH
    plan AS (
        SELECT lp.id, lp.estate_id
        FROM labour_plan lp
        JOIN estate e ON e.id = lp.estate_id
        WHERE e.name = 'Kundasale Estate'
          AND lp.week_start = DATE_TRUNC('week', CURRENT_DATE)::DATE
    ),
    cycle AS (SELECT id FROM rotation_cycle WHERE cycle_name = 'Kundasale Standard Rotation 2026'),
    round3 AS (
        SELECT rrb.block_id, rrb.worker_group_id
        FROM rotation_round_block rrb
        WHERE rrb.rotation_cycle_id = (SELECT id FROM cycle)
          AND rrb.round_number = 3
    )
SELECT
    (SELECT id FROM plan),
    round3.block_id,
    round3.worker_group_id,
    DATE_TRUNC('week', CURRENT_DATE)::DATE,
    (SELECT id FROM cycle),
    3,
    9000.000,
    3,
    'scheduled'
FROM round3;
