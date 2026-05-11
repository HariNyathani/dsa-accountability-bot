"""
DSA Progress Accountability Bot — Multi-User Entry Point

Supports multiple users with per-user configuration, reminders,
leaderboard, and weekly summaries.
"""

import logging
import os
import sys
import re

import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import pytz

import config
from db import database
from handlers.message_handler import handle_message
from handlers.reminder_handler import check_all_reminders
from handlers.summary_handler import (
    generate_weekly_summary,
    generate_weekly_summary_all,
    get_status_report,
    get_topic_summary,
    _build_summary_embed,
)
from handlers.leaderboard_handler import build_leaderboard, get_missed_today_report
from services.export_service import export_progress_csv, export_daily_status_csv
from services.ai_service import generate_insights
from utils.time_utils import today_str
from utils.streak_utils import recalculate_streak


# ── Logging ──────────────────────────────────────────────────────────────────

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-30s │ %(levelname)-7s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("dsa_bot")


# ── Bot setup ────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
scheduler = AsyncIOScheduler(timezone=pytz.timezone(config.DEFAULT_TIMEZONE))


# ── Helpers ──────────────────────────────────────────────────────────────────

def _split_message(text: str, limit: int = 1990) -> list[str]:
    """Split a long message into chunks that fit within Discord's character limit.
    Breaks at newlines to preserve formatting."""
    if len(text) <= limit:
        return [text]

    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # Find the last newline within the limit
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            # No newline found — hard split at limit
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks

async def _require_registered(ctx: commands.Context) -> bool:
    """Check if user is registered. Sends guidance if not. Returns True if registered."""
    if await database.is_registered(ctx.author.id):
        return True
    await ctx.send(
        "❌ You're not registered yet!\n"
        "Run `!register` to start tracking your DSA progress."
    )
    return False


def _is_admin(ctx: commands.Context) -> bool:
    """Check if user is the bot owner or has admin perms."""
    if config.BOT_OWNER_ID and ctx.author.id == config.BOT_OWNER_ID:
        return True
    if ctx.author.guild_permissions.administrator:
        return True
    return False


def _parse_channel_id(text: str) -> int:
    """Parse a channel mention or raw ID into an integer."""
    match = re.match(r"<#(\d+)>", text)
    if match:
        return int(match.group(1))
    try:
        return int(text)
    except ValueError:
        return 0


def _parse_user_mention(text: str) -> int:
    """Parse a user mention like <@123> or <@!123> into an integer ID. Returns 0 on failure."""
    match = re.match(r"<@!?(\d+)>", text)
    if match:
        return int(match.group(1))
    try:
        return int(text)
    except ValueError:
        return 0


async def _resolve_target_user(ctx: commands.Context, args: list[str]):
    """
    Check if the last arg is a @user mention. If so, verify admin perms.
    Returns (target_user_id, remaining_args, error_msg).
    error_msg is set if permission denied.
    """
    if not args:
        return ctx.author.id, args, None

    last = args[-1]
    mentioned_id = _parse_user_mention(last)

    if not mentioned_id or mentioned_id == ctx.author.id:
        return ctx.author.id, args, None

    # A different user was mentioned — require admin
    if not _is_admin(ctx):
        return None, args, "❌ Only the bot owner can use commands on other users."

    return mentioned_id, args[:-1], None


# ── Events ───────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    """Called when the bot successfully connects to Discord."""
    logger.info(f"Bot connected as {bot.user} (ID: {bot.user.id})")

    # Initialise database
    await database.init_db()

    # Start scheduler
    _setup_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")

    users = await database.get_all_active_users()
    logger.info(f"Tracking {len(users)} registered user(s).")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="DSA progress 📚",
        )
    )


@bot.event
async def on_message(message: discord.Message):
    """Route every message through the handler, then process commands."""
    await handle_message(message, bot)
    await bot.process_commands(message)


# ── Scheduler ────────────────────────────────────────────────────────────────

def _setup_scheduler():
    """Register scheduler jobs."""
    # Minutely ticker for per-user reminders
    scheduler.add_job(
        _run_reminders,
        IntervalTrigger(minutes=1),
        id="reminder_ticker",
        replace_existing=True,
    )

    # Weekly summary — every Monday at 9:00 AM (default tz)
    tz = pytz.timezone(config.DEFAULT_TIMEZONE)
    scheduler.add_job(
        _run_weekly_summary,
        CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=tz),
        id="weekly_summary",
        replace_existing=True,
    )

    logger.info("Scheduler configured: minutely reminders + weekly summary.")


