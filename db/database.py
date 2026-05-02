"""
SQLite database manager — async via aiosqlite.

Multi-user schema:
  users, user_settings, progress_logs, daily_status, streaks, weekly_summaries
"""

import aiosqlite
import os
import logging
from typing import Optional, List

import config

logger = logging.getLogger("dsa_bot.database")

DB_PATH = config.DATABASE_PATH


async def _ensure_dir():
    """Create the directory for the DB file if it doesn't exist."""
    directory = os.path.dirname(DB_PATH)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


async def get_connection() -> aiosqlite.Connection:
    """Return an async connection to the SQLite database."""
    await _ensure_dir()
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# ── Schema ───────────────────────────────────────────────────────────────────

async def init_db():
    """Create all tables if they don't exist, then run migrations."""
    conn = await get_connection()
    try:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id           INTEGER PRIMARY KEY,
                discord_username  TEXT,
                email             TEXT,
                timezone          TEXT DEFAULT 'Asia/Kolkata',
                is_active         INTEGER DEFAULT 1,
                created_at        TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS user_settings (
                user_id           INTEGER PRIMARY KEY,
                tracked_channel_id INTEGER DEFAULT 0,
                deadline_hour     INTEGER DEFAULT 23,
                deadline_minute   INTEGER DEFAULT 0,
                warn_hour         INTEGER DEFAULT 22,
                warn_minute       INTEGER DEFAULT 0,
                final_hour        INTEGER DEFAULT 23,
                final_minute      INTEGER DEFAULT 0,
                email_hour        INTEGER DEFAULT 23,
                email_minute      INTEGER DEFAULT 30,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS progress_logs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                channel_id    INTEGER NOT NULL,
                message_content TEXT,
                topics        TEXT,
                posted_at     TEXT NOT NULL,
                log_date      TEXT NOT NULL,
                message_type  TEXT DEFAULT 'progress',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS daily_status (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id           INTEGER NOT NULL,
                date              TEXT NOT NULL,
                posted_flag       INTEGER DEFAULT 0,
                warn_sent         INTEGER DEFAULT 0,
                final_sent        INTEGER DEFAULT 0,
                email_sent        INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, date)
            );

            CREATE TABLE IF NOT EXISTS streaks (
                user_id        INTEGER PRIMARY KEY,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_post_date TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS weekly_summaries (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id               INTEGER NOT NULL,
                week_start            TEXT NOT NULL,
                week_end              TEXT NOT NULL,
                days_posted           INTEGER DEFAULT 0,
                days_missed           INTEGER DEFAULT 0,
                consistency_percentage REAL DEFAULT 0.0,
                total_messages        INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_progress_logs_user_date
                ON progress_logs(user_id, log_date);
            CREATE INDEX IF NOT EXISTS idx_daily_status_user_date
                ON daily_status(user_id, date);
            """
        )
        await conn.commit()

        # Run migrations for existing databases
        await _migrate(conn)

        logger.info("Database tables initialised successfully.")
    finally:
        await conn.close()


async def _migrate(conn: aiosqlite.Connection):
    """Run incremental migrations for schema changes."""

    # Check if user_settings table has any rows — if users table exists
    # but user_settings doesn't have entries for those users, populate defaults
    try:
        cursor = await conn.execute("SELECT user_id FROM users")
        existing_users = [row[0] for row in await cursor.fetchall()]
        for uid in existing_users:
            await conn.execute(
                "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)",
                (uid,),
            )
        await conn.commit()
    except Exception:
        pass

    # Add timezone and is_active columns to users if missing (migration from old schema)
    try:
        cursor = await conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "timezone" not in columns:
            await conn.execute(
                "ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'Asia/Kolkata'"
            )
        if "is_active" not in columns:
            await conn.execute(
                "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1"
            )
        await conn.commit()
    except Exception as e:
        logger.debug(f"Migration column check: {e}")

    # Migrate daily_status columns from old naming convention
    try:
        cursor = await conn.execute("PRAGMA table_info(daily_status)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "reminder_10pm_sent" in columns and "warn_sent" not in columns:
            # Old schema — recreate with new column names
            await conn.executescript("""
                ALTER TABLE daily_status RENAME TO daily_status_old;
                CREATE TABLE daily_status (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id           INTEGER NOT NULL,
                    date              TEXT NOT NULL,
                    posted_flag       INTEGER DEFAULT 0,
                    warn_sent         INTEGER DEFAULT 0,
                    final_sent        INTEGER DEFAULT 0,
                    email_sent        INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, date)
                );
                INSERT INTO daily_status (id, user_id, date, posted_flag, warn_sent, final_sent, email_sent)
                    SELECT id, user_id, date, posted_flag,
                           reminder_10pm_sent, reminder_11pm_sent, reminder_1130pm_sent
                    FROM daily_status_old;
                DROP TABLE daily_status_old;
                CREATE INDEX IF NOT EXISTS idx_daily_status_user_date
                    ON daily_status(user_id, date);
            """)
            await conn.commit()
            logger.info("Migrated daily_status columns to new naming.")
    except Exception as e:
        logger.debug(f"daily_status migration: {e}")


# ── User helpers ─────────────────────────────────────────────────────────────

async def register_user(user_id: int, discord_username: str = "", email: str = "",
                        timezone: str = "Asia/Kolkata") -> bool:
    """
    Register a new user. Returns True if newly created, False if already exists.
    Also creates default user_settings row.
    """
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        )
        existing = await cursor.fetchone()
        if existing:
            # Reactivate if deactivated
            await conn.execute(
                "UPDATE users SET is_active = 1, discord_username = ? WHERE user_id = ?",
                (discord_username, user_id),
            )
            await conn.execute(
                "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)",
                (user_id,),
            )
            await conn.commit()
            return False

        await conn.execute(
            """
            INSERT INTO users (user_id, discord_username, email, timezone)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, discord_username, email, timezone),
        )
        await conn.execute(
            "INSERT INTO user_settings (user_id) VALUES (?)",
            (user_id,),
        )
        await conn.execute(
            """
            INSERT OR IGNORE INTO streaks (user_id, current_streak, longest_streak, last_post_date)
            VALUES (?, 0, 0, NULL)
            """,
            (user_id,),
        )
        await conn.commit()
        return True
    finally:
        await conn.close()


