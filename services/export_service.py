"""
Export service — CSV exports of progress data.
"""

import csv
import os
import logging
from datetime import datetime
from db import database

logger = logging.getLogger("dsa_bot.export")

EXPORT_DIR = "exports"


def _ensure_export_dir():
    os.makedirs(EXPORT_DIR, exist_ok=True)


async def export_progress_csv(user_id: int, start_date: str = "", end_date: str = "") -> str:
    """
    Export progress logs to a CSV file.
    Returns the file path of the generated CSV.
    """
    _ensure_export_dir()

    logs = await database.get_progress_logs(user_id, start_date, end_date)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"progress_export_{user_id}_{timestamp}.csv"
    filepath = os.path.join(EXPORT_DIR, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Date", "Posted At", "Message", "Topics", "Type", "Channel ID"
        ])
        for log in logs:
            writer.writerow([
                log["log_date"],
                log["posted_at"],
                log["message_content"],
                log["topics"],
                log.get("message_type", "progress"),
                log["channel_id"],
            ])

    logger.info(f"CSV exported: {filepath} ({len(logs)} rows)")
    return filepath


async def export_daily_status_csv(user_id: int) -> str:
    """Export daily status log (posted/missed per day) to CSV."""
    _ensure_export_dir()

    statuses = await database.get_all_daily_statuses(user_id)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"daily_status_{user_id}_{timestamp}.csv"
    filepath = os.path.join(EXPORT_DIR, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Date", "Posted", "Warning Sent", "Final Sent", "Email Sent"
        ])
        for s in statuses:
            writer.writerow([
                s["date"],
                "Yes" if s["posted_flag"] else "No",
                "Yes" if s.get("warn_sent", 0) else "No",
                "Yes" if s.get("final_sent", 0) else "No",
                "Yes" if s.get("email_sent", 0) else "No",
            ])

    logger.info(f"Daily status CSV exported: {filepath}")
    return filepath
