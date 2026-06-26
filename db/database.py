"""
PostgreSQL database manager.

Multi-user schema:
  users, user_settings, progress_logs, daily_status, streaks, weekly_summaries
"""

import os
import logging
import asyncio
import json
from typing import Optional, List

import psycopg2
import psycopg2.extras
import config

logger = logging.getLogger("dsa_bot.database")

DATABASE_URL = os.getenv("DATABASE_URL")

from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, dsn):
        self.dsn = dsn
        self.pool = None

    def init_pool(self) -> None:
        """Eagerly create the connection pool. Called from app startup."""
        if self.pool:
            return
        if not self.dsn:
            raise RuntimeError("Database connection pool is not initialized (DATABASE_URL may be missing).")
        self.pool = SimpleConnectionPool(5, 25, self.dsn)

    @contextmanager
    def get_connection(self):
        if not self.pool:
            if not self.dsn:
                raise RuntimeError("Database connection pool is not initialized (DATABASE_URL may be missing).")
            self.pool = SimpleConnectionPool(5, 25, self.dsn)
        conn = self.pool.getconn()
        try:
            with conn:
                yield conn
        finally:
            self.pool.putconn(conn)

db_manager = DatabaseManager(DATABASE_URL)

async def _run_sync(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

# ── Schema ───────────────────────────────────────────────────────────────────

async def init_db():
    """Run init_postgres.sql to ensure tables exist."""
    def _sync():
        sql_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'init_postgres.sql')
        if os.path.exists(sql_path):
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql_content)
                    
                    # Sanitize legacy database state
                    cur.execute("""
                        DELETE FROM progress_logs 
                        WHERE topics = 'Uncategorized' 
                           OR topics ~ '^[0-9.]+$'
                    """)
                    if cur.rowcount > 0:
                        logger.info(f"Sanitized DB: Deleted {cur.rowcount} garbage rows from progress_logs.")
                        
                    # NOTE: Sanitizer disabled — limit raised to 200 for testing.
                    # cur.execute("""
                    #     DELETE FROM progress_logs
                    #     WHERE id IN (
                    #         SELECT id
                    #         FROM progress_logs, jsonb_array_elements(parsed_fields->'log') elem
                    #         GROUP BY id
                    #         HAVING sum((elem->>'question_count')::int) > 25
                    #     )
                    # """)
                    # if cur.rowcount > 0:
                    #     logger.info(f"Sanitized DB: Deleted {cur.rowcount} clown data rows (>25 q's) from progress_logs.")
                conn.commit()
    return await _run_sync(_sync)

# ── User helpers ─────────────────────────────────────────────────────────────

