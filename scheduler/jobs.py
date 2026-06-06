"""
Scheduler module for automated market updates.
Sends morning and evening market digests to subscribed users.
"""

import logging
from datetime import time
from zoneinfo import ZoneInfo

from telegram.ext import Application, ContextTypes

from config import settings
from fetchers import fetch_crypto_news, fetch_stocks_news, fetch_forex_news
from ai.llm import summarize_news, analyze_sentiment, format_sentiment_message

logger = logging.getLogger(__name__)

# In-memory store for subscribed chat IDs and their language preference
# In production, use a database
subscribers: dict[int, dict] = {}
# Format: {chat_id: {"language": "en", "markets": ["crypto", "stocks", "forex"]}}


def subscribe_user(chat_id: int, language: str = "en"):
    """Subscribe a user to scheduled updates."""
    if chat_id not in subscribers:
        subscribers[chat_id] = {
            "language": language,
            "markets": ["crypto", "stocks", "forex"],
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


async def send_market_update(context: ContextTypes.DEFAULT_TYPE, period: str = "morning"):
    """
    Send market update to all subscribers.
    Called by the scheduler at configured times.
    """
    if not subscribers:
        logger.info(f"No subscribers for {period} update. Skipping.")
        return

    logger.info(f"Sending {period} market update to {len(subscribers)} subscribers...")

    for chat_id, prefs in subscribers.items():
        try:
            language = prefs["language"]
            markets = prefs["markets"]

            # Build greeting
            if period == "morning":
                greeting = (
                    "☀️ *Good Morning! Here's your market briefing:*\n\n"
                    if language == "en"
                    else "☀️ *Selamat Pagi! Ini ringkasan pasar hari ini:*\n\n"
                )
            else:
                greeting = (
                    "🌙 *Evening Market Wrap-up:*\n\n"
                    if language == "en"
                    else "🌙 *Ringkasan Pasar Sore Ini:*\n\n"
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
                # Send in chunks
                for i in range(0, len(full_message), 4000):
                    chunk = full_message[i:i + 4000]
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=chunk,
                        parse_mode="Markdown",
                    )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=full_message,
                    parse_mode="Markdown",
                )

            logger.info(f"Sent {period} update to chat_id={chat_id}")

        except Exception as e:
            logger.error(f"Failed to send update to chat_id={chat_id}: {e}")


async def morning_update(context: ContextTypes.DEFAULT_TYPE):
    """Morning scheduled job."""
    await send_market_update(context, period="morning")


async def evening_update(context: ContextTypes.DEFAULT_TYPE):
    """Evening scheduled job."""
    await send_market_update(context, period="evening")


def setup_scheduler(app: Application):
    """Set up the scheduled jobs for the bot."""
    tz = ZoneInfo(settings.TIMEZONE)

    # Morning update
    morning_time = time(
        hour=settings.MORNING_HOUR,
        minute=settings.MORNING_MINUTE,
        tzinfo=tz,
    )
    app.job_queue.run_daily(
        morning_update,
        time=morning_time,
        name="morning_market_update",
    )
    logger.info(
        f"Scheduled morning update at {settings.MORNING_HOUR:02d}:{settings.MORNING_MINUTE:02d} {settings.TIMEZONE}"
    )

    # Evening update
    evening_time = time(
        hour=settings.EVENING_HOUR,
        minute=settings.EVENING_MINUTE,
        tzinfo=tz,
    )
    app.job_queue.run_daily(
        evening_update,
        time=evening_time,
        name="evening_market_update",
    )
    logger.info(
        f"Scheduled evening update at {settings.EVENING_HOUR:02d}:{settings.EVENING_MINUTE:02d} {settings.TIMEZONE}"
    )
