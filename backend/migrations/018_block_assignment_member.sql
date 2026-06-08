-- =============================================================================
-- KVPL — Per-month group membership snapshot
-- Migration 018
--
-- Until now the monthly plan recorded only allocated_workers (a COUNT) per block.
-- Because workers are allocated proportional to each month's yield predictions,
-- the individuals on a block change month to month — but there was no record of
-- WHICH employees, so "who was in group X in March?" could not be answered.
--
-- block_assignment_member captures that: one row per (employee, block, month).
-- Supervisors stay anchored to their group's block; the remaining active
-- employees form a pool distributed to match each block's allocated headcount
-- exactly, so COUNT(members) == block_assignment.allocated_workers.
--
-- UNIQUE (labour_plan_id, employee_id) enforces the core rule of the flexible
-- pool model: an employee is assigned to exactly one block per month.
-- =============================================================================

CREATE TABLE IF NOT EXISTS block_assignment_member (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    block_assignment_id UUID NOT NULL REFERENCES block_assignment(id) ON DELETE CASCADE,
    labour_plan_id      UUID NOT NULL REFERENCES labour_plan(id)      ON DELETE CASCADE,
    employee_id         UUID NOT NULL REFERENCES employee(id)         ON DELETE CASCADE,
    skill_type          VARCHAR(50),
    created_at          TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (labour_plan_id, employee_id)
);

CREATE INDEX IF NOT EXISTS idx_bam_assignment ON block_assignment_member (block_assignment_id);
CREATE INDEX IF NOT EXISTS idx_bam_plan       ON block_assignment_member (labour_plan_id);
CREATE INDEX IF NOT EXISTS idx_bam_employee   ON block_assignment_member (employee_id);

COMMENT ON TABLE block_assignment_member IS
    'Per-month snapshot of which specific employees filled each block assignment.
     Reconciles block_assignment.allocated_workers (a count) with named people so
     historical group membership for any month is queryable.';