async def register_user(user_id: int, discord_username: str = "", email: str = "",
                        timezone: str = "Asia/Kolkata") -> bool:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                existing = cur.fetchone()
                if existing:
                    cur.execute("UPDATE users SET is_active = 1, discord_username = %s WHERE user_id = %s",
                                (discord_username, user_id))
                    cur.execute("INSERT INTO user_settings (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
                    return False

                cur.execute("""
                    INSERT INTO users (user_id, discord_username, email, timezone)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, discord_username, email, timezone))
                cur.execute("INSERT INTO user_settings (user_id) VALUES (%s)", (user_id,))
                cur.execute("""
                    INSERT INTO streaks (user_id, current_streak, longest_streak, last_post_date)
                    VALUES (%s, 0, 0, NULL) ON CONFLICT DO NOTHING
                """, (user_id,))
                return True
    return await _run_sync(_sync)


async def unregister_user(user_id: int):
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET is_active = 0 WHERE user_id = %s", (user_id,))
    return await _run_sync(_sync)


async def is_registered(user_id: int) -> bool:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE user_id = %s AND is_active = 1", (user_id,))
                return cur.fetchone() is not None
    return await _run_sync(_sync)


async def ensure_user(user_id: int, discord_username: str = "", email: str = ""):
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (user_id, discord_username, email)
                    VALUES (%s, %s, %s) ON CONFLICT (user_id) DO NOTHING
                """, (user_id, discord_username, email))
                if discord_username:
                    cur.execute("""
                        UPDATE users SET discord_username = %s
                        WHERE user_id = %s AND (discord_username IS NULL OR discord_username = '')
                    """, (discord_username, user_id))
                cur.execute("INSERT INTO user_settings (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
    return await _run_sync(_sync)


async def update_user_email(user_id: int, email: str):
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET email = %s WHERE user_id = %s", (email, user_id))
    return await _run_sync(_sync)


async def get_user(user_id: int) -> Optional[dict]:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                row = cur.fetchone()
                if row:
                    d = dict(row)
                    if 'created_at' in d and d['created_at']:
                        d['created_at'] = str(d['created_at'])
                    return d

                # Auto-heal
                cur.execute("""
                    SELECT 1 FROM streaks WHERE user_id = %(uid)s
                    UNION SELECT 1 FROM progress_logs WHERE user_id = %(uid)s
                    UNION SELECT 1 FROM daily_status WHERE user_id = %(uid)s
                    LIMIT 1
                """, {'uid': user_id})
                if cur.fetchone():
                    logger.info(f"Auto-healing: user_id={user_id}")
                    cur.execute("""
                        INSERT INTO users (user_id, discord_username, timezone, is_active)
                        VALUES (%s, '', 'Asia/Kolkata', 1) ON CONFLICT DO NOTHING
                    """, (user_id,))
                    cur.execute("INSERT INTO user_settings (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
                    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                    row = cur.fetchone()
                    if row:
                        d = dict(row)
                        if 'created_at' in d and d['created_at']:
                            d['created_at'] = str(d['created_at'])
                        return d
                    return None
                return None
    return await _run_sync(_sync)


async def get_all_active_users() -> List[dict]:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE is_active = 1")
                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    if 'created_at' in d and d['created_at']:
                        d['created_at'] = str(d['created_at'])
                    rows.append(d)
                return rows
    return await _run_sync(_sync)



# ── Username (vanity handle) helpers ─────────────────────────────────────────

async def get_user_by_username(username: str) -> Optional[dict]:
    """Fetch an active user by their vanity username handle."""
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    "SELECT * FROM users WHERE username = %s AND is_active = 1",
                    (username,),
                )
                row = cur.fetchone()
                if row:
                    d = dict(row)
                    if 'created_at' in d and d['created_at']:
                        d['created_at'] = str(d['created_at'])
                    return d
                return None
    return await _run_sync(_sync)


async def check_username_available(username: str) -> bool:
    """Return True if the username is not yet claimed by any user."""
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM users WHERE username = %s LIMIT 1",
                    (username,),
                )
                return cur.fetchone() is None
    return await _run_sync(_sync)


async def set_username(user_id: int, username: Optional[str]) -> None:
    """Assign (or clear) a vanity username for a user."""
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET username = %s WHERE user_id = %s",
                    (username, user_id),
                )
    return await _run_sync(_sync)


# ── User settings helpers ────────────────────────────────────────────────────

async def get_user_settings(user_id: int) -> Optional[dict]:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM user_settings WHERE user_id = %s", (user_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    return await _run_sync(_sync)


async def update_user_settings(user_id: int, **kwargs):
    if not kwargs:
        return
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                sets = ", ".join(f"{k} = %s" for k in kwargs)
                values = list(kwargs.values()) + [user_id]
                cur.execute(f"UPDATE user_settings SET {sets} WHERE user_id = %s", values)
    return await _run_sync(_sync)


async def reset_user_settings(user_id: int):
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_settings WHERE user_id = %s", (user_id,))
                cur.execute("INSERT INTO user_settings (user_id) VALUES (%s)", (user_id,))
    return await _run_sync(_sync)


async def get_users_for_channel(channel_id: int) -> List[dict]:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT u.*, us.tracked_channel_id
                    FROM users u
                    JOIN user_settings us ON u.user_id = us.user_id
                    WHERE us.tracked_channel_id = %s AND u.is_active = 1
                """, (channel_id,))
                return [dict(r) for r in cur.fetchall()]
    return await _run_sync(_sync)


async def get_user_with_settings(user_id: int) -> Optional[dict]:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT u.*, us.tracked_channel_id, us.deadline_hour, us.deadline_minute,
                           us.warn_hour, us.warn_minute, us.final_hour, us.final_minute,
                           us.email_hour, us.email_minute
                    FROM users u
                    LEFT JOIN user_settings us ON u.user_id = us.user_id
                    WHERE u.user_id = %s
                """, (user_id,))
                row = cur.fetchone()
                if row:
                    d = dict(row)
                    if 'created_at' in d and d['created_at']:
                        d['created_at'] = str(d['created_at'])
                    return d
                return None
    return await _run_sync(_sync)


async def get_all_active_users_with_settings() -> List[dict]:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT u.*, us.tracked_channel_id, us.deadline_hour, us.deadline_minute,
                           us.warn_hour, us.warn_minute, us.final_hour, us.final_minute,
                           us.email_hour, us.email_minute
                    FROM users u
                    JOIN user_settings us ON u.user_id = us.user_id
                    WHERE u.is_active = 1
                """)
                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    if 'created_at' in d and d['created_at']:
                        d['created_at'] = str(d['created_at'])
                    rows.append(d)
                return rows
    return await _run_sync(_sync)


# ── Progress log helpers ─────────────────────────────────────────────────────

async def save_progress_log(user_id: int, channel_id: int, message_content: str, topics: str,
                            posted_at: str, log_date: str, message_type: str = "progress",
                            parsed_fields: str = None, platform: str = "leetcode",
                            is_review: bool = False):
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO progress_logs
                        (user_id, channel_id, message_content, topics, parsed_fields, posted_at, log_date, message_type, platform, is_review)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, channel_id, message_content, topics, parsed_fields, posted_at, log_date, message_type, platform, is_review))
    return await _run_sync(_sync)


async def check_duplicate_log(user_id: int, message_content: str, log_date: str) -> bool:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM progress_logs
                    WHERE user_id = %s AND message_content = %s AND log_date = %s
                    LIMIT 1
                """, (user_id, message_content, log_date))
                return cur.fetchone() is not None
    return await _run_sync(_sync)


