-- ══════════════════════════════════════════════════════════════════════════════
-- Migration 006 — SRS / Revision Bank opt-in enrollment flag
-- DEFAULT TRUE intentionally backfills ALL existing users as enrolled so the
-- current ~15 active SRS users are NOT disrupted by this deploy.
-- New users are created with srs_enrolled=FALSE explicitly in register_user().
-- Unenrolling never touches revision_bank rows.
-- ══════════════════════════════════════════════════════════════════════════════

ALTER TABLE user_settings
    ADD COLUMN IF NOT EXISTS srs_enrolled BOOLEAN NOT NULL DEFAULT TRUE;
