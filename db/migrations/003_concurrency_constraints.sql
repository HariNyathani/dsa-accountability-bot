-- =============================================================================
-- Migration 003: Concurrency Constraints — one rest day per user per date
-- Covers: P3-02 (TOCTOU rest-day limit race, schema side)
-- Author: Security Remediation — Module 1
-- Safe to re-run: all statements use IF NOT EXISTS / idempotent DELETE logic.
-- =============================================================================

-- Step 1: De-duplication guard.
-- Remove any pre-existing duplicate rest rows (keep only the earliest row for
-- each (user_id, log_date) pair) so the unique index below can be built cleanly.
-- If there are NO duplicates this DELETE is a no-op.
DELETE FROM progress_logs a
USING progress_logs b
WHERE a.message_type = 'rest'
  AND b.message_type = 'rest'
  AND a.user_id  = b.user_id
  AND a.log_date = b.log_date
  AND a.id > b.id;

-- Step 2: Partial unique index — enforces one rest entry per (user_id, log_date).
-- Uses a WHERE predicate so it only applies to rows with message_type = 'rest'
-- and has no impact on 'done', 'plan', or other message types.
-- IF NOT EXISTS makes this safe to re-run on an already-migrated database.
CREATE UNIQUE INDEX IF NOT EXISTS idx_progress_one_rest_per_day
    ON progress_logs (user_id, log_date)
    WHERE message_type = 'rest';