async def get_daily_question_count(user_id: int, log_date: str) -> int:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(sum((elem->>'question_count')::int), 0)
                    FROM progress_logs pl, jsonb_array_elements(pl.parsed_fields->'log') elem
                    WHERE pl.user_id = %s AND pl.log_date = %s
                """, (user_id, log_date))
                row = cur.fetchone()
                return int(row[0]) if row and row[0] else 0
    return await _run_sync(_sync)


async def get_progress_logs(user_id: int, start_date: str = "", end_date: str = ""):
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if start_date and end_date:
                    cur.execute("""
                        SELECT * FROM progress_logs
                        WHERE user_id = %s AND log_date BETWEEN %s AND %s
                        ORDER BY posted_at ASC
                    """, (user_id, start_date, end_date))
                else:
                    cur.execute("SELECT * FROM progress_logs WHERE user_id = %s ORDER BY posted_at ASC", (user_id,))
                # Ensure parsed_fields is returned as a dict or string, if it's JSONB psycopg2 will return dict
                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    if isinstance(d.get("parsed_fields"), dict) or isinstance(d.get("parsed_fields"), list):
                        d["parsed_fields"] = json.dumps(d["parsed_fields"])
                    # Convert dates/timestamps to string to match SQLite behaviour
                    if 'log_date' in d and d['log_date']:
                        d['log_date'] = str(d['log_date'])
                    if 'posted_at' in d and d['posted_at']:
                        d['posted_at'] = str(d['posted_at'])
                    rows.append(d)
                return rows
    return await _run_sync(_sync)


async def get_recent_progress_logs(user_id: int, limit: int = 10) -> List[dict]:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT * FROM progress_logs
                    WHERE user_id = %s
                    ORDER BY posted_at DESC
                    LIMIT %s
                """, (user_id, limit))
                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    if isinstance(d.get("parsed_fields"), dict) or isinstance(d.get("parsed_fields"), list):
                        d["parsed_fields"] = json.dumps(d["parsed_fields"])
                    if 'log_date' in d and d['log_date']:
                        d['log_date'] = str(d['log_date'])
                    if 'posted_at' in d and d['posted_at']:
                        d['posted_at'] = str(d['posted_at'])
                    rows.append(d)
                return rows
    return await _run_sync(_sync)


async def get_user_heatmap(user_id: int) -> dict:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Question counts — exclude rest days and plan entries
                cur.execute("""
                    SELECT 
                        log_date,
                        SUM(
                            CASE 
                                WHEN parsed_fields IS NOT NULL THEN 
                                    (SELECT SUM(COALESCE((elem->>'question_count')::integer, 1))
                                     FROM jsonb_array_elements(parsed_fields->'log') AS elem)
                                WHEN topics IS NOT NULL AND topics != '' THEN 
                                    LENGTH(topics) - LENGTH(REPLACE(topics, ',', '')) + 1
                                ELSE 1 
                            END
                        ) as daily_questions
                    FROM progress_logs 
                    WHERE user_id = %s AND log_date >= CURRENT_DATE - INTERVAL '365 days'
                      AND message_type NOT IN ('plan', 'rest')
                    GROUP BY log_date
                """, (user_id,))
                
                rows = cur.fetchall()
                heatmap_data = {str(row["log_date"]): int(row["daily_questions"] or 0) for row in rows}
                
                # Rest day dates — separate query
                cur.execute("""
                    SELECT DISTINCT log_date
                    FROM progress_logs
                    WHERE user_id = %s AND log_date >= CURRENT_DATE - INTERVAL '365 days'
                      AND (message_type = 'rest' OR topics = 'Rest')
                """, (user_id,))
                rest_dates = [str(row["log_date"]) for row in cur.fetchall()]
                
                cur.execute("SELECT current_streak, longest_streak FROM streaks WHERE user_id = %s", (user_id,))
                streak_row = cur.fetchone()
                
                all_active_dates = set(heatmap_data.keys()) | set(rest_dates)
                
                return {
                    "dates": heatmap_data,
                    "rest_dates": rest_dates,
                    "active_days": len(all_active_dates),
                    "current_streak": streak_row["current_streak"] if streak_row else 0,
                    "max_streak": streak_row["longest_streak"] if streak_row else 0
                }
    return await _run_sync(_sync)


