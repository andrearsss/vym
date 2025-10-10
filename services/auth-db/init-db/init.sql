-- Create database (already created by POSTGRES_DB env var)
-- CREATE DATABASE microservices_db;

-- Connect to the database
\c vym_db;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(10) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Insert a default admin user (password: admin123)
-- Password hash for 'admin123' using bcrypt
INSERT INTO users (email, username, password_hash, role) 
VALUES ('admin@example.com', 'admin', '$2a$12$idJGFKxzf4/v/bK0UYiidelrHxP345IJzgnZRkaZMN2sx8FSDBf1W', 'admin')
ON CONFLICT (email) DO NOTHING;

COMMIT;