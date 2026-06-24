"""
ui/confidence_view.py — SRS Confidence Rating UI

Provides a discord.ui.Select dropdown that the user fills in after logging a
problem.  One ConfidenceView is created per resolved LeetCode problem so batch
logs (`!qdone 73, 75`) each get their own rating prompt.

Design decisions:
  - Pure in-memory: the view holds the problem_id and user_id.  The revision_bank
    row is written exactly once — when the user selects a value, OR when the 60-
    second timeout fires and defaults to 3 (Okay).
  - Error-surfacing: if the DB write fails the prompt message is updated with a
    clear ❌ failure notice so the user knows to retry (no silent false-positives).
  - Thread-safe: view.stop() is called before any DB write so rapid double-clicks
    cannot trigger two concurrent writes for the same (user, problem) pair.
"""

import logging
from datetime import datetime, timezone, timedelta

import discord

from db import database
from services.progress_service import CONFIDENCE_INTERVAL_DAYS

logger = logging.getLogger("dsa_bot.confidence_view")

# ── Label copy ────────────────────────────────────────────────────────────────

_SCORE_META: dict[int, dict] = {
    1: {"emoji": "🔴", "label": "1 Star — Hard / Blackout",     "desc": "Totally forgot it. Review tomorrow."},
    2: {"emoji": "⚪", "label": "2 Stars — Below Average",       "desc": "Got some of it but struggled."},
    3: {"emoji": "🟡", "label": "3 Stars — Okay / Medium",       "desc": "Solved it with some friction."},
    4: {"emoji": "🟢", "label": "4 Stars — Good / Easy",         "desc": "Solved it cleanly."},
    5: {"emoji": "🟢", "label": "5 Stars — Mastered / Confident","desc": "Could explain it in my sleep."},
}


# ── Select component ──────────────────────────────────────────────────────────

class ConfidenceSelect(discord.ui.Select):
    """A single-choice dropdown listing the five confidence levels."""

    def __init__(self, author_id: int, problem_id: int, user_id: int) -> None:
        self.author_id = author_id
        self.problem_id = problem_id
        self.user_id = user_id

        options = [
            discord.SelectOption(
                label=meta["label"],
                value=str(score),
                emoji=meta["emoji"],
                description=meta["desc"],
            )
            for score, meta in _SCORE_META.items()
        ]

        super().__init__(
            placeholder="⭐ Rate your confidence (1 = Hard, 5 = Mastered)…",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        # Security: only the message author may interact
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ These buttons aren't for you.", ephemeral=True
            )
            return

        score = int(self.values[0])
        # Acknowledge immediately — stops the "thinking…" spinner
        await interaction.response.defer()
        # Delegate to the parent View's resolution handler
        await self.view._resolve(score=score, interaction=interaction)


# ── View ──────────────────────────────────────────────────────────────────────

class ConfidenceView(discord.ui.View):
    """
    Wraps ConfidenceSelect with a 60-second timeout.

    Usage
    -----
    view = ConfidenceView(author_id=..., problem_id=..., user_id=...)
    msg  = await channel.send("Rate your confidence:", view=view)
    view.message = msg        # ← REQUIRED so on_timeout can edit the message
    """

    def __init__(self, author_id: int, problem_id: int, user_id: int) -> None:
        super().__init__(timeout=60)
        self.author_id = author_id
        self.problem_id = problem_id
        self.user_id = user_id
        self.message: discord.Message | None = None   # set by caller after send
        self._resolved = False                        # idempotency guard

        self.add_item(ConfidenceSelect(author_id, problem_id, user_id))

    # ── Internal resolution handler ───────────────────────────────────────────

    async def _resolve(
        self,
        score: int,
        interaction: discord.Interaction | None = None,
        is_timeout: bool = False,
    ) -> None:
        """Write to revision_bank and update the prompt message. Idempotent."""
        if self._resolved:
            return
        self._resolved = True
        self.stop()  # disables all children immediately

        interval = CONFIDENCE_INTERVAL_DAYS[score]
        next_review = (
            datetime.now(timezone.utc) + timedelta(days=interval)
        ).isoformat()

        db_ok = True
        try:
            await database.upsert_revision_bank(
                user_id=self.user_id,
                problem_id=self.problem_id,
                confidence=score,
                next_review_at=next_review,
            )
            logger.info(
                f"[SRS:VIEW] Saved confidence={score} for user={self.user_id} "
                f"problem={self.problem_id} next_review_at={next_review}"
            )
        except Exception as exc:
            db_ok = False
            logger.error(
                f"[SRS:VIEW] upsert_revision_bank failed for user={self.user_id} "
                f"problem={self.problem_id}: {exc}"
            )

        # Build the edit payload
        meta = _SCORE_META[score]
        if not db_ok:
            content = (
                "❌ **Error saving to database.** Please run your log command again."
            )
        elif is_timeout:
            content = (
                f"⏱️ **Confidence auto-saved as** {meta['emoji']} **{meta['label']}** "
                f"(you didn't rate it — defaulting to Okay). "
                f"Review in **{interval} day(s)**."
            )
        else:
            content = (
                f"✅ **Confidence saved:** {meta['emoji']} **{meta['label']}**. "
                f"Next review in **{interval} day(s)**."
            )

        # Edit the original prompt message to show the resolved state
        try:
            if self.message:
                await self.message.edit(content=content, view=None)
        except discord.HTTPException as exc:
            logger.debug(f"[SRS:VIEW] Could not edit confidence message: {exc}")

    # ── Timeout handler ───────────────────────────────────────────────────────

    async def on_timeout(self) -> None:
        """Default to score=3 (Okay) if the user ignores the prompt."""
        await self._resolve(score=3, is_timeout=True)