async def get_message_count(user_id: int, start_date: str = "", end_date: str = "") -> int:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # Sum question_count from parsed_fields JSONB (accurate for all platforms).
                # Falls back to comma-counting the topics column for legacy rows that
                # pre-date parsed_fields (no JSONB present).
                date_filter = ""
                params: list = [user_id]
                if start_date and end_date:
                    date_filter = "AND log_date BETWEEN %s AND %s"
                    params += [start_date, end_date]

                cur.execute(f"""
                    SELECT COALESCE(SUM(
                        CASE
                            WHEN parsed_fields IS NOT NULL
                                 AND parsed_fields ? 'log'
                                 AND jsonb_array_length(parsed_fields->'log') > 0
                            THEN (
                                SELECT COALESCE(SUM((elem->>'question_count')::int), 0)
                                FROM jsonb_array_elements(parsed_fields->'log') AS elem
                            )
                            WHEN topics IS NOT NULL AND topics != ''
                            THEN LENGTH(topics) - LENGTH(REPLACE(topics, ',', '')) + 1
                            ELSE 0
                        END
                    ), 0)
                    FROM progress_logs
                    WHERE user_id = %s
                      AND message_type NOT IN ('plan', 'rest')
                      {date_filter}
                """, params)
                row = cur.fetchone()
                return int(row[0]) if row else 0
    return await _run_sync(_sync)


async def has_rest_today(user_id: int, log_date: str) -> bool:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 1 FROM progress_logs
                    WHERE user_id = %s AND log_date = %s
                      AND (message_type = 'rest' OR topics = 'Rest')
                    LIMIT 1
                """, (user_id, log_date))
                row = cur.fetchone()
                # Explicit bool conversion — never let None evaluate as truthy.
                return row is not None
    result = await _run_sync(_sync)
    return bool(result) if result is not None else False


async def get_monthly_rest_count(user_id: int, current_month: str) -> int:
    """
    Count rest-day entries for a given YYYY-MM month.

    Uses ``log_date`` (stored as the user's local date at write time) instead
    of ``TO_CHAR(posted_at, 'YYYY-MM')`` so that IST users submitting just
    after UTC midnight are counted in the correct local month.
    """
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM progress_logs
                    WHERE user_id = %s
                      AND (message_type = 'rest' OR topics = 'Rest')
                      AND LEFT(log_date::text, 7) = %s
                """, (user_id, current_month))
                row = cur.fetchone()
                # Guard: return 0 on empty result set rather than raising.
                return int(row[0]) if row and row[0] is not None else 0
    result = await _run_sync(_sync)
    return result if result is not None else 0


# ── Admin Suite ──────────────────────────────────────────────────────────────

async def delete_user_progress(user_id: int):
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM progress_logs WHERE user_id = %s", (user_id,))
                cur.execute("UPDATE streaks SET current_streak = 0, longest_streak = 0, last_post_date = NULL WHERE user_id = %s", (user_id,))
                cur.execute("UPDATE daily_status SET posted_flag = 0 WHERE user_id = %s", (user_id,))
    await _run_sync(_sync)
    from utils.streak_utils import recalculate_streak
    await recalculate_streak(user_id)


async def undo_last_entry(user_id: int) -> bool:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT id, log_date FROM progress_logs WHERE user_id = %s ORDER BY posted_at DESC LIMIT 1", (user_id,))
                row = cur.fetchone()
                if row:
                    log_id = row["id"]
                    log_date = row["log_date"]
                    cur.execute("DELETE FROM progress_logs WHERE id = %s", (log_id,))
                    
                    cur.execute("SELECT id FROM progress_logs WHERE user_id = %s AND log_date = %s AND message_type != 'plan' LIMIT 1", (user_id, log_date))
                    if not cur.fetchone():
                        cur.execute("UPDATE daily_status SET posted_flag = 0 WHERE user_id = %s AND date = %s", (user_id, log_date))
                    return True
                return False
    log_deleted = await _run_sync(_sync)
    if log_deleted:
        from utils.streak_utils import recalculate_streak
        await recalculate_streak(user_id)
        return True
    return False


# ── Daily status helpers ─────────────────────────────────────────────────────

async def get_daily_status(user_id: int, target_date: str) -> Optional[dict]:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM daily_status WHERE user_id = %s AND date = %s", (user_id, target_date))
                row = cur.fetchone()
                if row:
                    d = dict(row)
                    if 'date' in d and d['date']:
                        d['date'] = str(d['date'])
                    return d
                return None
    return await _run_sync(_sync)


