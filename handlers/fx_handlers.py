"""
FX Trading feature command handlers.
Handles: /signal, /usnews, /review, /session, /weekly
"""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from fetchers.fx_signals import generate_fx_signal, format_signal_message
from fetchers.us_news import get_upcoming_events, get_news_review, get_weekly_analysis
from fetchers.sessions import get_session_update, get_all_sessions_summary
from fetchers.forex import fetch_forex_news
from handlers.commands import get_lang

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# /signal command - FX Signal Harian
# ─────────────────────────────────────────────
async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /signal command - generate FX trading signal."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    loading_text = (
        "⏳ Generating FX signal..." if lang == "en"
        else "⏳ Membuat sinyal FX..."
    )
    loading_msg = await update.message.reply_text(loading_text)

    try:
        # Fetch forex news for context
        forex_data = await fetch_forex_news(limit=5)
        news_context = "\n".join(
            f"- {a['title']}: {a.get('description', '')}"
            for a in forex_data.get("articles", [])
        )

        # Generate signal
        signal = await generate_fx_signal(news_context=news_context, language=lang)
        message = format_signal_message(signal)

        await loading_msg.edit_text(message)

    except Exception as e:
        logger.error(f"Error in /signal command: {e}")
        await loading_msg.edit_text(
            "⚠️ Failed to generate signal. Please try again later."
        )


