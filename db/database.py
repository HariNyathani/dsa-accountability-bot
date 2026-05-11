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

    @contextmanager
    def get_connection(self):
        if not self.pool:
            if not self.dsn:
                raise RuntimeError("Database connection pool is not initialized (DATABASE_URL may be missing).")
            self.pool = SimpleConnectionPool(1, 10, self.dsn)
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
                        
                    cur.execute("""
                        DELETE FROM progress_logs 
                        WHERE id IN (
                            SELECT id 
                            FROM progress_logs, jsonb_array_elements(parsed_fields->'log') elem 
                            GROUP BY id 
                            HAVING sum((elem->>'question_count')::int) > 25
                        )
                    """)
                    if cur.rowcount > 0:
                        logger.info(f"Sanitized DB: Deleted {cur.rowcount} clown data rows (>25 q's) from progress_logs.")
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
                            parsed_fields: str = None):
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO progress_logs
                        (user_id, channel_id, message_content, topics, parsed_fields, posted_at, log_date, message_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, channel_id, message_content, topics, parsed_fields, posted_at, log_date, message_type))
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
                # Postgres JSONB translation
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
                    WHERE user_id = %s AND log_date >= CURRENT_DATE - INTERVAL '365 days' AND message_type != 'plan'
                    GROUP BY log_date
                """, (user_id,))
                
                rows = cur.fetchall()
                heatmap_data = {str(row["log_date"]): int(row["daily_questions"] or 0) for row in rows}
                
                cur.execute("SELECT current_streak, longest_streak FROM streaks WHERE user_id = %s", (user_id,))
                streak_row = cur.fetchone()
                
                return {
                    "dates": heatmap_data,
                    "active_days": len(heatmap_data),
                    "current_streak": streak_row["current_streak"] if streak_row else 0,
                    "max_streak": streak_row["longest_streak"] if streak_row else 0
                }
    return await _run_sync(_sync)


async def get_message_count(user_id: int, start_date: str = "", end_date: str = "") -> int:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                if start_date and end_date:
                    cur.execute("""
                        SELECT COALESCE(SUM(CASE WHEN topics IS NOT NULL AND topics != '' THEN LENGTH(topics) - LENGTH(REPLACE(topics, ',', '')) + 1 ELSE 0 END), 0) as cnt FROM progress_logs
                        WHERE user_id = %s AND log_date BETWEEN %s AND %s AND message_type NOT IN ('plan', 'rest')
                    """, (user_id, start_date, end_date))
                else:
                    cur.execute("""
                        SELECT COALESCE(SUM(CASE WHEN topics IS NOT NULL AND topics != '' THEN LENGTH(topics) - LENGTH(REPLACE(topics, ',', '')) + 1 ELSE 0 END), 0) as cnt FROM progress_logs 
                        WHERE user_id = %s AND message_type NOT IN ('plan', 'rest')
                    """, (user_id,))
                row = cur.fetchone()
                return int(row[0]) if row else 0
    return await _run_sync(_sync)


async def has_rest_today(user_id: int, log_date: str) -> bool:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 1 FROM progress_logs
                    WHERE user_id = %s AND log_date = %s AND topics = 'Rest'
                    LIMIT 1
                """, (user_id, log_date))
                return cur.fetchone() is not None
    return await _run_sync(_sync)


async def get_monthly_rest_count(user_id: int, current_month: str) -> int:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM progress_logs
                    WHERE user_id = %s AND topics = 'Rest' AND TO_CHAR(posted_at, 'YYYY-MM') = %s
                """, (user_id, current_month))
                row = cur.fetchone()
                return int(row[0]) if row else 0
    return await _run_sync(_sync)


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

async def get_leaderboard_data() -> List[dict]:
    def _sync():
        with db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT
                        u.user_id,
                        u.discord_username,
                        COALESCE(s.current_streak, 0) as current_streak,
                        COALESCE(s.longest_streak, 0) as longest_streak,
                        COALESCE(s.last_post_date::text, '') as last_post_date,
                        (SELECT COALESCE(SUM(CASE WHEN p.topics IS NOT NULL AND p.topics != '' THEN LENGTH(p.topics) - LENGTH(REPLACE(p.topics, ',', '')) + 1 ELSE 0 END), 0) FROM progress_logs p WHERE p.user_id = u.user_id AND p.message_type != 'plan') as total_messages,
                        (SELECT COUNT(*) FROM daily_status d WHERE d.user_id = u.user_id AND d.posted_flag = 1) as days_posted,
                        (SELECT COUNT(*) FROM daily_status d WHERE d.user_id = u.user_id) as total_days
                    FROM users u
                    LEFT JOIN streaks s ON u.user_id = s.user_id
                    WHERE u.is_active = 1
                """)
                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    total = d["total_days"]
                    d["consistency"] = round((d["days_posted"] / total) * 100, 1) if total > 0 else 0.0
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
