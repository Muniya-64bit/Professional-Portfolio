-- Create block_state lookup table for flexible estate-specific state management
CREATE TABLE IF NOT EXISTS block_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estate_id UUID NOT NULL REFERENCES estate(id) ON DELETE CASCADE,
    state_name VARCHAR(50) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(estate_id, state_name)
);

-- Insert default states for all existing estates
INSERT INTO block_state (estate_id, state_name, description)
SELECT e.id, s.state_name, s.description FROM estate e
CROSS JOIN (
    VALUES
        ('preparation', 'Block being prepared for planting'),
        ('planting', 'Active planting phase'),
        ('growing', 'Plants growing and developing'),
        ('harvesting', 'Active harvesting phase'),
        ('fallow', 'Resting period, no production'),
        ('maintenance', 'Under maintenance or repairs'),
        ('active', 'Active production')
) s(state_name, description)
ON CONFLICT (estate_id, state_name) DO NOTHING;

-- Modify block table to remove CHECK constraint
ALTER TABLE block DROP CONSTRAINT IF EXISTS block_state_check;

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_block_state_estate ON block_state(estate_id);
CREATE INDEX IF NOT EXISTS idx_block_state_active ON block_state(estate_id, is_active);

COMMENT ON TABLE block_state IS 'Estate-specific block operational states - allows custom states per estate';
