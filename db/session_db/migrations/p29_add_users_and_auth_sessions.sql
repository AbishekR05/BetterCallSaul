-- db/session_db/migrations/p29_add_users_and_auth_sessions.sql
-- Phase 2.9 Migration Schema for Users, Auth Sessions, and Session Ownership

CREATE SCHEMA IF NOT EXISTS session_db;

CREATE TABLE IF NOT EXISTS session_db.users (
    user_id UUID PRIMARY KEY,
    auth_identifier TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'disabled', 'deleted')),
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS session_db.auth_sessions (
    token_id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES session_db.users(user_id) ON DELETE CASCADE,
    issued_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at_utc TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE
);

ALTER TABLE session_db.sessions ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES session_db.users(user_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_users_auth_identifier ON session_db.users(auth_identifier);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON session_db.auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at ON session_db.auth_sessions(expires_at_utc);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON session_db.sessions(user_id);