async def ensure_daily_status(user_id: int, target_date: str):
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO daily_status (user_id, date) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user_id, target_date))
    return await _run_sync(_sync)


async def mark_posted(user_id: int, target_date: str):
    await ensure_daily_status(user_id, target_date)
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE daily_status SET posted_flag = 1 WHERE user_id = %s AND date = %s", (user_id, target_date))
    return await _run_sync(_sync)


async def mark_reminder_sent(user_id: int, target_date: str, reminder_type: str):
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
        return
    await ensure_daily_status(user_id, target_date)
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"UPDATE daily_status SET {column} = 1 WHERE user_id = %s AND date = %s", (user_id, target_date))
    return await _run_sync(_sync)


async def has_posted_today(user_id: int, target_date: str) -> bool:
    status = await get_daily_status(user_id, target_date)
    if status is None:
        return False
    return bool(status["posted_flag"])


async def was_reminder_sent(user_id: int, target_date: str, reminder_type: str) -> bool:
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
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM streaks WHERE user_id = %s", (user_id,))
                row = cur.fetchone()
                if row:
                    d = dict(row)
                    if 'last_post_date' in d and d['last_post_date']:
                        d['last_post_date'] = str(d['last_post_date'])
                    return d
                return {
                    "user_id": user_id,
                    "current_streak": 0,
                    "longest_streak": 0,
                    "last_post_date": None,
                }
    return await _run_sync(_sync)


async def update_streak(user_id: int, current_streak: int, longest_streak: int, last_post_date: str):
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO streaks (user_id, current_streak, longest_streak, last_post_date)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT(user_id) DO UPDATE SET
                        current_streak = EXCLUDED.current_streak,
                        longest_streak = EXCLUDED.longest_streak,
                        last_post_date = EXCLUDED.last_post_date
                """, (user_id, current_streak, longest_streak, last_post_date))
    return await _run_sync(_sync)


# ── Leaderboard helpers ──────────────────────────────────────────────────────

async def get_leaderboard_data() -> dict:
    """Return leaderboard rankings (streak >= 1) plus the total registered-user count.

    Returns ``{"total_registered_users": int, "rankings": List[dict]}``.
    """
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Lightweight count of the full active user pool
                cur.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
                total_registered_users = cur.fetchone()[0]

                cur.execute("""
                    WITH msg_counts AS (
                        SELECT
                            p.user_id,
                            COALESCE(SUM(
                                CASE
                                    WHEN p.parsed_fields IS NOT NULL
                                         AND p.parsed_fields ? 'log'
                                         AND jsonb_array_length(p.parsed_fields->'log') > 0
                                    THEN (
                                        SELECT COALESCE(SUM((elem->>'question_count')::int), 0)
                                        FROM jsonb_array_elements(p.parsed_fields->'log') AS elem
                                    )
                                    WHEN p.topics IS NOT NULL AND p.topics != ''
                                    THEN LENGTH(p.topics) - LENGTH(REPLACE(p.topics, ',', '')) + 1
                                    ELSE 0
                                END
                            ), 0)::bigint AS total_messages
                        FROM progress_logs p
                        WHERE p.message_type NOT IN ('plan', 'rest')
                        GROUP BY p.user_id
                    ),
                    day_counts AS (
                        SELECT
                            user_id,
                            COUNT(*) FILTER (WHERE posted_flag = 1) AS days_posted,
                            COUNT(*) AS total_days
                        FROM daily_status
                        GROUP BY user_id
                    )
                    SELECT
                        u.user_id,
                        u.discord_username,
                        u.username,
                        COALESCE(s.current_streak, 0) as current_streak,
                        COALESCE(s.longest_streak, 0) as longest_streak,
                        COALESCE(s.last_post_date::text, '') as last_post_date,
                        COALESCE(m.total_messages, 0) as total_messages,
                        COALESCE(d.days_posted, 0) as days_posted,
                        COALESCE(d.total_days, 0) as total_days
                    FROM users u
                    LEFT JOIN streaks s ON u.user_id = s.user_id
                    LEFT JOIN msg_counts m ON u.user_id = m.user_id
                    LEFT JOIN day_counts d ON u.user_id = d.user_id
                    WHERE u.is_active = 1
                      AND COALESCE(s.current_streak, 0) >= 1
                """)
                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    total = d["total_days"]
                    d["consistency"] = round((d["days_posted"] / total) * 100, 1) if total > 0 else 0.0
                    rows.append(d)
                return {
                    "total_registered_users": total_registered_users,
                    "rankings": rows,
                }
    return await _run_sync(_sync)


# ── Analytics bulk helpers (N+1 elimination) ─────────────────────────────────

async def get_all_progress_topics() -> List[dict]:
    """Bulk-fetch topic data for ALL progress logs in a single query.

    Returns only the columns needed for topic extraction (topics, parsed_fields),
    pre-filtered to exclude plan/rest entries.  Replaces the old per-user
    ``get_progress_logs()`` loop (N queries → 1).
    """
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT topics, parsed_fields
                    FROM progress_logs
                    WHERE message_type NOT IN ('plan', 'rest')
                """)
                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    if isinstance(d.get("parsed_fields"), dict) or isinstance(d.get("parsed_fields"), list):
                        d["parsed_fields"] = json.dumps(d["parsed_fields"])
                    rows.append(d)
                return rows
    return await _run_sync(_sync)


