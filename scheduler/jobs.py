"""
Scheduler module for automated market updates.
Sends morning and evening market digests, FX signals, session updates,
and weekly analysis to subscribed users.
"""

import logging
from datetime import time
from zoneinfo import ZoneInfo

from telegram.ext import Application, ContextTypes

from config import settings
from fetchers import fetch_crypto_news, fetch_stocks_news, fetch_forex_news
from fetchers.fx_signals import generate_fx_signal, format_signal_message
from fetchers.us_news import get_upcoming_events, get_news_review, get_weekly_analysis
from fetchers.sessions import get_session_update
from ai.llm import summarize_news, analyze_sentiment, format_sentiment_message

logger = logging.getLogger(__name__)

# In-memory store for subscribed chat IDs and their language preference
# In production, use a database
subscribers: dict[int, dict] = {}
# Format: {chat_id: {"language": "en", "markets": [...], "fx_signals": True}}


def subscribe_user(chat_id: int, language: str = "en"):
    """Subscribe a user to scheduled updates."""
    if chat_id not in subscribers:
        subscribers[chat_id] = {
            "language": language,
            "markets": ["crypto", "stocks", "forex"],
            "fx_signals": True,
            "session_updates": True,
        }
    else:
        subscribers[chat_id]["language"] = language


def unsubscribe_user(chat_id: int):
    """Unsubscribe a user from scheduled updates."""
    subscribers.pop(chat_id, None)


def is_subscribed(chat_id: int) -> bool:
    """Check if a user is subscribed."""
    return chat_id in subscribers


def get_user_language(chat_id: int) -> str:
    """Get user's preferred language."""
    return subscribers.get(chat_id, {}).get("language", settings.DEFAULT_LANGUAGE)


def set_user_language(chat_id: int, language: str):
    """Set user's preferred language."""
    if chat_id in subscribers:
        subscribers[chat_id]["language"] = language


# ─────────────────────────────────────────────
# Market Update Jobs (existing)
# ─────────────────────────────────────────────
async def send_market_update(context: ContextTypes.DEFAULT_TYPE, period: str = "morning"):
    """
    Send market update to all subscribers.
    Called by the scheduler at configured times.
    """
    if not subscribers:
        logger.info(f"No subscribers for {period} update. Skipping.")
        return

    logger.info(f"Sending {period} market update to {len(subscribers)} subscribers...")

    for chat_id, prefs in list(subscribers.items()):
        try:
            language = prefs["language"]
            markets = prefs["markets"]

            # Build greeting
            if period == "morning":
                greeting = (
                    "☀️ Good Morning! Here's your market briefing:\n\n"
                    if language == "en"
                    else "☀️ Selamat Pagi! Ini ringkasan pasar hari ini:\n\n"
                )
            else:
                greeting = (
                    "🌙 Evening Market Wrap-up:\n\n"
                    if language == "en"
                    else "🌙 Ringkasan Pasar Sore Ini:\n\n"
                )

            message_parts = [greeting]

            # Fetch and summarize each market
            for market in markets:
                if market == "crypto":
                    data = await fetch_crypto_news(limit=5)
                elif market == "stocks":
                    data = await fetch_stocks_news(limit=5)
                elif market == "forex":
                    data = await fetch_forex_news(limit=5)
                else:
                    continue

                articles = data.get("articles", [])

                # Get summary
                summary = await summarize_news(articles, market, language)
                # Get sentiment
                sentiment = await analyze_sentiment(articles, market, language)
                sentiment_msg = format_sentiment_message(sentiment, market)

                message_parts.append(f"{summary}\n\n{sentiment_msg}\n")

            # Send the full message
            full_message = "\n".join(message_parts)

            # Telegram has 4096 char limit, split if needed
            if len(full_message) > 4000:
                chunks = _split_message(full_message)
                for chunk in chunks:
                    await context.bot.send_message(chat_id=chat_id, text=chunk)
            else:
                await context.bot.send_message(chat_id=chat_id, text=full_message)

            logger.info(f"Sent {period} update to chat_id={chat_id}")

        except Exception as e:
            logger.error(f"Failed to send update to chat_id={chat_id}: {e}")


