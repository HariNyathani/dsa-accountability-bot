-- ══════════════════════════════════════════════════════════════════════════════
-- Migration 002 — Revision Bank (Spaced Repetition System)
-- Run once against the production database.
-- All statements are idempotent (IF NOT EXISTS / IF EXISTS guards).
-- ══════════════════════════════════════════════════════════════════════════════

-- ── 1. Extend progress_logs with review-session flag ──────────────────────────
--
-- is_review: TRUE when this row is a spaced-repetition review session rather
-- than a first-time solve.  Defaults to FALSE so all existing rows retain their
-- original meaning without a backfill.

ALTER TABLE progress_logs
    ADD COLUMN IF NOT EXISTS is_review BOOLEAN NOT NULL DEFAULT FALSE;

-- ── 2. Partial index — fast lookup of new (non-review) solves per user/date ──
--
-- Supports analytics queries that aggregate only new problem solves while
-- excluding review repetitions from daily totals.
-- Partial because the predicate is highly selective (is_review = FALSE is ~95%+
-- of rows), keeping the index small and maintenance cheap.

CREATE INDEX IF NOT EXISTS idx_progress_logs_user_date_new_solves
    ON progress_logs (user_id, log_date)
    WHERE is_review = FALSE;

-- ── 3. Revision Bank table ────────────────────────────────────────────────────
--
-- One row per (user, problem) pair.  The composite primary key ensures no
-- duplicates.  next_review_at is updated on each review using the SRS schedule
-- derived from the user's self-reported confidence score.
--
-- confidence_last: 1 = ★☆☆☆☆ Blackout, 2 = ★★☆☆☆ Hard,
--                  3 = ★★★☆☆ Okay, 4 = ★★★★☆ Easy, 5 = ★★★★★ Confident
-- next_review_at:  UTC timestamp when the problem should resurface in the queue

CREATE TABLE IF NOT EXISTS revision_bank (
    user_id         BIGINT      NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    problem_id      BIGINT      NOT NULL REFERENCES leetcode_problems(question_id) ON DELETE CASCADE,
    confidence_last INTEGER     NOT NULL DEFAULT 3
                                CHECK (confidence_last BETWEEN 1 AND 5),
    next_review_at  TIMESTAMPTZ NOT NULL,
    first_solved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_reviewed_at TIMESTAMPTZ,
    review_count    INTEGER     NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, problem_id)
);

-- ── 4. Index — fetch due items in chronological order per user ────────────────
--
-- The primary access pattern for GET /progress/revision/due:
--   WHERE user_id = $1 AND next_review_at <= NOW()
--   ORDER BY next_review_at ASC

CREATE INDEX IF NOT EXISTS idx_revision_bank_user_due
    ON revision_bank (user_id, next_review_at ASC);
