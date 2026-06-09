-- Add state column to block table
ALTER TABLE block 
ADD COLUMN state VARCHAR(50) DEFAULT 'active' CHECK (state IN ('preparation', 'planting', 'growing', 'harvesting', 'fallow', 'maintenance', 'active'));

CREATE INDEX idx_block_state ON block(state);

COMMENT ON COLUMN block.state IS 'Block lifecycle state: preparation, planting, growing, harvesting, fallow, maintenance, active';