async def _run_reminders():
    await check_all_reminders(bot)

async def _run_weekly_summary():
    await generate_weekly_summary_all(bot, send=True)


# ── Registration Commands ────────────────────────────────────────────────────

@bot.command(name="register")
async def cmd_register(ctx: commands.Context, *, mention: str = ""):
    """Register yourself (or @user if admin). Usage: !register [@user]"""
    target_id, _, err = await _resolve_target_user(ctx, mention.split() if mention else [])
    if err:
        await ctx.send(err)
        return
    if not target_id:
        target_id = ctx.author.id

    is_admin_action = target_id != ctx.author.id
    username = str(ctx.author)
    if is_admin_action:
        member = ctx.guild.get_member(target_id) if ctx.guild else None
        username = str(member) if member else str(target_id)

    is_new = await database.register_user(
        target_id, username, timezone=config.DEFAULT_TIMEZONE
    )
    if is_admin_action:
        status = "registered" if is_new else "reactivated"
        await ctx.send(f"✅ {status.capitalize()} <@{target_id}> for DSA tracking.")
        return
    if is_new:
        embed = discord.Embed(
            title="🎉 Welcome to DSA Accountability!",
            description="You're now registered. Set up your tracking:",
            color=0x2ECC71,
        )
        embed.add_field(name="Step 1", value="`!setchannel #your-dsa-channel`", inline=False)
        embed.add_field(name="Step 2", value="`!setemail your@email.com` (optional)", inline=False)
        embed.add_field(name="Step 3", value="Start posting in your DSA channel! 🔥", inline=False)
        embed.add_field(name="Other Settings", value=(
            "`!setdeadline HH:MM` — set deadline\n"
            "`!setreminders HH:MM,HH:MM,HH:MM` — warn,final,email\n"
            "`!settimezone Asia/Kolkata` — set timezone\n"
            "`!mysettings` — view your config"
        ), inline=False)
    else:
        embed = discord.Embed(
            title="👋 Welcome back!",
            description="Your account has been reactivated.",
            color=0x3498DB,
        )
    await ctx.send(embed=embed)


@bot.command(name="setup")
async def cmd_setup(ctx: commands.Context):
    """Alias for !register."""
    await cmd_register(ctx)


@bot.command(name="unregister")
async def cmd_unregister(ctx: commands.Context):
    """Deactivate your tracking (data is preserved)."""
    if not await _require_registered(ctx):
        return
    await database.unregister_user(ctx.author.id)
    await ctx.send("👋 You've been unregistered. Your data is preserved.\nRun `!register` anytime to come back.")


# ── Settings Commands ────────────────────────────────────────────────────────

@bot.command(name="setchannel")
async def cmd_setchannel(ctx: commands.Context, *, args: str = ""):
    """Set DSA channel. Usage: !setchannel #channel [@user]"""
    parts = args.split() if args else []
    target_id, remaining, err = await _resolve_target_user(ctx, parts)
    if err:
        await ctx.send(err)
        return

    # Ensure target is registered
    if not await database.is_registered(target_id):
        if target_id == ctx.author.id:
            await ctx.send("❌ You're not registered yet! Run `!register` first.")
        else:
            await ctx.send(f"❌ <@{target_id}> is not registered. Use `!register @user` first.")
        return

    channel_ref = remaining[0] if remaining else ""
    if not channel_ref:
        settings = await database.get_user_settings(target_id)
        ch = settings.get("tracked_channel_id", 0) if settings else 0
        await ctx.send(f"Current channel: {'<#' + str(ch) + '>' if ch else 'Not set'}\nUsage: `!setchannel #channel`")
        return
    cid = _parse_channel_id(channel_ref)
    if not cid:
        await ctx.send("❌ Invalid channel. Use `!setchannel #channel-name` or `!setchannel 123456789`")
        return
    await database.update_user_settings(target_id, tracked_channel_id=cid)
    label = f"for <@{target_id}>" if target_id != ctx.author.id else ""
    await ctx.send(f"✅ Tracking channel set to <#{cid}> {label}".strip())


