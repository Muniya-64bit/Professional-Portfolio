-- Remove June 2026 labour plans and yield predictions.
-- block_assignment and block_assignment_member are deleted via ON DELETE CASCADE
-- from labour_plan. rotation_round_block is the permanent rotation matrix and
-- is intentionally left untouched.

BEGIN;

DELETE FROM yield_prediction
WHERE year = 2026 AND month = 6;

DELETE FROM labour_plan
WHERE period_start >= '2026-06-01'
  AND period_start <  '2026-07-01';

COMMIT;
