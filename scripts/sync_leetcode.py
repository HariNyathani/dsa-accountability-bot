"""
LeetCode Problem Metadata Sync Script
──────────────────────────────────────
Fetches all problems from the public LeetCode GraphQL API and upserts them
into the local `leetcode_problems` SQLite table.

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

import aiohttp
import aiosqlite

# ── Ensure project root is on sys.path so `config` can be imported ───────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import config  # noqa: E402 — must come after path setup

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sync_leetcode")

# ── Constants ────────────────────────────────────────────────────────────────
LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
DB_PATH = config.DATABASE_PATH
BATCH_SIZE = 100          # problems per GraphQL request
MAX_TOTAL = 5000          # safety cap — LeetCode currently has ~3 400 problems

# GraphQL query that returns problem metadata including topic tags.
# `problemsetQuestionList` accepts `limit` and `skip` for pagination.
# We request `questionFrontendId` (the human-visible number), `title`,
# `titleSlug`, `difficulty`, and the nested `topicTags` list.
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
    """
    Fetch a batch of problems from the LeetCode GraphQL API.

    Returns the raw JSON response body.
    """
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
    """Main sync routine: paginate through LeetCode problems and upsert into SQLite."""
    start_time = time.time()
    logger.info("═══════════════════════════════════════════════════")
    logger.info("  LeetCode Metadata Sync — starting")
    logger.info("═══════════════════════════════════════════════════")

    # ── Ensure database & table exist ────────────────────────────────────────
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS leetcode_problems (
            question_id   INTEGER PRIMARY KEY,
            title         TEXT,
            title_slug    TEXT,
            difficulty    TEXT,
            topics        TEXT
        )
    """)
    await conn.commit()

    total_upserted = 0
    skip = 0

    async with aiohttp.ClientSession() as session:
        # First request to discover total problem count
        data = await fetch_problems(session, skip=0, limit=BATCH_SIZE)
        total_available = data["data"]["problemsetQuestionList"]["total"]
        effective_total = min(total_available, MAX_TOTAL)
        logger.info(f"LeetCode reports {total_available} problems — syncing up to {effective_total}")

        # Process first batch
        questions = data["data"]["problemsetQuestionList"]["questions"]
        batch_count = await _upsert_batch(conn, questions)
        total_upserted += batch_count
        skip += len(questions)
        logger.info(f"  Batch 1: upserted {batch_count} problems  (skip=0, limit={BATCH_SIZE})")

        # Continue paginating
        batch_num = 2
        while skip < effective_total:
            data = await fetch_problems(session, skip=skip, limit=BATCH_SIZE)
            questions = data["data"]["problemsetQuestionList"]["questions"]
            if not questions:
                logger.info("  No more problems returned — stopping pagination.")
                break

            batch_count = await _upsert_batch(conn, questions)
            total_upserted += batch_count
            logger.info(
                f"  Batch {batch_num}: upserted {batch_count} problems  "
                f"(skip={skip}, limit={BATCH_SIZE})"
            )
            skip += len(questions)
            batch_num += 1

            # Brief pause to be respectful to LeetCode servers
            await asyncio.sleep(1)

    await conn.close()

    elapsed = time.time() - start_time
    logger.info("───────────────────────────────────────────────────")
    logger.info(f"  Sync complete — {total_upserted} problems upserted in {elapsed:.1f}s")
    logger.info("───────────────────────────────────────────────────")


async def _upsert_batch(conn: aiosqlite.Connection, questions: list) -> int:
    """
    Upsert a list of problem dicts into the `leetcode_problems` table.

    Uses INSERT OR REPLACE so re-running the script safely updates existing rows.
    Returns the number of rows upserted.
    """
    rows = []
    for q in questions:
        try:
            qid = int(q["questionFrontendId"])
        except (ValueError, TypeError):
            continue

        title = q.get("title", "")
        slug = q.get("titleSlug", "")
        difficulty = q.get("difficulty", "")

        # Extract just the tag name strings and store as a JSON array
        topic_tags = q.get("topicTags") or []
        topics_json = json.dumps([tag["name"] for tag in topic_tags])

        rows.append((qid, title, slug, difficulty, topics_json))

    if rows:
        await conn.executemany(
            """
            INSERT OR REPLACE INTO leetcode_problems
                (question_id, title, title_slug, difficulty, topics)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        await conn.commit()

    return len(rows)


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(sync())