@bot.command(name="setemail")
async def cmd_setemail(ctx: commands.Context, *, args: str = ""):
    """Set reminder email. Usage: !setemail email [@user]"""
    parts = args.split() if args else []
    target_id, remaining, err = await _resolve_target_user(ctx, parts)
    if err:
        await ctx.send(err)
        return

    if not await database.is_registered(target_id):
        if target_id == ctx.author.id:
            await ctx.send("❌ You're not registered yet! Run `!register` first.")
        else:
            await ctx.send(f"❌ <@{target_id}> is not registered. Use `!register @user` first.")
        return

    email = remaining[0] if remaining else ""
    if not email:
        user = await database.get_user(target_id)
        current = user.get("email", "") if user else ""
        await ctx.send(f"Current email: `{current or 'Not set'}`\nUsage: `!setemail you@email.com`")
        return
    if "@" not in email or "." not in email:
        await ctx.send("❌ That doesn't look like a valid email.")
        return
    await database.update_user_email(target_id, email)
    label = f" for <@{target_id}>" if target_id != ctx.author.id else ""
    await ctx.send(f"✅ Reminder email set to `{email}`{label}")


@bot.command(name="setdeadline")
async def cmd_setdeadline(ctx: commands.Context, *, args: str = ""):
    """Set deadline time. Usage: !setdeadline HH:MM [@user]"""
    parts = args.split() if args else []
    target_id, remaining, err = await _resolve_target_user(ctx, parts)
    if err:
        await ctx.send(err)
        return

    if not await database.is_registered(target_id):
        if target_id == ctx.author.id:
            await ctx.send("❌ You're not registered yet! Run `!register` first.")
        else:
            await ctx.send(f"❌ <@{target_id}> is not registered. Use `!register @user` first.")
        return

    time_str = remaining[0] if remaining else ""
    if not time_str:
        s = await database.get_user_settings(target_id)
        h, m = (s["deadline_hour"], s["deadline_minute"]) if s else (23, 0)
        await ctx.send(f"Current deadline: `{h:02d}:{m:02d}`\nUsage: `!setdeadline HH:MM`")
        return
    tparts = time_str.split(":")
    try:
        h, m = int(tparts[0]), int(tparts[1]) if len(tparts) > 1 else 0
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except (ValueError, IndexError):
        await ctx.send("❌ Invalid format. Use `HH:MM` (e.g. `23:00`)")
        return
    await database.update_user_settings(target_id, deadline_hour=h, deadline_minute=m)
    label = f" for <@{target_id}>" if target_id != ctx.author.id else ""
    await ctx.send(f"✅ Deadline set to `{h:02d}:{m:02d}`{label}")


@bot.command(name="setreminders")
async def cmd_setreminders(ctx: commands.Context, *, raw_args: str = ""):
    """Set reminder times. Usage: !setreminders HH:MM,HH:MM,HH:MM [@user]"""
    tokens = raw_args.split() if raw_args else []
    target_id, remaining, err = await _resolve_target_user(ctx, tokens)
    if err:
        await ctx.send(err)
        return

    if not await database.is_registered(target_id):
        if target_id == ctx.author.id:
            await ctx.send("❌ You're not registered yet! Run `!register` first.")
        else:
            await ctx.send(f"❌ <@{target_id}> is not registered. Use `!register @user` first.")
        return

    times = " ".join(remaining).strip()
    if not times:
        s = await database.get_user_settings(target_id)
        if s:
            await ctx.send(
                f"Current reminders:\n"
                f"  ⏰ Warning: `{s['warn_hour']:02d}:{s['warn_minute']:02d}`\n"
                f"  🚨 Final: `{s['final_hour']:02d}:{s['final_minute']:02d}`\n"
                f"  📧 Email: `{s['email_hour']:02d}:{s['email_minute']:02d}`\n"
                f"Usage: `!setreminders HH:MM,HH:MM,HH:MM`"
            )
        return
    parts = [t.strip() for t in times.split(",")]
    if len(parts) != 3:
        await ctx.send("❌ Provide exactly 3 times: `!setreminders warn,final,email`\nExample: `!setreminders 22:00,23:00,23:30`")
        return
    try:
        parsed = []
        for p in parts:
            hm = p.split(":")
            h, m = int(hm[0]), int(hm[1]) if len(hm) > 1 else 0
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
            parsed.append((h, m))
    except (ValueError, IndexError):
        await ctx.send("❌ Invalid format. Use `HH:MM,HH:MM,HH:MM`")
        return
    await database.update_user_settings(
        target_id,
        warn_hour=parsed[0][0], warn_minute=parsed[0][1],
        final_hour=parsed[1][0], final_minute=parsed[1][1],
        email_hour=parsed[2][0], email_minute=parsed[2][1],
    )
    label = f" for <@{target_id}>" if target_id != ctx.author.id else ""
    await ctx.send(f"✅ Reminders set: ⏰ `{parts[0]}` | 🚨 `{parts[1]}` | 📧 `{parts[2]}`{label}")


