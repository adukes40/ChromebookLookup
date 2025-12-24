-- Migration: Add IIQ Owner and Status Fields
-- Date: 2025-12-24
-- Description: Add minimal IIQ enhancement fields (owner email/name, status)
-- Run with: psql -U chromebook_user -d chromebook_dashboard -f migrations/001_add_iiq_owner_status.sql

BEGIN;

-- Add IIQ Owner columns
ALTER TABLE chromebooks ADD COLUMN IF NOT EXISTS iiq_owner_email VARCHAR(255);
ALTER TABLE chromebooks ADD COLUMN IF NOT EXISTS iiq_owner_name VARCHAR(255);

-- Add IIQ Status column
ALTER TABLE chromebooks ADD COLUMN IF NOT EXISTS iiq_status VARCHAR(100);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_chromebooks_iiq_owner_email ON chromebooks(iiq_owner_email);
CREATE INDEX IF NOT EXISTS idx_chromebooks_iiq_status ON chromebooks(iiq_status);

-- Add comments for documentation
COMMENT ON COLUMN chromebooks.iiq_owner_email IS 'Official assigned user email from IIQ asset management';
COMMENT ON COLUMN chromebooks.iiq_owner_name IS 'Official assigned user full name from IIQ asset management';
COMMENT ON COLUMN chromebooks.iiq_status IS 'Asset status from IIQ (In Use, In Repair, Available, etc.)';

COMMIT;

-- Verify migration
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'chromebooks'
    AND column_name IN ('iiq_owner_email', 'iiq_owner_name', 'iiq_status')
ORDER BY column_name;
