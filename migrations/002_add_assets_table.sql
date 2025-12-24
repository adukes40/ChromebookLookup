-- Migration: Add Assets Table for All IIQ Device Types
-- Date: 2025-12-24
-- Description: Add assets table to cache ALL IIQ asset types (chromebooks, iPads, laptops, etc.)
-- Run with: psql -U chromebook_user -d chromebook_dashboard -f migrations/002_add_assets_table.sql

BEGIN;

-- Create assets table
CREATE TABLE IF NOT EXISTS assets (
    asset_id VARCHAR(100) PRIMARY KEY,
    asset_tag VARCHAR(100) UNIQUE,
    serial_number VARCHAR(100),
    device_type VARCHAR(100),
    model VARCHAR(255),
    status VARCHAR(100),
    owner_email VARCHAR(255),
    owner_name VARCHAR(255),
    location VARCHAR(255),
    room VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_synced TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_assets_asset_tag ON assets(asset_tag);
CREATE INDEX IF NOT EXISTS idx_assets_serial_number ON assets(serial_number);
CREATE INDEX IF NOT EXISTS idx_assets_device_type ON assets(device_type);
CREATE INDEX IF NOT EXISTS idx_assets_owner_email ON assets(owner_email);

-- Add comments for documentation
COMMENT ON TABLE assets IS 'Cached IIQ asset data for all device types';
COMMENT ON COLUMN assets.asset_id IS 'IIQ AssetID (primary key)';
COMMENT ON COLUMN assets.asset_tag IS 'Asset tag from IIQ';
COMMENT ON COLUMN assets.serial_number IS 'Serial number from IIQ';
COMMENT ON COLUMN assets.device_type IS 'Category from IIQ (Chromebooks, iPads, Laptops, etc.)';
COMMENT ON COLUMN assets.status IS 'Asset status from IIQ (In Use, In Repair, Available, etc.)';
COMMENT ON COLUMN assets.owner_email IS 'Assigned user email from IIQ';
COMMENT ON COLUMN assets.owner_name IS 'Assigned user full name from IIQ';
COMMENT ON COLUMN assets.last_synced IS 'When this record was last fetched from IIQ API';

COMMIT;

-- Verify migration
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'assets'
ORDER BY ordinal_position;