@bot.command(name="settimezone")
async def cmd_settimezone(ctx: commands.Context, tz: str = ""):
    """Set your timezone. Usage: !settimezone Asia/Kolkata"""
    if not await _require_registered(ctx):
        return
    if not tz:
        user = await database.get_user(ctx.author.id)
        current = user.get("timezone", config.DEFAULT_TIMEZONE) if user else config.DEFAULT_TIMEZONE
        await ctx.send(f"Current timezone: `{current}`\nUsage: `!settimezone Asia/Kolkata`")
        return
    try:
        pytz.timezone(tz)
    except pytz.UnknownTimeZoneError:
        await ctx.send(f"❌ Unknown timezone `{tz}`.\nExamples: `Asia/Kolkata`, `US/Eastern`, `Europe/London`")
        return
    conn = await database.get_connection()
    try:
        await conn.execute("UPDATE users SET timezone = ? WHERE user_id = ?", (tz, ctx.author.id))
        await conn.commit()
    finally:
        await conn.close()
    await ctx.send(f"✅ Timezone set to `{tz}`")


@bot.command(name="mysettings")
async def cmd_mysettings(ctx: commands.Context, *, mention: str = ""):
    """View bot configuration. Admin: !mysettings @user"""
    target_id, _, err = await _resolve_target_user(ctx, mention.split() if mention else [])
    if err:
        await ctx.send(err)
        return

    if not await database.is_registered(target_id):
        if target_id == ctx.author.id:
            await ctx.send("❌ You're not registered yet! Run `!register` first.")
        else:
            await ctx.send(f"❌ <@{target_id}> is not registered.")
        return

    user = await database.get_user_with_settings(target_id)
    if not user:
        await ctx.send("❌ Settings not found. Try `!register` first.")
        return
    ch = user.get("tracked_channel_id", 0)
    title = f"⚙️ Settings for <@{target_id}>" if target_id != ctx.author.id else "⚙️ Your Settings"
    embed = discord.Embed(title=title, color=0x3498DB)
    embed.add_field(name="📺 Channel", value=f"<#{ch}>" if ch else "Not set", inline=True)
    embed.add_field(name="🌍 Timezone", value=user.get("timezone", "Not set"), inline=True)
    embed.add_field(name="📧 Email", value=user.get("email") or "Not set", inline=True)
    embed.add_field(name="⏰ Deadline", value=f"`{user.get('deadline_hour', 23):02d}:{user.get('deadline_minute', 0):02d}`", inline=True)
    embed.add_field(name="⏰ Warn", value=f"`{user.get('warn_hour', 22):02d}:{user.get('warn_minute', 0):02d}`", inline=True)
    embed.add_field(name="🚨 Final", value=f"`{user.get('final_hour', 23):02d}:{user.get('final_minute', 0):02d}`", inline=True)
    embed.add_field(name="📧 Email Escalation", value=f"`{user.get('email_hour', 23):02d}:{user.get('email_minute', 30):02d}`", inline=True)
    embed.set_footer(text="Use !help to see all commands")
    await ctx.send(embed=embed)


@bot.command(name="resetconfig")
async def cmd_resetconfig(ctx: commands.Context):
    """Reset your settings to defaults."""
    if not await _require_registered(ctx):
        return
    await database.reset_user_settings(ctx.author.id)
    await ctx.send("✅ Settings reset to defaults. Run `!mysettings` to view.")


# ── User Tracking Commands ───────────────────────────────────────────────────

