-- MODULE 7 — Input Validation & Schema Hardening (P3-05)
-- Adds timezone_updated_at to users so we can enforce a minimum interval
-- between timezone changes (prevents streak-banking via rapid TZ flipping).

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS timezone_updated_at TIMESTAMPTZ;

-- Index so the cooldown look-up (WHERE user_id = ?) is an index scan.
CREATE INDEX IF NOT EXISTS idx_users_tz_updated_at
    ON users (user_id, timezone_updated_at);
