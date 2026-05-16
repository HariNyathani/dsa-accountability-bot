"""
Codeforces Problem Sync Script
===============================

Fetches the full Codeforces problem list from their public API
and populates the `codeforces_problems` table.

Usage:
    python scripts/sync_codeforces.py

The script will:
  1. Call https://codeforces.com/api/problemset.problems
  2. Parse all problems with their tags and ratings
  3. Upsert into the codeforces_problems table
  4. Report how many problems were synced

Can be run manually or scheduled as a periodic job.
"""

import os
import sys
import json
import logging
import requests

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras
from db.database import db_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("sync_codeforces")

CF_API_URL = "https://codeforces.com/api/problemset.problems"


def fetch_codeforces_problems() -> list[dict]:
    """Fetch the full problem list from the Codeforces API."""
    logger.info(f"Fetching problems from {CF_API_URL} ...")
    resp = requests.get(CF_API_URL, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    if data.get("status") != "OK":
        raise RuntimeError(f"Codeforces API returned non-OK status: {data.get('status')}")

    problems = data["result"]["problems"]
    logger.info(f"Received {len(problems)} problems from Codeforces API.")
    return problems


def sync_to_database(problems: list[dict]) -> tuple[int, int]:
    """
    Upsert problems into the codeforces_problems table.

    Returns (inserted_count, updated_count).
    """
    inserted = 0
    updated = 0

    with db_manager.get_connection() as conn:
        with conn.cursor() as cur:
            # Ensure table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS codeforces_problems (
                    contest_id    INTEGER NOT NULL,
                    problem_index TEXT NOT NULL,
                    title         TEXT,
                    rating        INTEGER,
                    tags          JSONB,
                    PRIMARY KEY (contest_id, problem_index)
                )
            """)

            for p in problems:
                contest_id = p.get("contestId")
                index = p.get("index")

                # Skip problems without a contest ID (some CF problems are standalone)
                if contest_id is None or index is None:
                    continue

                title = p.get("name", "")
                rating = p.get("rating")  # Can be None for unrated problems
                tags = p.get("tags", [])

                cur.execute("""
                    INSERT INTO codeforces_problems (contest_id, problem_index, title, rating, tags)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (contest_id, problem_index)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        rating = EXCLUDED.rating,
                        tags = EXCLUDED.tags
                """, (contest_id, index, title, rating, json.dumps(tags)))

                if cur.statusmessage.startswith("INSERT"):
                    inserted += 1
                else:
                    updated += 1

        conn.commit()

    return inserted, updated


def main():
    logger.info("=" * 60)
    logger.info("Codeforces Problem Sync — Starting")
    logger.info("=" * 60)

    try:
        problems = fetch_codeforces_problems()
        inserted, updated = sync_to_database(problems)

        # Count total in DB
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM codeforces_problems")
                total = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM codeforces_problems WHERE rating IS NOT NULL")
                rated = cur.fetchone()[0]

        logger.info(f"Sync complete!")
        logger.info(f"  Total in DB:      {total}")
        logger.info(f"  With ratings:     {rated}")
        logger.info(f"  Without ratings:  {total - rated}")
        logger.info("=" * 60)

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching from Codeforces API: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