@bot.command(name="plan")
async def cmd_plan(ctx: commands.Context, *, text: str = ""):
    """Log a planned study message. Usage: !plan <what you plan>"""
    if not await _require_registered(ctx):
        return
    if not text:
        await ctx.send("📋 Usage: `!plan <what you plan to study today>`")
        return
    await ctx.send("📋 Plan recorded for today! Stay focused. 🎯")


@bot.command(name="done")
async def cmd_done(ctx: commands.Context, *, text: str = ""):
    """Log a completed study message. Usage: !done <what you completed>"""
    if not await _require_registered(ctx):
        return
    if not text:
        await ctx.send("✅ Usage: `!done <what you completed today>`")
        return
    await ctx.send("✅ Great job! Progress logged. Keep it up! 🔥")


@bot.command(name="status")
async def cmd_status(ctx: commands.Context):
    """Show your current tracking status."""
    if not await _require_registered(ctx):
        return
    report = await get_status_report(ctx.author.id)
    embed = discord.Embed(title="📊 Your DSA Status", color=0x3498DB)
    embed.add_field(
        name="📅 Today",
        value=f"{'✅ Posted' if report['posted_today'] else '❌ Not posted yet'}\nDate: {report['today']}",
        inline=True,
    )
    embed.add_field(
        name="🔥 Streak",
        value=f"Current: **{report['current_streak']}** days\nLongest: **{report['longest_streak']}** days",
        inline=True,
    )
    embed.add_field(
        name="📈 Overall",
        value=f"Messages: **{report['total_messages']}**\nDays tracked: **{report['total_days_tracked']}**\nConsistency: **{report['consistency']}%**",
        inline=False,
    )
    embed.set_footer(text="DSA Accountability Bot")
    await ctx.send(embed=embed)


@bot.command(name="streak")
async def cmd_streak(ctx: commands.Context):
    """Show your current streak info."""
    if not await _require_registered(ctx):
        return
    streak = await recalculate_streak(ctx.author.id)
    if streak["current_streak"] > 0:
        msg = (
            f"🔥 **Current Streak:** {streak['current_streak']} days\n"
            f"🏆 **Longest Streak:** {streak['longest_streak']} days\n"
            f"📅 **Last Post:** {streak['last_post_date']}\n\n"
        )
        if streak["current_streak"] >= 30:
            msg += "🎉 Amazing! Over a month of consistency!"
        elif streak["current_streak"] >= 7:
            msg += "💪 One week strong! Keep pushing!"
        else:
            msg += "🌱 Building momentum — don't break the chain!"
    else:
        msg = (
            "😔 **Current Streak:** 0 days\n"
            f"🏆 **Longest Streak:** {streak['longest_streak']} days\n\n"
            "Post your DSA progress to start a new streak! 🚀"
        )
    await ctx.send(msg)


@bot.command(name="weekly")
async def cmd_weekly(ctx: commands.Context):
    """Generate and display your weekly summary."""
    if not await _require_registered(ctx):
        return
    await ctx.send("📊 Generating weekly summary...")
    summary = await generate_weekly_summary(bot, user_id=ctx.author.id, send=False)
    if not summary:
        await ctx.send("❌ Could not generate summary.")
        return
    embed = _build_summary_embed(summary)
    await ctx.send(embed=embed)


@bot.command(name="topics")
async def cmd_topics(ctx: commands.Context):
    """Show topic frequency analysis."""
    if not await _require_registered(ctx):
        return
    topic_data = await get_topic_summary(ctx.author.id)
    if not topic_data["frequency"]:
        await ctx.send("📚 No topics tracked yet. Start posting to see analysis!")
        return
    embed = discord.Embed(title="📚 DSA Topic Analysis", color=0x9B59B6)
    embed.add_field(
        name="📊 Overview",
        value=f"Total mentions: **{topic_data['total_topics_mentioned']}**\nUnique topics: **{topic_data['unique_topics']}**",
        inline=False,
    )
    topics_text = "\n".join(
        f"{'🥇' if i == 0 else '🥈' if i == 1 else '🥉' if i == 2 else '•'} "
        f"**{topic}** — {count} mention{'s' if count > 1 else ''}"
        for i, (topic, count) in enumerate(topic_data["frequency"][:10])
    )
    embed.add_field(name="🏅 Topic Ranking", value=topics_text, inline=False)
    embed.set_footer(text="DSA Accountability Bot • Track what you study!")
    await ctx.send(embed=embed)


