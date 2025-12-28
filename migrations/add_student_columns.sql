-- Add student columns to users table
-- Migration: Add student_id and student_grade for IIQ sync
-- Date: 2025-12-27

-- Add student columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS student_id VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS student_grade VARCHAR(20);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_student_id ON users(student_id);

-- Verify columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name IN ('student_id', 'student_grade');