async def get_activity_trend_bulk(start_date: str, end_date: str) -> dict:
    """Aggregate daily posting activity across ALL users in two queries.

    Returns ``{"statuses": [{date, users_posted}], "logs": [{date, total_messages}]}``.
    Both queries run within a single connection checkout, replacing the old
    per-user double loop (2N queries → 2).
    """
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Query 1: Daily posting user counts
                cur.execute("""
                    SELECT
                        date::text AS date,
                        COUNT(*) FILTER (WHERE posted_flag = 1) AS users_posted
                    FROM daily_status
                    WHERE date BETWEEN %s AND %s
                    GROUP BY date
                    ORDER BY date
                """, (start_date, end_date))
                statuses = [dict(r) for r in cur.fetchall()]

                # Query 2: Daily message volume (topic-count based)
                cur.execute("""
                    SELECT
                        log_date::text AS date,
                        SUM(
                            CASE
                                WHEN topics IS NOT NULL AND topics != ''
                                THEN LENGTH(topics) - LENGTH(REPLACE(topics, ',', '')) + 1
                                ELSE 0
                            END
                        ) AS total_messages
                    FROM progress_logs
                    WHERE log_date BETWEEN %s AND %s
                      AND message_type NOT IN ('plan', 'rest')
                    GROUP BY log_date
                    ORDER BY log_date
                """, (start_date, end_date))
                logs = [dict(r) for r in cur.fetchall()]

                return {"statuses": statuses, "logs": logs}
    return await _run_sync(_sync)


# ── Admin bulk-metrics helper ────────────────────────────────────────────────

async def get_admin_user_metrics(today: str) -> List[dict]:
    """Fetch all active users with streaks, totals, consistency, and posted_today
    in a **single query**.  Replaces the old N+1 loop (157 queries → 1)."""
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT
                        u.user_id,
                        u.discord_username,
                        u.is_active,
                        COALESCE(s.current_streak, 0)  AS current_streak,
                        COALESCE(s.longest_streak, 0)  AS longest_streak,

                        -- Total questions (same JSONB logic as get_message_count)
                        COALESCE((
                            SELECT SUM(
                                CASE
                                    WHEN p.parsed_fields IS NOT NULL
                                         AND p.parsed_fields ? 'log'
                                         AND jsonb_array_length(p.parsed_fields->'log') > 0
                                    THEN (
                                        SELECT COALESCE(SUM((elem->>'question_count')::int), 0)
                                        FROM jsonb_array_elements(p.parsed_fields->'log') AS elem
                                    )
                                    WHEN p.topics IS NOT NULL AND p.topics != ''
                                    THEN LENGTH(p.topics) - LENGTH(REPLACE(p.topics, ',', '')) + 1
                                    ELSE 0
                                END
                            )
                            FROM progress_logs p
                            WHERE p.user_id = u.user_id
                              AND p.message_type NOT IN ('plan', 'rest')
                        ), 0) AS total_questions,

                        -- Consistency components
                        COALESCE((
                            SELECT COUNT(*) FILTER (WHERE d.posted_flag = 1)
                            FROM daily_status d WHERE d.user_id = u.user_id
                        ), 0) AS days_posted,
                        COALESCE((
                            SELECT COUNT(*)
                            FROM daily_status d WHERE d.user_id = u.user_id
                        ), 0) AS total_days,

                        -- Posted today
                        EXISTS (
                            SELECT 1 FROM daily_status d
                            WHERE d.user_id = u.user_id
                              AND d.date = %s
                              AND d.posted_flag = 1
                        ) AS posted_today

                    FROM users u
                    LEFT JOIN streaks s ON u.user_id = s.user_id
                    WHERE u.is_active = 1
                    ORDER BY COALESCE(s.current_streak, 0) DESC
                """, (today,))

                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    total = d.pop("total_days")
                    days_posted_val = d.pop("days_posted")
                    d["consistency_pct"] = round(
                        (days_posted_val / total) * 100, 1
                    ) if total > 0 else 0.0
                    rows.append(d)
                return rows
    return await _run_sync(_sync)


# ── Weekly summary helpers ───────────────────────────────────────────────────

async def save_weekly_summary(user_id: int, week_start: str, week_end: str, days_posted: int,
                              days_missed: int, consistency_percentage: float, total_messages: int):
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO weekly_summaries
                        (user_id, week_start, week_end, days_posted, days_missed,
                         consistency_percentage, total_messages)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (user_id, week_start, week_end, days_posted, days_missed,
                     consistency_percentage, total_messages))
    return await _run_sync(_sync)


async def get_daily_statuses_range(user_id: int, start_date: str, end_date: str) -> list:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT * FROM daily_status
                    WHERE user_id = %s AND date BETWEEN %s AND %s
                    ORDER BY date ASC
                """, (user_id, start_date, end_date))
                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    if 'date' in d and d['date']:
                        d['date'] = str(d['date'])
                    rows.append(d)
                return rows
    return await _run_sync(_sync)


