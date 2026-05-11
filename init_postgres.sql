CREATE TABLE IF NOT EXISTS users (
    user_id           BIGINT PRIMARY KEY,
    discord_username  TEXT,
    email             TEXT,
    timezone          TEXT DEFAULT 'Asia/Kolkata',
    is_active         INTEGER DEFAULT 1,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id           BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    tracked_channel_id BIGINT DEFAULT 0,
    deadline_hour     INTEGER DEFAULT 23,
    deadline_minute   INTEGER DEFAULT 0,
    warn_hour         INTEGER DEFAULT 22,
    warn_minute       INTEGER DEFAULT 0,
    final_hour        INTEGER DEFAULT 22,
    final_minute      INTEGER DEFAULT 30,
    email_hour        INTEGER DEFAULT 23,
    email_minute      INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS progress_logs (
    id            SERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    channel_id    BIGINT NOT NULL,
    message_content TEXT,
    topics        TEXT,
    parsed_fields JSONB,
    posted_at     TIMESTAMP NOT NULL,
    log_date      DATE NOT NULL,
    message_type  TEXT DEFAULT 'progress'
);

CREATE INDEX IF NOT EXISTS idx_progress_logs_user_date ON progress_logs(user_id, log_date);

CREATE TABLE IF NOT EXISTS daily_status (
    id                SERIAL PRIMARY KEY,
    user_id           BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    date              DATE NOT NULL,
    posted_flag       INTEGER DEFAULT 0,
    warn_sent         INTEGER DEFAULT 0,
    final_sent        INTEGER DEFAULT 0,
    email_sent        INTEGER DEFAULT 0,
    UNIQUE(user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_status_user_date ON daily_status(user_id, date);

CREATE TABLE IF NOT EXISTS streaks (
    user_id        BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_post_date DATE
);

CREATE TABLE IF NOT EXISTS weekly_summaries (
    id                    SERIAL PRIMARY KEY,
    user_id               BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    week_start            DATE NOT NULL,
    week_end              DATE NOT NULL,
    days_posted           INTEGER DEFAULT 0,
    days_missed           INTEGER DEFAULT 0,
    consistency_percentage NUMERIC DEFAULT 0.0,
    total_messages        INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS leetcode_problems (
    question_id   BIGINT PRIMARY KEY,
    title         TEXT,
    title_slug    TEXT,
    difficulty    TEXT,
    topics        JSONB
);