# ─────────────────────────────────────────────
# /usnews command - US News Alert (pre-release)
# ─────────────────────────────────────────────
async def usnews_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /usnews command - show US economic news options."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    text = (
        "🖥 US Economic News - Pilih:" if lang == "id"
        else "🖥 US Economic News - Choose:"
    )

    keyboard = [
        [
            InlineKeyboardButton("📢 Upcoming Alert", callback_data="fx_usnews_alert"),
            InlineKeyboardButton("📊 Post-Release Review", callback_data="fx_usnews_review"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup)


# ─────────────────────────────────────────────
# /review command - US News Review (post-release)
# ─────────────────────────────────────────────
async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /review command - post-release economic data analysis."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    loading_text = (
        "⏳ Analyzing recent US data releases..." if lang == "en"
        else "⏳ Menganalisis data ekonomi terbaru..."
    )
    loading_msg = await update.message.reply_text(loading_text)

    try:
        review = await get_news_review(language=lang)

        # Split if too long for Telegram
        if len(review) > 4000:
            chunks = _split_message(review)
            await loading_msg.edit_text(chunks[0])
            for chunk in chunks[1:]:
                await update.message.reply_text(chunk)
        else:
            await loading_msg.edit_text(review)

    except Exception as e:
        logger.error(f"Error in /review command: {e}")
        await loading_msg.edit_text(
            "⚠️ Failed to generate review. Please try again later."
        )


# ─────────────────────────────────────────────
# /session command - Session Update
# ─────────────────────────────────────────────
async def session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /session command - show session selection."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    text = (
        "🌐 Pilih sesi trading:" if lang == "id"
        else "🌐 Choose trading session:"
    )

    keyboard = [
        [
            InlineKeyboardButton("🌏 Asian", callback_data="fx_session_asian"),
            InlineKeyboardButton("🇬🇧 London", callback_data="fx_session_london"),
            InlineKeyboardButton("🇺🇸 New York", callback_data="fx_session_newyork"),
        ],
        [
            InlineKeyboardButton("🌐 All Sessions", callback_data="fx_session_all"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup)


# ─────────────────────────────────────────────
# /weekly command - Weekly Analysis
# ─────────────────────────────────────────────
async def weekly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /weekly command - comprehensive weekly market analysis."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    loading_text = (
        "⏳ Generating weekly analysis..." if lang == "en"
        else "⏳ Membuat analisa mingguan..."
    )
    loading_msg = await update.message.reply_text(loading_text)

    try:
        analysis = await get_weekly_analysis(language=lang)

        # Split if too long for Telegram
        if len(analysis) > 4000:
            chunks = _split_message(analysis)
            await loading_msg.edit_text(chunks[0])
            for chunk in chunks[1:]:
                await update.message.reply_text(chunk)
        else:
            await loading_msg.edit_text(analysis)

    except Exception as e:
        logger.error(f"Error in /weekly command: {e}")
        await loading_msg.edit_text(
            "⚠️ Failed to generate weekly analysis. Please try again later."
        )


# ─────────────────────────────────────────────
# Callback handler for FX inline buttons
# ─────────────────────────────────────────────
async def fx_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle FX-related inline button callbacks."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data
    lang = get_lang(chat_id)

    # US News callbacks
    if data == "fx_usnews_alert":
        loading_text = (
            "⏳ Checking upcoming US data releases..." if lang == "en"
            else "⏳ Mengecek jadwal data ekonomi AS..."
        )
        await query.edit_message_text(loading_text)

        try:
            alert = await get_upcoming_events(language=lang)
            if len(alert) > 4000:
                chunks = _split_message(alert)
                await query.edit_message_text(chunks[0])
                for chunk in chunks[1:]:
                    await context.bot.send_message(chat_id=chat_id, text=chunk)
            else:
                await query.edit_message_text(alert)
        except Exception as e:
            logger.error(f"Error in US news alert callback: {e}")
            await query.edit_message_text(
                "⚠️ Failed to fetch US news alert. Try /usnews again."
            )
        return

    if data == "fx_usnews_review":
        loading_text = (
            "⏳ Analyzing post-release data..." if lang == "en"
            else "⏳ Menganalisis data pasca rilis..."
        )
        await query.edit_message_text(loading_text)

        try:
            review = await get_news_review(language=lang)
            if len(review) > 4000:
                chunks = _split_message(review)
                await query.edit_message_text(chunks[0])
                for chunk in chunks[1:]:
                    await context.bot.send_message(chat_id=chat_id, text=chunk)
            else:
                await query.edit_message_text(review)
        except Exception as e:
            logger.error(f"Error in US news review callback: {e}")
            await query.edit_message_text(
                "⚠️ Failed to generate review. Try /review again."
            )
        return

    # Session callbacks
    if data.startswith("fx_session_"):
        session = data.replace("fx_session_", "")
        loading_text = (
            "⏳ Analyzing market session..." if lang == "en"
            else "⏳ Menganalisis sesi pasar..."
        )
        await query.edit_message_text(loading_text)

        try:
            if session == "all":
                update_msg = await get_all_sessions_summary(language=lang)
            else:
                update_msg = await get_session_update(session, language=lang)

            if len(update_msg) > 4000:
                chunks = _split_message(update_msg)
                await query.edit_message_text(chunks[0])
                for chunk in chunks[1:]:
                    await context.bot.send_message(chat_id=chat_id, text=chunk)
            else:
                await query.edit_message_text(update_msg)
        except Exception as e:
            logger.error(f"Error in session callback: {e}")
            await query.edit_message_text(
                "⚠️ Failed to generate session update. Try /session again."
            )
        return


# ─────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────
def _split_message(text: str, max_length: int = 4000) -> list[str]:
    """Split a long message into chunks that fit Telegram's limit."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break

        # Find a good split point (newline)
        split_point = text.rfind("\n", 0, max_length)
        if split_point == -1:
            split_point = max_length

        chunks.append(text[:split_point])
        text = text[split_point:].lstrip("\n")

    return chunks


# ─────────────────────────────────────────────
# Register FX handlers
# ─────────────────────────────────────────────
def register_fx_handlers(app: Application):
    """Register all FX trading feature handlers."""
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("usnews", usnews_command))
    app.add_handler(CommandHandler("review", review_command))
    app.add_handler(CommandHandler("session", session_command))
    app.add_handler(CommandHandler("weekly", weekly_command))
    app.add_handler(CallbackQueryHandler(fx_button_callback, pattern="^fx_"))

    logger.info("FX trading handlers registered successfully.")
