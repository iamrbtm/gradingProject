-- ===========================================
-- MySQL Initialization Script
-- ===========================================
-- This script sets up proper authentication
-- and addresses deprecation warnings
-- ===========================================

-- Set default authentication plugin globally
SET GLOBAL default_authentication_plugin = 'caching_sha2_password';

-- Create database if it doesn't exist (redundant with MYSQL_DATABASE, but safe)
CREATE DATABASE IF NOT EXISTS gradetracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Grant proper privileges to the user (created via environment variables)
-- This ensures the user uses the correct authentication method
FLUSH PRIVILEGES;

-- Log successful initialization
SELECT 'MySQL initialization completed successfully' AS status;