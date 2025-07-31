-- HoopHead Database Initialization
-- This script sets up the initial database structure

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create database user if not exists (handled by Docker environment variables)
-- The main database and user are created by Docker PostgreSQL image

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE hoophead TO hoophead;

-- Create schema for organizing tables
CREATE SCHEMA IF NOT EXISTS basketball;
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS queries;

-- Set default search path
ALTER DATABASE hoophead SET search_path TO public, basketball, users, queries;

-- Add comments
COMMENT ON SCHEMA basketball IS 'Basketball-related data tables';
COMMENT ON SCHEMA users IS 'User management and authentication';
COMMENT ON SCHEMA queries IS 'Query logging and caching'; 