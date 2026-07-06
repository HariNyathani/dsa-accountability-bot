-- =============================================================================
-- Migration 004: Token revocation table
-- Covers: P2-05 (30-day non-revocable JWT)
-- Author: Security Remediation — Module 4
-- Safe to re-run: CREATE TABLE IF NOT EXISTS is idempotent.
-- =============================================================================

CREATE TABLE IF NOT EXISTS revoked_tokens (
    jti        TEXT PRIMARY KEY,
    revoked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for the cleanup job / expiry pruning (tokens older than
-- ACCESS_TOKEN_TTL_HOURS can never be valid, so we can prune them).
CREATE INDEX IF NOT EXISTS idx_revoked_tokens_revoked_at
    ON revoked_tokens (revoked_at);