# ─────────────────────────────────────────────
# FX Signal Job (NEW)
# ─────────────────────────────────────────────
async def send_daily_fx_signal(context: ContextTypes.DEFAULT_TYPE):
    """
    Send daily FX signal to all subscribers.
    Scheduled for market open times.
    """
    if not subscribers:
        logger.info("No subscribers for FX signal. Skipping.")
        return

    logger.info(f"Generating daily FX signal for {len(subscribers)} subscribers...")

    # Fetch forex news context once
    forex_data = await fetch_forex_news(limit=5)
    news_context = "\n".join(
        f"- {a['title']}: {a.get('description', '')}"
        for a in forex_data.get("articles", [])
    )

    # Generate signal once (same signal for all users)
    signal = await generate_fx_signal(news_context=news_context, language="en")

    for chat_id, prefs in list(subscribers.items()):
        if not prefs.get("fx_signals", True):
            continue

        try:
            language = prefs["language"]

            # If user wants Indonesian, regenerate with ID language
            if language == "id":
                signal_id = await generate_fx_signal(news_context=news_context, language="id")
                message = format_signal_message(signal_id)
            else:
                message = format_signal_message(signal)

            await context.bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Sent FX signal to chat_id={chat_id}")

        except Exception as e:
            logger.error(f"Failed to send FX signal to chat_id={chat_id}: {e}")


# ─────────────────────────────────────────────
# Session Update Jobs (NEW)
# ─────────────────────────────────────────────
async def send_session_update(context: ContextTypes.DEFAULT_TYPE):
    """
    Send session update based on current time.
    Auto-detects which session is opening.
    """
    if not subscribers:
        logger.info("No subscribers for session update. Skipping.")
        return

    # Determine which session based on the job data
    session = context.job.data if context.job.data else "london"

    logger.info(f"Sending {session} session update to subscribers...")

    for chat_id, prefs in list(subscribers.items()):
        if not prefs.get("session_updates", True):
            continue

        try:
            language = prefs["language"]
            update_msg = await get_session_update(session, language=language)

            if len(update_msg) > 4000:
                chunks = _split_message(update_msg)
                for chunk in chunks:
                    await context.bot.send_message(chat_id=chat_id, text=chunk)
            else:
                await context.bot.send_message(chat_id=chat_id, text=update_msg)

            logger.info(f"Sent {session} session update to chat_id={chat_id}")

        except Exception as e:
            logger.error(f"Failed to send session update to chat_id={chat_id}: {e}")


# ─────────────────────────────────────────────
# US News Alert Job (NEW)
# ─────────────────────────────────────────────
async def send_us_news_alert(context: ContextTypes.DEFAULT_TYPE):
    """
    Send US economic news alert to subscribers.
    Scheduled before major data releases.
    """
    if not subscribers:
        logger.info("No subscribers for US news alert. Skipping.")
        return

    logger.info(f"Sending US news alert to {len(subscribers)} subscribers...")

    for chat_id, prefs in list(subscribers.items()):
        try:
            language = prefs["language"]
            alert = await get_upcoming_events(language=language)

            if len(alert) > 4000:
                chunks = _split_message(alert)
                for chunk in chunks:
                    await context.bot.send_message(chat_id=chat_id, text=chunk)
            else:
                await context.bot.send_message(chat_id=chat_id, text=alert)

            logger.info(f"Sent US news alert to chat_id={chat_id}")

        except Exception as e:
            logger.error(f"Failed to send US news alert to chat_id={chat_id}: {e}")


# ─────────────────────────────────────────────
# Weekly Analysis Job (NEW)
# ─────────────────────────────────────────────
async def send_weekly_analysis(context: ContextTypes.DEFAULT_TYPE):
    """
    Send weekly market analysis to subscribers.
    Scheduled for Sunday evening / Monday morning.
    """
    if not subscribers:
        logger.info("No subscribers for weekly analysis. Skipping.")
        return

    logger.info(f"Sending weekly analysis to {len(subscribers)} subscribers...")

    for chat_id, prefs in list(subscribers.items()):
        try:
            language = prefs["language"]
            analysis = await get_weekly_analysis(language=language)

            if len(analysis) > 4000:
                chunks = _split_message(analysis)
                for chunk in chunks:
                    await context.bot.send_message(chat_id=chat_id, text=chunk)
            else:
                await context.bot.send_message(chat_id=chat_id, text=analysis)

            logger.info(f"Sent weekly analysis to chat_id={chat_id}")

        except Exception as e:
            logger.error(f"Failed to send weekly analysis to chat_id={chat_id}: {e}")