@bot.command(name="exportcsv")
async def cmd_exportcsv(ctx: commands.Context):
    """Export your progress logs to CSV."""
    if not await _require_registered(ctx):
        return
    await ctx.send("📁 Generating CSV export...")
    filepath = await export_progress_csv(ctx.author.id)
    status_path = await export_daily_status_csv(ctx.author.id)
    try:
        await ctx.send(
            "✅ Export complete!",
            files=[discord.File(filepath), discord.File(status_path)],
        )
    except Exception as e:
        await ctx.send(f"❌ Error sending files: {e}")


# ── Leaderboard ──────────────────────────────────────────────────────────────

@bot.command(name="leaderboard", aliases=["lb"])
async def cmd_leaderboard(ctx: commands.Context, sort_by: str = "streak"):
    """Show the group leaderboard. Usage: !leaderboard [streak|consistency|posts|longest|days]"""
    valid = ["streak", "consistency", "posts", "longest", "days"]
    if sort_by not in valid:
        sort_by = "streak"
    embed = await build_leaderboard(sort_by)
    await ctx.send(embed=embed)


# ── AI Insights ──────────────────────────────────────────────────────────────

@bot.command(name="insights", aliases=["analyze", "review"])
async def cmd_insights(ctx: commands.Context):
    """Get AI-powered study insights (requires Gemini key)."""
    if not await _require_registered(ctx):
        return
    if not config.GEMINI_API_KEY:
        await ctx.send("🧠 AI insights require a Gemini API key.\nAsk the bot admin to configure one.")
        return
    await ctx.send("🧠 Generating AI insights...")
    from db import database as db
    logs = await db.get_progress_logs(ctx.author.id)
    streak = await db.get_streak(ctx.author.id)
    topics = await get_topic_summary(ctx.author.id)
    analysis = await generate_insights(logs, streak, topics)
    if analysis:
        header = "🧠 **AI Study Insights**\n\nHere is your personalized DSA study coaching report!\n\n"
        full_text = header + analysis

        # Discord has a 2000-char limit per message — split into chunks
        chunks = _split_message(full_text, limit=1990)
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send("❌ Could not generate insights. Not enough data or AI unavailable.")


# ── Admin Commands ───────────────────────────────────────────────────────────

@bot.command(name="admin")
async def cmd_admin(ctx: commands.Context, action: str = "", *, args: str = ""):
    """Admin commands. Usage: !admin [users|missed|forcesummary]"""
    if not _is_admin(ctx):
        await ctx.send("❌ Admin only.")
        return

    if action == "users":
        users = await database.get_all_active_users()
        if not users:
            await ctx.send("No registered users.")
            return
        lines = [f"• **{u.get('discord_username', 'Unknown')}** (ID: `{u['user_id']}`)" for u in users]
        embed = discord.Embed(title="👥 Registered Users", description="\n".join(lines), color=0x3498DB)
        embed.set_footer(text=f"{len(users)} user(s)")
        await ctx.send(embed=embed)

    elif action == "missed":
        missed = await get_missed_today_report()
        if not missed:
            await ctx.send("✅ Everyone has posted today!")
            return
        lines = [f"• **{u.get('discord_username', 'Unknown')}**" for u in missed]
        embed = discord.Embed(title="😔 Missed Today", description="\n".join(lines), color=0xE74C3C)
        await ctx.send(embed=embed)

    elif action == "forcesummary":
        await ctx.send("📊 Forcing weekly summary for all users...")
        await generate_weekly_summary_all(bot, send=True)
        await ctx.send("✅ Done!")

    else:
        await ctx.send("Usage: `!admin users` | `!admin missed` | `!admin forcesummary`")


# ── Help ─────────────────────────────────────────────────────────────────────

