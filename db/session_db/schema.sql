-- db/session_db/schema.sql
-- Phase 2.8 Session Database DDL Schema for PostgreSQL

CREATE SCHEMA IF NOT EXISTS session_db;

CREATE TABLE IF NOT EXISTS session_db.sessions (
    session_id UUID PRIMARY KEY,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at_utc TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'expired', 'closed')),
    turn_count INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS session_db.conversation_turns (
    turn_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES session_db.sessions(session_id) ON DELETE CASCADE,
    turn_index INT NOT NULL,
    user_query TEXT NOT NULL,
    rewritten_query TEXT,
    followup_classification VARCHAR(50) NOT NULL,
    jurisdiction_carried_forward VARCHAR(50),
    domain_carried_forward VARCHAR(100),
    grounded_answer_json JSONB NOT NULL,
    timestamp_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_session_turn_index UNIQUE (session_id, turn_index)
);

CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON session_db.sessions(expires_at_utc);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON session_db.sessions(status);
CREATE INDEX IF NOT EXISTS idx_turns_session_turn_index ON session_db.conversation_turns(session_id, turn_index);