async def unregister_user(user_id: int):
    """Deactivate a user (soft delete)."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE users SET is_active = 0 WHERE user_id = ?",
            (user_id,),
        )
        await conn.commit()
    finally:
        await conn.close()


async def is_registered(user_id: int) -> bool:
    """Check if a user is registered and active."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT user_id FROM users WHERE user_id = ? AND is_active = 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row is not None
    finally:
        await conn.close()


async def ensure_user(user_id: int, discord_username: str = "", email: str = ""):
    """Insert user row if it doesn't exist. Legacy compat wrapper."""
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT OR IGNORE INTO users (user_id, discord_username, email)
            VALUES (?, ?, ?)
            """,
            (user_id, discord_username, email),
        )
        await conn.execute(
            "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)",
            (user_id,),
        )
        await conn.commit()
    finally:
        await conn.close()


async def update_user_email(user_id: int, email: str):
    """Update a user's email address."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE users SET email = ? WHERE user_id = ?",
            (email, user_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_user(user_id: int) -> Optional[dict]:
    """Get a single user record."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def get_all_active_users() -> List[dict]:
    """Get all registered and active users."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM users WHERE is_active = 1"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# ── User settings helpers ────────────────────────────────────────────────────

async def get_user_settings(user_id: int) -> Optional[dict]:
    """Get settings for a user."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM user_settings WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def update_user_settings(user_id: int, **kwargs):
    """
    Update specific settings for a user.
    Pass keyword arguments matching column names.
    Example: await update_user_settings(123, tracked_channel_id=456, deadline_hour=22)
    """
    if not kwargs:
        return
    conn = await get_connection()
    try:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [user_id]
        await conn.execute(
            f"UPDATE user_settings SET {sets} WHERE user_id = ?",
            values,
        )
        await conn.commit()
    finally:
        await conn.close()


async def reset_user_settings(user_id: int):
    """Reset a user's settings to defaults."""
    conn = await get_connection()
    try:
        await conn.execute("DELETE FROM user_settings WHERE user_id = ?", (user_id,))
        await conn.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))
        await conn.commit()
    finally:
        await conn.close()