# ─────────────────────────────────────────────
# Scheduled job wrappers
# ─────────────────────────────────────────────
async def morning_update(context: ContextTypes.DEFAULT_TYPE):
    """Morning scheduled job."""
    await send_market_update(context, period="morning")


async def evening_update(context: ContextTypes.DEFAULT_TYPE):
    """Evening scheduled job."""
    await send_market_update(context, period="evening")


# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────
def _split_message(text: str, max_length: int = 4000) -> list[str]:
    """Split a long message into chunks."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        split_point = text.rfind("\n", 0, max_length)
        if split_point == -1:
            split_point = max_length
        chunks.append(text[:split_point])
        text = text[split_point:].lstrip("\n")

    return chunks


# ─────────────────────────────────────────────
# Setup all scheduled jobs
# ─────────────────────────────────────────────
def setup_scheduler(app: Application):
    """Set up all scheduled jobs for the bot."""
    tz = ZoneInfo(settings.TIMEZONE)

    # ── Morning Market Update (07:00 WIB) ──
    morning_time = time(hour=7, minute=0, tzinfo=tz)
    app.job_queue.run_daily(
        morning_update,
        time=morning_time,
        name="morning_market_update",
    )
    logger.info("Scheduled: Morning market update at 07:00 WIB")

    # ── Evening Market Update (18:00 WIB) ──
    evening_time = time(hour=18, minute=0, tzinfo=tz)
    app.job_queue.run_daily(
        evening_update,
        time=evening_time,
        name="evening_market_update",
    )
    logger.info("Scheduled: Evening market update at 18:00 WIB")

    # ── Daily FX Signal (08:00 WIB - after Asian session open) ──
    fx_signal_time = time(hour=8, minute=0, tzinfo=tz)
    app.job_queue.run_daily(
        send_daily_fx_signal,
        time=fx_signal_time,
        name="daily_fx_signal",
    )
    logger.info("Scheduled: Daily FX signal at 08:00 WIB")

    # ── Session Updates ──
    # Asian session open (07:00 WIB = 00:00 UTC)
    asian_time = time(hour=7, minute=15, tzinfo=tz)
    app.job_queue.run_daily(
        send_session_update,
        time=asian_time,
        name="asian_session_update",
        data="asian",
    )
    logger.info("Scheduled: Asian session update at 07:15 WIB")

    # London session open (14:00 WIB = 07:00 UTC)
    london_time = time(hour=14, minute=0, tzinfo=tz)
    app.job_queue.run_daily(
        send_session_update,
        time=london_time,
        name="london_session_update",
        data="london",
    )
    logger.info("Scheduled: London session update at 14:00 WIB")

    # New York session open (19:30 WIB = 12:30 UTC)
    ny_time = time(hour=19, minute=30, tzinfo=tz)
    app.job_queue.run_daily(
        send_session_update,
        time=ny_time,
        name="ny_session_update",
        data="newyork",
    )
    logger.info("Scheduled: New York session update at 19:30 WIB")

    # ── US News Alert (20:00 WIB - before major US data at 19:30-21:30 WIB) ──
    us_news_time = time(hour=20, minute=0, tzinfo=tz)
    app.job_queue.run_daily(
        send_us_news_alert,
        time=us_news_time,
        name="us_news_alert",
    )
    logger.info("Scheduled: US news alert at 20:00 WIB")

    # ── Weekly Analysis (Sunday 20:00 WIB) ──
    weekly_time = time(hour=20, minute=0, tzinfo=tz)
    app.job_queue.run_daily(
        send_weekly_analysis,
        time=weekly_time,
        days=(6,),  # Sunday only
        name="weekly_analysis",
    )
    logger.info("Scheduled: Weekly analysis on Sunday at 20:00 WIB")
