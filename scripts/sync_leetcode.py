"""
LeetCode Problem Metadata Sync Script
──────────────────────────────────────
Fetches all problems from the public LeetCode GraphQL API and upserts them
into the PostgreSQL `leetcode_problems` table.

Usage:
    python -m scripts.sync_leetcode          (from project root)
    python scripts/sync_leetcode.py          (directly)

Recommended cadence: run once initially, then weekly via cron / Task Scheduler.
"""

import asyncio
import json
import logging
import os
import sys
import time
import psycopg2
import psycopg2.extras

import aiohttp
from dotenv import load_dotenv
load_dotenv()

# ── Ensure project root is on sys.path so `config` can be imported ───────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sync_leetcode")

# ── Constants ────────────────────────────────────────────────────────────────
LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
DATABASE_URL = os.getenv("DATABASE_URL")
BATCH_SIZE = 100          # problems per GraphQL request
MAX_TOTAL = 5000          # safety cap — LeetCode currently has ~3 400 problems

GRAPHQL_QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      questionFrontendId
      title
      titleSlug
      difficulty
      topicTags {
        name
      }
    }
  }
}
"""

async def fetch_problems(session: aiohttp.ClientSession, skip: int, limit: int) -> dict:
    """Fetch a batch of problems from the LeetCode GraphQL API."""
    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {
            "categorySlug": "",
            "skip": skip,
            "limit": limit,
            "filters": {},
        },
    }
    headers = {
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com/problemset/",
        "User-Agent": "Mozilla/5.0 (compatible; DSA-Bot-Sync/1.0)",
    }

    async with session.post(LEETCODE_GRAPHQL_URL, json=payload, headers=headers) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"LeetCode API returned HTTP {resp.status}: {text[:300]}")
        return await resp.json()

async def sync():
    """Main sync routine: paginate through LeetCode problems and upsert into Postgres."""
    start_time = time.time()
    logger.info("═══════════════════════════════════════════════════")
    logger.info("  LeetCode Metadata Sync — starting")
    logger.info("═══════════════════════════════════════════════════")

    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable is not set!")
        return

    # Use a thread pool to avoid blocking the event loop with psycopg2
    def _db_init():
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS leetcode_problems (
                        question_id   BIGINT PRIMARY KEY,
                        title         TEXT,
                        title_slug    TEXT,
                        difficulty    TEXT,
                        topics        JSONB
                    )
                """)
            conn.commit()

    await asyncio.to_thread(_db_init)

    total_upserted = 0
    skip = 0

    async with aiohttp.ClientSession() as session:
        # First request to discover total problem count
        data = await fetch_problems(session, skip=0, limit=BATCH_SIZE)
        total_available = data["data"]["problemsetQuestionList"]["total"]
        effective_total = min(total_available, MAX_TOTAL)
        logger.info(f"LeetCode reports {total_available} problems — syncing up to {effective_total}")

        questions = data["data"]["problemsetQuestionList"]["questions"]
        batch_count = await _upsert_batch(questions)
        total_upserted += batch_count
        skip += len(questions)
        logger.info(f"  Batch 1: upserted {batch_count} problems  (skip=0, limit={BATCH_SIZE})")

        batch_num = 2
        while skip < effective_total:
            data = await fetch_problems(session, skip=skip, limit=BATCH_SIZE)
            questions = data["data"]["problemsetQuestionList"]["questions"]
            if not questions:
                logger.info("  No more problems returned — stopping pagination.")
                break

            batch_count = await _upsert_batch(questions)
            total_upserted += batch_count
            logger.info(
                f"  Batch {batch_num}: upserted {batch_count} problems  "
                f"(skip={skip}, limit={BATCH_SIZE})"
            )
            skip += len(questions)
            batch_num += 1

            await asyncio.sleep(1)

    elapsed = time.time() - start_time
    logger.info("───────────────────────────────────────────────────")
    logger.info(f"  Sync complete — {total_upserted} problems upserted in {elapsed:.1f}s")
    logger.info("───────────────────────────────────────────────────")


async def _upsert_batch(questions: list) -> int:
    """Upsert a list of problem dicts into Postgres using execute_values."""
    rows = []
    for q in questions:
        try:
            qid = int(q["questionFrontendId"])
        except (ValueError, TypeError):
            continue

        title = q.get("title", "")
        slug = q.get("titleSlug", "")
        difficulty = q.get("difficulty", "")
        
        topic_tags = q.get("topicTags") or []
        topics_json = json.dumps([tag["name"] for tag in topic_tags])

        rows.append((qid, title, slug, difficulty, topics_json))

    if not rows:
        return 0

    def _sync_upsert():
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                query = """
                    INSERT INTO leetcode_problems 
                        (question_id, title, title_slug, difficulty, topics)
                    VALUES %s
                    ON CONFLICT (question_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        title_slug = EXCLUDED.title_slug,
                        difficulty = EXCLUDED.difficulty,
                        topics = EXCLUDED.topics
                """
                psycopg2.extras.execute_values(cur, query, rows)
            conn.commit()

    await asyncio.to_thread(_sync_upsert)
    return len(rows)


if __name__ == "__main__":
    asyncio.run(sync())