async def get_all_daily_statuses(user_id: int) -> list:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM daily_status WHERE user_id = %s ORDER BY date ASC", (user_id,))
                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    if 'date' in d and d['date']:
                        d['date'] = str(d['date'])
                    rows.append(d)
                return rows
    return await _run_sync(_sync)


# ── Revision Bank (Spaced Repetition) helpers ────────────────────────────────

async def upsert_revision_bank(
    user_id: int,
    problem_id: int,
    confidence: int,
    next_review_at: str,
) -> None:
    """
    INSERT a new revision-bank row or UPDATE an existing one.

    On conflict (user_id, problem_id) the existing row is updated with:
      - confidence_last  → the new self-reported confidence score
      - next_review_at   → the newly calculated UTC review timestamp
      - last_reviewed_at → NOW()
      - review_count     → incremented by 1

    ``first_solved_at`` is intentionally left unchanged so we preserve
    the original solve date across all subsequent reviews.
    """
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO revision_bank
                        (user_id, problem_id, confidence_last, next_review_at,
                         first_solved_at, last_reviewed_at, review_count)
                    VALUES (%s, %s, %s, %s::timestamptz, NOW(), NOW(), 1)
                    ON CONFLICT (user_id, problem_id) DO UPDATE SET
                        confidence_last  = EXCLUDED.confidence_last,
                        next_review_at   = EXCLUDED.next_review_at,
                        last_reviewed_at = NOW(),
                        review_count     = revision_bank.review_count + 1
                """, (user_id, problem_id, confidence, next_review_at))
    return await _run_sync(_sync)


async def get_due_revision_items(user_id: int) -> List[dict]:
    """
    Return all revision-bank items that are due (next_review_at <= NOW())
    for the given user, joined with leetcode_problems for title/difficulty/topics.

    Results are ordered by next_review_at ASC (most overdue first).
    """
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT
                        rb.problem_id,
                        rb.confidence_last,
                        rb.next_review_at,
                        rb.first_solved_at,
                        rb.last_reviewed_at,
                        rb.review_count,
                        lp.title,
                        lp.title_slug,
                        lp.difficulty,
                        lp.topics
                    FROM revision_bank rb
                    JOIN leetcode_problems lp ON lp.question_id = rb.problem_id
                    WHERE rb.user_id = %s
                      AND rb.next_review_at::date <= CURRENT_DATE
                    ORDER BY rb.next_review_at ASC
                """, (user_id,))
                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    # Serialize timestamps to ISO strings for JSON serialisation
                    for ts_col in ("next_review_at", "first_solved_at", "last_reviewed_at"):
                        if d.get(ts_col):
                            d[ts_col] = d[ts_col].isoformat()
                    # topics is JSONB — psycopg2 returns it as a Python list already
                    if isinstance(d.get("topics"), str):
                        try:
                            d["topics"] = json.loads(d["topics"])
                        except (ValueError, TypeError):
                            d["topics"] = []
                    rows.append(d)
                return rows
    return await _run_sync(_sync)


