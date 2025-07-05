-- Archelyst Database Initialization Script
-- This script sets up the initial database schema and configuration

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas for different modules
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS securities;
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS ai_analytics;
CREATE SCHEMA IF NOT EXISTS system;

-- Set default search path
ALTER DATABASE archelyst SET search_path TO public, users, securities, market_data, ai_analytics, system;

-- Create basic user roles table
CREATE TABLE IF NOT EXISTS users.roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    level INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default roles
INSERT INTO users.roles (name, description, level) VALUES
    ('user', 'Basic user with standard access', 0),
    ('premium', 'Premium user with enhanced features', 1),
    ('creator', 'Content creator with publishing rights', 2),
    ('admin', 'Administrator with full system access', 3),
    ('superuser', 'Super administrator with all privileges', 4)
ON CONFLICT (name) DO NOTHING;

-- Create users table
CREATE TABLE IF NOT EXISTS users.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    supabase_user_id UUID UNIQUE,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    role_id UUID REFERENCES users.roles(id) DEFAULT (SELECT id FROM users.roles WHERE name = 'user'),
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- Create API keys table for service authentication
CREATE TABLE IF NOT EXISTS system.api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users.users(id),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used TIMESTAMP WITH TIME ZONE
);

-- Create data provider status table
CREATE TABLE IF NOT EXISTS system.data_provider_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'unknown',
    last_check TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_time_ms INTEGER,
    error_message TEXT,
    metadata JSONB
);

-- Create request logs table for analytics
CREATE TABLE IF NOT EXISTS system.request_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id VARCHAR(100),
    user_id UUID REFERENCES users.users(id),
    endpoint VARCHAR(255),
    method VARCHAR(10),
    status_code INTEGER,
    response_time_ms INTEGER,
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users.users(email);
CREATE INDEX IF NOT EXISTS idx_users_supabase_id ON users.users(supabase_user_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users.users(role_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON system.api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON system.api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_request_logs_user ON system.request_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_request_logs_created ON system.request_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_provider_status_name ON system.data_provider_status(provider_name);

-- Create update trigger function
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create update triggers
CREATE TRIGGER set_timestamp_users
    BEFORE UPDATE ON users.users
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_set_timestamp();

CREATE TRIGGER set_timestamp_roles
    BEFORE UPDATE ON users.roles
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_set_timestamp();

-- Grant permissions to the application user
GRANT USAGE ON SCHEMA users, securities, market_data, ai_analytics, system TO archelyst;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA users, securities, market_data, ai_analytics, system TO archelyst;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA users, securities, market_data, ai_analytics, system TO archelyst;

-- Insert a default admin user (for development only)
-- Note: In production, this should be created through the application
INSERT INTO users.users (
    email, 
    username, 
    role_id, 
    is_active, 
    email_verified
) VALUES (
    'admin@archelyst.com',
    'admin',
    (SELECT id FROM users.roles WHERE name = 'admin'),
    TRUE,
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Log initialization completion
INSERT INTO system.data_provider_status (provider_name, status, metadata) VALUES
    ('database_init', 'completed', '{"timestamp": "' || NOW() || '", "version": "1.0.0"}')
ON CONFLICT DO NOTHING;

-- Create a view for user information with role details
CREATE OR REPLACE VIEW users.user_details AS
SELECT 
    u.id,
    u.supabase_user_id,
    u.email,
    u.username,
    u.is_active,
    u.email_verified,
    u.created_at,
    u.updated_at,
    u.last_login,
    r.name as role_name,
    r.description as role_description,
    r.level as role_level
FROM users.users u
JOIN users.roles r ON u.role_id = r.id;

COMMENT ON DATABASE archelyst IS 'Archelyst Backend Database - Financial data and AI analytics platform';