async def get_users_for_channel(channel_id: int) -> List[dict]:
    """Get all active users who track a specific channel."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT u.*, us.tracked_channel_id
            FROM users u
            JOIN user_settings us ON u.user_id = us.user_id
            WHERE us.tracked_channel_id = ? AND u.is_active = 1
            """,
            (channel_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_user_with_settings(user_id: int) -> Optional[dict]:
    """Get a user joined with their settings."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT u.*, us.tracked_channel_id, us.deadline_hour, us.deadline_minute,
                   us.warn_hour, us.warn_minute, us.final_hour, us.final_minute,
                   us.email_hour, us.email_minute
            FROM users u
            LEFT JOIN user_settings us ON u.user_id = us.user_id
            WHERE u.user_id = ?
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def get_all_active_users_with_settings() -> List[dict]:
    """Get all active users joined with their settings."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT u.*, us.tracked_channel_id, us.deadline_hour, us.deadline_minute,
                   us.warn_hour, us.warn_minute, us.final_hour, us.final_minute,
                   us.email_hour, us.email_minute
            FROM users u
            JOIN user_settings us ON u.user_id = us.user_id
            WHERE u.is_active = 1
            """
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# ── Progress log helpers ─────────────────────────────────────────────────────

async def save_progress_log(
    user_id: int,
    channel_id: int,
    message_content: str,
    topics: str,
    posted_at: str,
    log_date: str,
    message_type: str = "progress",
):
    """Insert a progress log entry."""
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO progress_logs
                (user_id, channel_id, message_content, topics, posted_at, log_date, message_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, channel_id, message_content, topics, posted_at, log_date, message_type),
        )
        await conn.commit()
    finally:
        await conn.close()


async def check_duplicate_log(user_id: int, message_content: str, log_date: str) -> bool:
    """Check if an identical message was already logged today (anti-duplicate)."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT id FROM progress_logs
            WHERE user_id = ? AND message_content = ? AND log_date = ?
            LIMIT 1
            """,
            (user_id, message_content, log_date),
        )
        row = await cursor.fetchone()
        return row is not None
    finally:
        await conn.close()


async def get_progress_logs(user_id: int, start_date: str = "", end_date: str = ""):
    """Fetch progress logs for a user, optionally filtered by date range."""
    conn = await get_connection()
    try:
        if start_date and end_date:
            cursor = await conn.execute(
                """
                SELECT * FROM progress_logs
                WHERE user_id = ? AND log_date BETWEEN ? AND ?
                ORDER BY posted_at ASC
                """,
                (user_id, start_date, end_date),
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM progress_logs WHERE user_id = ? ORDER BY posted_at ASC",
                (user_id,),
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_message_count(user_id: int, start_date: str = "", end_date: str = "") -> int:
    """Count total progress messages, optionally within a date range."""
    conn = await get_connection()
    try:
        if start_date and end_date:
            cursor = await conn.execute(
                """
                SELECT COUNT(*) as cnt FROM progress_logs
                WHERE user_id = ? AND log_date BETWEEN ? AND ?
                """,
                (user_id, start_date, end_date),
            )
        else:
            cursor = await conn.execute(
                "SELECT COUNT(*) as cnt FROM progress_logs WHERE user_id = ?",
                (user_id,),
            )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0
    finally:
        await conn.close()


# ── Daily status helpers ─────────────────────────────────────────────────────

async def get_daily_status(user_id: int, target_date: str) -> Optional[dict]:
    """Get daily status row for a specific date."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM daily_status WHERE user_id = ? AND date = ?",
            (user_id, target_date),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def ensure_daily_status(user_id: int, target_date: str):
    """Create daily status row for today if it doesn't exist."""
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT OR IGNORE INTO daily_status (user_id, date) VALUES (?, ?)
            """,
            (user_id, target_date),
        )
        await conn.commit()
    finally:
        await conn.close()


async def mark_posted(user_id: int, target_date: str):
    """Mark the day as posted."""
    await ensure_daily_status(user_id, target_date)
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE daily_status SET posted_flag = 1 WHERE user_id = ? AND date = ?",
            (user_id, target_date),
        )
        await conn.commit()
    finally:
        await conn.close()


async def mark_reminder_sent(user_id: int, target_date: str, reminder_type: str):
    """
    Mark a reminder as sent for today.
    reminder_type: 'warn' | 'final' | 'email'
    Also supports legacy: '10pm' | '11pm' | '1130pm'
    """
    column_map = {
        "warn": "warn_sent",
        "final": "final_sent",
        "email": "email_sent",
        # Legacy compat
        "10pm": "warn_sent",
        "11pm": "final_sent",
        "1130pm": "email_sent",
    }
    column = column_map.get(reminder_type)
    if not column:
        logger.warning(f"Unknown reminder type: {reminder_type}")
        return

    await ensure_daily_status(user_id, target_date)
    conn = await get_connection()
    try:
        await conn.execute(
            f"UPDATE daily_status SET {column} = 1 WHERE user_id = ? AND date = ?",
            (user_id, target_date),
        )
        await conn.commit()
    finally:
        await conn.close()


async def has_posted_today(user_id: int, target_date: str) -> bool:
    """Check if the user has posted today."""
    status = await get_daily_status(user_id, target_date)
    if status is None:
        return False
    return bool(status["posted_flag"])


async def was_reminder_sent(user_id: int, target_date: str, reminder_type: str) -> bool:
    """Check if a specific reminder was already sent today."""
    column_map = {
        "warn": "warn_sent",
        "final": "final_sent",
        "email": "email_sent",
        "10pm": "warn_sent",
        "11pm": "final_sent",
        "1130pm": "email_sent",
    }
    column = column_map.get(reminder_type)
    if not column:
        return False
    status = await get_daily_status(user_id, target_date)
    if status is None:
        return False
    return bool(status[column])


# ── Streak helpers ───────────────────────────────────────────────────────────

async def get_streak(user_id: int) -> dict:
    """Get streak info for a user."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM streaks WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return {
            "user_id": user_id,
            "current_streak": 0,
            "longest_streak": 0,
            "last_post_date": None,
        }
    finally:
        await conn.close()


