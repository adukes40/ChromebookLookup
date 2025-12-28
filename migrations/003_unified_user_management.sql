-- Migration: 003_unified_user_management.sql
-- Description: Add unified user management support with IIQ user sync and fee tracking
-- Date: 2025-12-27

BEGIN;

-- Add new columns to users table for unified user management
ALTER TABLE users
  ADD COLUMN google_user_id VARCHAR(255),
  ADD COLUMN iiq_user_id VARCHAR(255),
  ADD COLUMN google_synced_at TIMESTAMP,
  ADD COLUMN iiq_synced_at TIMESTAMP,
  ADD COLUMN total_fee_balance NUMERIC(10, 2) DEFAULT 0.00,
  ADD COLUMN fee_last_synced TIMESTAMP,
  ADD COLUMN has_outstanding_fees BOOLEAN DEFAULT FALSE,
  ADD COLUMN iiq_location VARCHAR(255),
  ADD COLUMN iiq_role_name VARCHAR(100),
  ADD COLUMN is_active_iiq BOOLEAN DEFAULT TRUE,
  ADD COLUMN username VARCHAR(255),
  ADD COLUMN data_source VARCHAR(50),
  ADD COLUMN is_merged BOOLEAN DEFAULT FALSE;

-- Create indexes for performance
CREATE INDEX idx_users_google_user_id ON users(google_user_id);
CREATE INDEX idx_users_iiq_user_id ON users(iiq_user_id);
CREATE INDEX idx_users_email_lower ON users(LOWER(email));
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_has_fees ON users(has_outstanding_fees);
CREATE INDEX idx_users_data_source ON users(data_source);

-- Backfill existing Google users
UPDATE users
SET
  google_user_id = user_id,
  data_source = 'google',
  is_merged = FALSE,
  google_synced_at = COALESCE(updated_at, NOW()),
  is_active_iiq = TRUE
WHERE user_id IS NOT NULL AND google_user_id IS NULL;

-- Add comment describing the unified user management feature
COMMENT ON COLUMN users.google_user_id IS 'Google user ID from Google Workspace Admin API';
COMMENT ON COLUMN users.iiq_user_id IS 'IncidentIQ user ID from IIQ API';
COMMENT ON COLUMN users.total_fee_balance IS 'Total outstanding fee balance from IIQ Fee Tracker';
COMMENT ON COLUMN users.iiq_location IS 'User location from IncidentIQ';
COMMENT ON COLUMN users.data_source IS 'Data source: google, iiq, or merged';
COMMENT ON COLUMN users.is_merged IS 'True if user exists in both Google and IIQ';

COMMIT;
