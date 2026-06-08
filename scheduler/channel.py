"""
Channel auto-posting module.
Sends scheduled market updates directly to a Telegram Channel.
"""

import logging

from telegram.ext import ContextTypes

from config import settings
from fetchers import fetch_crypto_news, fetch_stocks_news, fetch_forex_news
from fetchers.fx_signals import generate_quantum_signal, format_quantum_signal
from fetchers.us_news import get_upcoming_events, get_news_review, get_weekly_analysis
from fetchers.sessions import get_session_update, get_all_sessions_summary
from ai.llm import summarize_news, analyze_sentiment, format_sentiment_message

logger = logging.getLogger(__name__)


def _get_channel_id() -> str:
    """Get the configured channel ID."""
    return settings.CHANNEL_ID


def _get_channel_language() -> str:
    """Get the configured channel language."""
    return settings.CHANNEL_LANGUAGE


async def _send_to_channel(context: ContextTypes.DEFAULT_TYPE, text: str):
    """
    Send a message to the configured channel.
    Splits long messages automatically.
    """
    channel_id = _get_channel_id()
    if not channel_id:
        logger.debug("No CHANNEL_ID configured. Skipping channel post.")
        return

    try:
        if len(text) > 4000:
            chunks = _split_message(text)
            for chunk in chunks:
                await context.bot.send_message(chat_id=channel_id, text=chunk)
        else:
            await context.bot.send_message(chat_id=channel_id, text=text)

        logger.info(f"Posted to channel: {channel_id}")

    except Exception as e:
        logger.error(f"Failed to post to channel {channel_id}: {e}")


# ─────────────────────────────────────────────
# Channel: Morning Market Briefing
# ─────────────────────────────────────────────
async def channel_morning_update(context: ContextTypes.DEFAULT_TYPE):
    """Post morning market briefing to channel."""
    channel_id = _get_channel_id()
    if not channel_id:
        return

    lang = _get_channel_language()
    logger.info("Posting morning update to channel...")

    greeting = (
        "☀️ MORNING MARKET BRIEFING\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        if lang == "en"
        else "☀️ BRIEFING PASAR PAGI\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    message_parts = [greeting]

    for market in ["crypto", "stocks", "forex"]:
        try:
            if market == "crypto":
                data = await fetch_crypto_news(limit=5)
            elif market == "stocks":
                data = await fetch_stocks_news(limit=5)
            else:
                data = await fetch_forex_news(limit=5)

            articles = data.get("articles", [])
            summary = await summarize_news(articles, market, lang)
            sentiment = await analyze_sentiment(articles, market, lang)
            sentiment_msg = format_sentiment_message(sentiment, market)

            cat_emoji = {"crypto": "🪙", "stocks": "📈", "forex": "💱"}
            message_parts.append(
                f"{cat_emoji.get(market, '📊')} {market.upper()}\n"
                f"{summary}\n\n{sentiment_msg}\n"
            )
        except Exception as e:
            logger.error(f"Error fetching {market} for channel: {e}")

    separator = "\n" + "━" * 20 + "\n\n"
    full_message = separator.join(message_parts)

    await _send_to_channel(context, full_message)


# ─────────────────────────────────────────────
# Channel: Evening Market Wrap
# ─────────────────────────────────────────────
async def channel_evening_update(context: ContextTypes.DEFAULT_TYPE):
    """Post evening market wrap-up to channel."""
    channel_id = _get_channel_id()
    if not channel_id:
        return

    lang = _get_channel_language()
    logger.info("Posting evening update to channel...")

    greeting = (
        "🌙 EVENING MARKET WRAP-UP\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        if lang == "en"
        else "🌙 RINGKASAN PASAR SORE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    message_parts = [greeting]

    for market in ["crypto", "stocks", "forex"]:
        try:
            if market == "crypto":
                data = await fetch_crypto_news(limit=5)
            elif market == "stocks":
                data = await fetch_stocks_news(limit=5)
            else:
                data = await fetch_forex_news(limit=5)

            articles = data.get("articles", [])
            summary = await summarize_news(articles, market, lang)
            sentiment = await analyze_sentiment(articles, market, lang)
            sentiment_msg = format_sentiment_message(sentiment, market)

            cat_emoji = {"crypto": "🪙", "stocks": "📈", "forex": "💱"}
            message_parts.append(
                f"{cat_emoji.get(market, '📊')} {market.upper()}\n"
                f"{summary}\n\n{sentiment_msg}\n"
            )
        except Exception as e:
            logger.error(f"Error fetching {market} for channel: {e}")

    separator = "\n" + "━" * 20 + "\n\n"
    full_message = separator.join(message_parts)

    await _send_to_channel(context, full_message)


# ─────────────────────────────────────────────
# Channel: Quantum FX Signal
# ─────────────────────────────────────────────
async def channel_quantum_signal(context: ContextTypes.DEFAULT_TYPE, session: str = "london"):
    """Post Quantum Physics FX signal to channel."""
    channel_id = _get_channel_id()
    if not channel_id:
        return

    lang = _get_channel_language()
    logger.info(f"Posting Quantum {session} signal to channel...")

    try:
        signal = await generate_quantum_signal(session=session, language=lang)
        message = format_quantum_signal(signal)

        await _send_to_channel(context, message)

    except Exception as e:
        logger.error(f"Error posting Quantum signal to channel: {e}")


# ─────────────────────────────────────────────
# Channel: Session Update
# ─────────────────────────────────────────────
async def channel_session_update(context: ContextTypes.DEFAULT_TYPE):
    """Post session update to channel."""
    channel_id = _get_channel_id()
    if not channel_id:
        return

    session = context.job.data if context.job.data else "london"
    lang = _get_channel_language()
    logger.info(f"Posting {session} session update to channel...")

    try:
        update_msg = await get_session_update(session, language=lang)
        await _send_to_channel(context, update_msg)

    except Exception as e:
        logger.error(f"Error posting session update to channel: {e}")


# ─────────────────────────────────────────────
# Channel: US News Alert
# ─────────────────────────────────────────────
async def channel_us_news_alert(context: ContextTypes.DEFAULT_TYPE):
    """Post US news alert to channel."""
    channel_id = _get_channel_id()
    if not channel_id:
        return

    lang = _get_channel_language()
    logger.info("Posting US news alert to channel...")

    try:
        alert = await get_upcoming_events(language=lang)
        await _send_to_channel(context, alert)

    except Exception as e:
        logger.error(f"Error posting US news alert to channel: {e}")


# ─────────────────────────────────────────────
# Channel: US News Review
# ─────────────────────────────────────────────
async def channel_us_news_review(context: ContextTypes.DEFAULT_TYPE):
    """Post US news review to channel."""
    channel_id = _get_channel_id()
    if not channel_id:
        return

    lang = _get_channel_language()
    logger.info("Posting US news review to channel...")

    try:
        review = await get_news_review(language=lang)
        await _send_to_channel(context, review)

    except Exception as e:
        logger.error(f"Error posting US news review to channel: {e}")


# ─────────────────────────────────────────────
# Channel: Weekly Analysis
# ─────────────────────────────────────────────
async def channel_weekly_analysis(context: ContextTypes.DEFAULT_TYPE):
    """Post weekly analysis to channel."""
    channel_id = _get_channel_id()
    if not channel_id:
        return

    lang = _get_channel_language()
    logger.info("Posting weekly analysis to channel...")

    try:
        analysis = await get_weekly_analysis(language=lang)
        await _send_to_channel(context, analysis)

    except Exception as e:
        logger.error(f"Error posting weekly analysis to channel: {e}")


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