async def get_all_due_revision_items() -> List[dict]:
    """
    Bulk-fetch ALL revision-bank items that are due TODAY OR OVERDUE,
    across every active user — for use by the daily SRS digest cron job.

    Returns a flat list of dicts.  Each dict includes:
      - user_id, problem_id, confidence_last, next_review_at,
        review_count, title, difficulty, title_slug
    Ordered by user_id ASC, next_review_at ASC so the caller can iterate
    with itertools.groupby(results, key=lambda r: r["user_id"]).
    """
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT
                        rb.user_id,
                        rb.problem_id,
                        rb.confidence_last,
                        rb.next_review_at,
                        rb.review_count,
                        lp.title,
                        lp.title_slug,
                        lp.difficulty
                    FROM revision_bank rb
                    JOIN leetcode_problems lp ON lp.question_id = rb.problem_id
                    JOIN users u ON u.user_id = rb.user_id
                    WHERE u.is_active = 1
                      AND rb.next_review_at::date <= CURRENT_DATE
                    ORDER BY rb.user_id ASC, rb.next_review_at ASC
                """)
                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    if d.get("next_review_at"):
                        d["next_review_at"] = d["next_review_at"].isoformat()
                    rows.append(d)
                return rows
    return await _run_sync(_sync)


async def get_all_revision_items(
    user_id: int,
    page: int = 1,
    limit: int = 10,
) -> dict:
    """Return ALL revision-bank items for a user (paginated), regardless of
    whether next_review_at is in the past or future.

    Unlike ``get_due_revision_items``, this query has **no** ``next_review_at
    <= NOW()`` predicate — it surfaces the entire tracking population so the
    mobile client can render a comprehensive "All Problems" view.

    Returns
    -------
    dict
        ``{"items": List[dict], "total_count": int}``

        Each item dict mirrors the RevisionDueItem schema plus:
        - ``days_remaining`` (float): positive = future, negative = overdue.
          Computed server-side to avoid timezone drift.
        - ``total_count``: total rows before pagination (from window function).
    """
    offset = (page - 1) * limit

    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    """
                    WITH ranked AS (
                        SELECT
                            rb.problem_id,
                            rb.confidence_last,
                            rb.next_review_at,
                            rb.first_solved_at,
                            rb.last_reviewed_at,
                            rb.review_count,
                            lp.title,
                            lp.title_slug,
                            lp.difficulty,
                            lp.topics,
                            EXTRACT(EPOCH FROM (rb.next_review_at - NOW()))
                                / 86400.0                          AS days_remaining,
                            COUNT(*) OVER ()                       AS total_count
                        FROM revision_bank rb
                        JOIN leetcode_problems lp
                          ON lp.question_id = rb.problem_id
                        WHERE rb.user_id = %(user_id)s
                        ORDER BY rb.next_review_at ASC
                    )
                    SELECT * FROM ranked
                    LIMIT  %(limit)s
                    OFFSET %(offset)s
                    """,
                    {"user_id": user_id, "limit": limit, "offset": offset},
                )
                rows = cur.fetchall()
                total_count = int(rows[0]["total_count"]) if rows else 0

                items = []
                for r in rows:
                    d = dict(r)
                    d.pop("total_count", None)

                    # Serialise timestamps to ISO-8601 strings
                    for ts_col in ("next_review_at", "first_solved_at", "last_reviewed_at"):
                        if d.get(ts_col):
                            d[ts_col] = d[ts_col].isoformat()

                    # Ensure days_remaining is a Python float
                    if d.get("days_remaining") is not None:
                        d["days_remaining"] = float(d["days_remaining"])

                    # topics JSONB → Python list
                    raw_topics = d.get("topics")
                    if isinstance(raw_topics, str):
                        try:
                            d["topics"] = json.loads(raw_topics)
                        except (ValueError, TypeError):
                            d["topics"] = []
                    elif not isinstance(raw_topics, list):
                        d["topics"] = []

                    items.append(d)

                return {"items": items, "total_count": total_count}

    return await _run_sync(_sync)


async def get_revision_topic_confidence(user_id: int) -> List[dict]:
    """Aggregate average SRS confidence per topic cluster for a user.

    Unnests the ``topics`` JSONB array on ``leetcode_problems`` using
    ``CROSS JOIN LATERAL jsonb_array_elements_text`` so that a problem
    tagged with multiple topics contributes its ``confidence_last`` score
    to *each* of those topic aggregates independently.

    Results are sorted ``avg_confidence ASC`` (lowest = weakest pattern).
    A secondary ``problem_count DESC`` tie-break surfaces topics backed by
    more data first when two topics share an identical average.

    Returns
    -------
    List[dict]
        Each dict: ``{"topic": str, "avg_confidence": float, "problem_count": int}``.
        Returns ``[]`` if the user has no revision-bank entries.
    """
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        topic_tag                                   AS topic,
                        ROUND(AVG(rb.confidence_last)::numeric, 2) AS avg_confidence,
                        COUNT(*)                                    AS problem_count
                    FROM revision_bank rb
                    JOIN leetcode_problems lp
                      ON lp.question_id = rb.problem_id
                    CROSS JOIN LATERAL
                        jsonb_array_elements_text(lp.topics)       AS topic_tag
                    WHERE rb.user_id = %(user_id)s
                    GROUP BY topic_tag
                    ORDER BY avg_confidence ASC,   -- lowest confidence first (weakest)
                             problem_count DESC    -- tie-break: prefer more data
                    """,
                    {"user_id": user_id},
                )
                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    d["avg_confidence"] = float(d["avg_confidence"])
                    d["problem_count"]  = int(d["problem_count"])
                    rows.append(d)
                return rows

    return await _run_sync(_sync)