async def update_streak(user_id: int, current_streak: int, longest_streak: int, last_post_date: str):
    """Upsert streak record."""
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO streaks (user_id, current_streak, longest_streak, last_post_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                current_streak = excluded.current_streak,
                longest_streak = excluded.longest_streak,
                last_post_date = excluded.last_post_date
            """,
            (user_id, current_streak, longest_streak, last_post_date),
        )
        await conn.commit()
    finally:
        await conn.close()


# ── Leaderboard helpers ──────────────────────────────────────────────────────

async def get_leaderboard_data() -> List[dict]:
    """
    Get leaderboard data for all active users.
    Returns list of dicts with user info, streak, and consistency.
    """
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT
                u.user_id,
                u.discord_username,
                COALESCE(s.current_streak, 0) as current_streak,
                COALESCE(s.longest_streak, 0) as longest_streak,
                COALESCE(s.last_post_date, '') as last_post_date,
                (SELECT COUNT(*) FROM progress_logs p WHERE p.user_id = u.user_id) as total_messages,
                (SELECT COUNT(*) FROM daily_status d WHERE d.user_id = u.user_id AND d.posted_flag = 1) as days_posted,
                (SELECT COUNT(*) FROM daily_status d WHERE d.user_id = u.user_id) as total_days
            FROM users u
            LEFT JOIN streaks s ON u.user_id = s.user_id
            WHERE u.is_active = 1
            """
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            total = d["total_days"]
            d["consistency"] = round((d["days_posted"] / total) * 100, 1) if total > 0 else 0.0
            result.append(d)
        return result
    finally:
        await conn.close()


# ── Weekly summary helpers ───────────────────────────────────────────────────

async def save_weekly_summary(
    user_id: int,
    week_start: str,
    week_end: str,
    days_posted: int,
    days_missed: int,
    consistency_percentage: float,
    total_messages: int,
):
    """Insert a weekly summary row."""
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO weekly_summaries
                (user_id, week_start, week_end, days_posted, days_missed,
                 consistency_percentage, total_messages)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, week_start, week_end, days_posted, days_missed,
             consistency_percentage, total_messages),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_daily_statuses_range(user_id: int, start_date: str, end_date: str) -> list:
    """Get daily statuses for a date range."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT * FROM daily_status
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC
            """,
            (user_id, start_date, end_date),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_all_daily_statuses(user_id: int) -> list:
    """Get all daily statuses for a user."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM daily_status WHERE user_id = ? ORDER BY date ASC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()