@bot.command(name="help")
async def cmd_help(ctx: commands.Context, command_name: str = ""):
    """Show all available commands."""
    cmd_name = command_name.lower().strip()
    
    if cmd_name == "qdone":
        embed = discord.Embed(title="📖 Command Help: !qdone", color=0x3498DB)
        embed.description = (
            "**`!qdone`** is the power user command for logging multiple topics with full flexibility.\n\n"
            "**Syntax:** `!qdone <topic> [count] [diff]`\n\n"
            "• Supports natural language (e.g., 'arrays' or 'array')\n"
            "• Flexible ordering (e.g., `arrays 2 hard` or `arrays hard 2`)\n"
            "• Batch logging (separate by commas)\n\n"
            "**Examples:**\n"
            "`!qdone arrays` (Logs 1 array question)\n"
            "`!qdone dp 3` (Logs 3 DP questions)\n"
            "`!qdone graphs 2 hard, trees 1` (Logs 2 hard graph questions and 1 tree question)"
        )
        await ctx.send(embed=embed)
        return
        
    if cmd_name == "qn":
        embed = discord.Embed(title="📖 Command Help: !qn", color=0x3498DB)
        embed.description = (
            "**`!qn`** is for lightning-fast logging using the official LeetCode Question ID.\n\n"
            "**Syntax:** `!qn <id>`\n\n"
            "It instantly fetches the official LeetCode title, difficulty, and auto-tags it.\n\n"
            "**Examples:**\n"
            "`!qn 1` (Logs Two Sum)\n"
            "`!qn 73` (Logs Set Matrix Zeroes)"
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="🤖 DSA Accountability Bot — Commands",
        description="💡 Tip: Type `!help <command>` for detailed examples (e.g., `!help qdone`)",
        color=0x2ECC71
    )

    setup = (
        "**!register** — Join DSA tracking\n"
        "**!unregister** — Leave tracking\n"
        "**!setchannel** `#channel` — Set your DSA channel\n"
        "**!setemail** `email` — Set reminder email\n"
        "**!setdeadline** `HH:MM` — Set deadline\n"
        "**!setreminders** `HH:MM,HH:MM,HH:MM` — Set reminders\n"
        "**!settimezone** `tz` — Set timezone\n"
        "**!mysettings** — View your config\n"
        "**!resetconfig** — Reset to defaults"
    )
    embed.add_field(name="⚙️ Setup", value=setup, inline=False)

    tracking = (
        "**!plan** `text` — Log study plan\n"
        "**!done** `text` — Log completion\n"
        "**!qdone** `<topic> [count] [diff]` — Log topics (e.g., arrays 2 hard)\n"
        "**!qn** `<id>` — Log by LeetCode ID (e.g., 73)\n"
        "**!status** — Today's status\n"
        "**!streak** — Streak info\n"
        "**!weekly** — Weekly summary\n"
        "**!topics** — Topic analysis\n"
        "**!exportcsv** — Export logs\n"
        "**!insights** — AI analysis (Gemini)"
    )
    embed.add_field(name="📊 Tracking", value=tracking, inline=False)

    group = "**!leaderboard** `[streak|consistency|posts]` — Group rankings"
    embed.add_field(name="🏆 Group", value=group, inline=False)

    if _is_admin(ctx):
        admin_text = (
            "Append `@user` to configure others:\n"
            "`!register @user` · `!setchannel #ch @user`\n"
            "`!setemail email @user` · `!setdeadline HH:MM @user`\n"
            "`!setreminders ... @user` · `!mysettings @user`\n"
            "`!admin users` · `!admin missed` · `!admin forcesummary`"
        )
        if config.BOT_OWNER_ID and ctx.author.id == config.BOT_OWNER_ID:
            admin_text += "\n\n**Owner Suite:**\n`!qpurge @user` — Delete all user progress\n`!qundo @user` — Delete latest entry"
        embed.add_field(name="🔐 Admin", value=admin_text, inline=False)

    embed.set_footer(text="Post daily in your DSA channel to stay accountable! 💪")
    await ctx.send(embed=embed)


# ── Error handling ───────────────────────────────────────────────────────────

@bot.event
async def on_command_error(ctx: commands.Context, error):
    """Global command error handler."""
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: `{error.param.name}`")
        return
    logger.error(f"Command error in {ctx.command}: {error}", exc_info=True)
    await ctx.send(f"❌ An error occurred: {error}")


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    """Start the bot."""
    token = config.DISCORD_BOT_TOKEN
    if not token or token == "your_discord_bot_token_here":
        logger.error(
            "DISCORD_BOT_TOKEN not set! "
            "Copy .env.example to .env and fill in your token."
        )
        sys.exit(1)

    logger.info("Starting DSA Accountability Bot (multi-user mode)...")
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
