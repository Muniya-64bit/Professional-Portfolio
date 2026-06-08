-- =============================================================================
-- 009: Add read-only 'manager' role
-- =============================================================================
-- The original role CHECK constraint (001_initial_schema.sql) did not allow
-- 'manager'. A manager is a read-only user scoped to a single estate
-- (user.estate_id). estate_id already exists on "user", so only the CHECK
-- constraint needs widening.

ALTER TABLE "user" DROP CONSTRAINT IF EXISTS user_role_check;

ALTER TABLE "user" ADD CONSTRAINT user_role_check CHECK (role IN (
    'admin',
    'estate_manager',
    'manager',
    'field_supervisor',
    'factory_manager',
    'finance',
    'agronomist'
));
