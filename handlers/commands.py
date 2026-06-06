"""
Telegram bot command handlers.
Handles all user interactions: /start, /news, /sentiment, /lang, /subscribe, /help
"""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import settings
from fetchers import fetch_crypto_news, fetch_stocks_news, fetch_forex_news
from ai.llm import summarize_news, analyze_sentiment, format_sentiment_message
from scheduler.jobs import (
    subscribe_user,
    unsubscribe_user,
    is_subscribed,
    get_user_language,
    set_user_language,
)

logger = logging.getLogger(__name__)

# In-memory language store for non-subscribed users too
user_languages: dict[int, str] = {}


def get_lang(chat_id: int) -> str:
    """Get language for a user (checks subscriber store first, then local)."""
    lang = get_user_language(chat_id)
    if lang == settings.DEFAULT_LANGUAGE and chat_id in user_languages:
        return user_languages[chat_id]
    return lang


# ─────────────────────────────────────────────
# /start command
# ─────────────────────────────────────────────
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - welcome message."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    if lang == "id":
        welcome = (
            "🤖 *AI Market News Bot*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Selamat datang! Saya adalah bot berita pasar bertenaga AI.\n"
            "Saya menyediakan ringkasan berita dan analisis sentimen untuk:\n\n"
            "🪙 *Crypto* — Bitcoin, Ethereum, dll\n"
            "📈 *Saham US* — S&P 500, NASDAQ, dll\n"
            "💱 *Forex* — EUR/USD, GBP/USD, dll\n\n"
            "📋 *Perintah:*\n"
            "/news — Dapatkan berita pasar terbaru\n"
            "/sentiment — Analisis sentimen pasar\n"
            "/subscribe — Berlangganan update otomatis\n"
            "/unsubscribe — Berhenti berlangganan\n"
            "/lang — Ganti bahasa (EN/ID)\n"
            "/help — Bantuan\n\n"
            "Pilih kategori pasar di bawah untuk memulai! 👇"
        )
    else:
        welcome = (
            "🤖 *AI Market News Bot*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Welcome! I'm an AI-powered market news bot.\n"
            "I provide news summaries and sentiment analysis for:\n\n"
            "🪙 *Crypto* — Bitcoin, Ethereum, and more\n"
            "📈 *US Stocks* — S&P 500, NASDAQ, and more\n"
            "💱 *Forex* — EUR/USD, GBP/USD, and more\n\n"
            "📋 *Commands:*\n"
            "/news — Get latest market news\n"
            "/sentiment — Market sentiment analysis\n"
            "/subscribe — Subscribe to auto updates\n"
            "/unsubscribe — Unsubscribe from updates\n"
            "/lang — Switch language (EN/ID)\n"
            "/help — Help\n\n"
            "Choose a market category below to get started! 👇"
        )

    keyboard = [
        [
            InlineKeyboardButton("🪙 Crypto", callback_data="news_crypto"),
            InlineKeyboardButton("📈 Stocks", callback_data="news_stocks"),
            InlineKeyboardButton("💱 Forex", callback_data="news_forex"),
        ],
        [
            InlineKeyboardButton("📊 All Markets", callback_data="news_all"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome, parse_mode="Markdown", reply_markup=reply_markup
    )


# ─────────────────────────────────────────────
# /news command
# ─────────────────────────────────────────────
async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /news command - show market selection."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    text = (
        "📰 Pilih kategori pasar:" if lang == "id"
        else "📰 Choose a market category:"
    )

    keyboard = [
        [
            InlineKeyboardButton("🪙 Crypto", callback_data="news_crypto"),
            InlineKeyboardButton("📈 Stocks", callback_data="news_stocks"),
            InlineKeyboardButton("💱 Forex", callback_data="news_forex"),
        ],
        [
            InlineKeyboardButton("📊 All Markets", callback_data="news_all"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup)


# ─────────────────────────────────────────────
# /sentiment command
# ─────────────────────────────────────────────
async def sentiment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sentiment command - show market selection for sentiment."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    text = (
        "📊 Pilih pasar untuk analisis sentimen:" if lang == "id"
        else "📊 Choose a market for sentiment analysis:"
    )

    keyboard = [
        [
            InlineKeyboardButton("🪙 Crypto", callback_data="sent_crypto"),
            InlineKeyboardButton("📈 Stocks", callback_data="sent_stocks"),
            InlineKeyboardButton("💱 Forex", callback_data="sent_forex"),
        ],
        [
            InlineKeyboardButton("📊 All Markets", callback_data="sent_all"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup)


# ─────────────────────────────────────────────
# /lang command
# ─────────────────────────────────────────────
async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /lang command - switch language."""
    chat_id = update.effective_chat.id

    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇮🇩 Indonesia", callback_data="lang_id"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🌐 Choose your language / Pilih bahasa:",
        reply_markup=reply_markup,
    )


# ─────────────────────────────────────────────
# /subscribe command
# ─────────────────────────────────────────────
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscribe command."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    if is_subscribed(chat_id):
        text = (
            "✅ Anda sudah berlangganan update otomatis!\n"
            "Update dikirim setiap pagi (07:00) dan sore (18:00) WIB."
            if lang == "id"
            else "✅ You're already subscribed to auto updates!\n"
            "Updates are sent every morning (07:00) and evening (18:00) WIB."
        )
    else:
        subscribe_user(chat_id, lang)
        text = (
            "🔔 Berhasil berlangganan!\n"
            "Anda akan menerima update pasar setiap:\n"
            "• ☀️ Pagi: 07:00 WIB\n"
            "• 🌙 Sore: 18:00 WIB\n\n"
            "Gunakan /unsubscribe untuk berhenti."
            if lang == "id"
            else "🔔 Successfully subscribed!\n"
            "You'll receive market updates every:\n"
            "• ☀️ Morning: 07:00 WIB\n"
            "• 🌙 Evening: 18:00 WIB\n\n"
            "Use /unsubscribe to stop."
        )

    await update.message.reply_text(text)


# ─────────────────────────────────────────────
# /unsubscribe command
# ─────────────────────────────────────────────
async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unsubscribe command."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    if is_subscribed(chat_id):
        unsubscribe_user(chat_id)
        text = (
            "🔕 Berhasil berhenti berlangganan. Anda tidak akan menerima update otomatis lagi."
            if lang == "id"
            else "🔕 Successfully unsubscribed. You won't receive auto updates anymore."
        )
    else:
        text = (
            "ℹ️ Anda belum berlangganan."
            if lang == "id"
            else "ℹ️ You're not subscribed."
        )

    await update.message.reply_text(text)


# ─────────────────────────────────────────────
# /help command
# ─────────────────────────────────────────────
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    if lang == "id":
        text = (
            "❓ *Bantuan - AI Market News Bot*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "*Perintah yang tersedia:*\n\n"
            "/start — Mulai bot & lihat menu utama\n"
            "/news — Ambil berita pasar terbaru (Crypto/Saham/Forex)\n"
            "/sentiment — Lihat analisis sentimen pasar\n"
            "/subscribe — Berlangganan update pagi & sore\n"
            "/unsubscribe — Berhenti berlangganan\n"
            "/lang — Ganti bahasa (English/Indonesia)\n"
            "/help — Tampilkan pesan ini\n\n"
            "*Cara kerja:*\n"
            "Bot ini mengambil berita terbaru dari berbagai sumber, "
            "lalu menggunakan AI untuk membuat ringkasan dan analisis sentimen.\n\n"
            "*Jadwal update otomatis:*\n"
            "• ☀️ 07:00 WIB — Briefing pagi\n"
            "• 🌙 18:00 WIB — Ringkasan sore"
        )
    else:
        text = (
            "❓ *Help - AI Market News Bot*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "*Available commands:*\n\n"
            "/start — Start bot & show main menu\n"
            "/news — Get latest market news (Crypto/Stocks/Forex)\n"
            "/sentiment — View market sentiment analysis\n"
            "/subscribe — Subscribe to morning & evening updates\n"
            "/unsubscribe — Unsubscribe from updates\n"
            "/lang — Switch language (English/Indonesia)\n"
            "/help — Show this message\n\n"
            "*How it works:*\n"
            "This bot fetches the latest news from multiple sources, "
            "then uses AI to create summaries and sentiment analysis.\n\n"
            "*Auto update schedule:*\n"
            "• ☀️ 07:00 WIB — Morning briefing\n"
            "• 🌙 18:00 WIB — Evening wrap-up"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


# ─────────────────────────────────────────────
# Callback query handler (inline buttons)
# ─────────────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data
    lang = get_lang(chat_id)

    # Language switch
    if data.startswith("lang_"):
        new_lang = data.replace("lang_", "")
        user_languages[chat_id] = new_lang
        set_user_language(chat_id, new_lang)

        if new_lang == "id":
            text = "✅ Bahasa diubah ke *Bahasa Indonesia*."
        else:
            text = "✅ Language switched to *English*."

        await query.edit_message_text(text, parse_mode="Markdown")
        return

    # News requests
    if data.startswith("news_"):
        market = data.replace("news_", "")
        loading_text = (
            "⏳ Mengambil berita terbaru..." if lang == "id"
            else "⏳ Fetching latest news..."
        )
        await query.edit_message_text(loading_text)

        markets_to_fetch = (
            ["crypto", "stocks", "forex"] if market == "all" else [market]
        )

        message_parts = []
        for m in markets_to_fetch:
            data_result = await _fetch_market(m)
            articles = data_result.get("articles", [])
            summary = await summarize_news(articles, m, lang)

            # Add price info for crypto
            if m == "crypto" and data_result.get("prices"):
                price_text = _format_prices(data_result["prices"])
                message_parts.append(f"{price_text}\n\n{summary}")
            else:
                cat_emoji = {"crypto": "🪙", "stocks": "📈", "forex": "💱"}
                header = f"{cat_emoji.get(m, '📊')} *{m.upper()} NEWS*\n"
                message_parts.append(f"{header}\n{summary}")

        full_message = "\n\n{'━' * 20}\n\n".join(message_parts)

        # Split if too long
        if len(full_message) > 4000:
            for part in message_parts:
                await context.bot.send_message(
                    chat_id=chat_id, text=part, parse_mode="Markdown"
                )
            # Delete the loading message
            await query.message.delete()
        else:
            await query.edit_message_text(full_message, parse_mode="Markdown")
        return

    # Sentiment requests
    if data.startswith("sent_"):
        market = data.replace("sent_", "")
        loading_text = (
            "⏳ Menganalisis sentimen pasar..." if lang == "id"
            else "⏳ Analyzing market sentiment..."
        )
        await query.edit_message_text(loading_text)

        markets_to_analyze = (
            ["crypto", "stocks", "forex"] if market == "all" else [market]
        )

        message_parts = []
        for m in markets_to_analyze:
            data_result = await _fetch_market(m)
            articles = data_result.get("articles", [])
            sentiment = await analyze_sentiment(articles, m, lang)
            sentiment_msg = format_sentiment_message(sentiment, m)
            message_parts.append(sentiment_msg)

        full_message = "\n".join(message_parts)
        await query.edit_message_text(full_message, parse_mode="Markdown")
        return


async def _fetch_market(market: str) -> dict:
    """Helper to fetch market data."""
    if market == "crypto":
        return await fetch_crypto_news(limit=5)
    elif market == "stocks":
        return await fetch_stocks_news(limit=5)
    elif market == "forex":
        return await fetch_forex_news(limit=5)
    return {"articles": []}


def _format_prices(prices: list[dict]) -> str:
    """Format crypto prices into a readable string."""
    lines = ["🪙 *CRYPTO PRICES*\n"]
    for p in prices:
        change = p.get("change_24h", 0)
        emoji = "🟢" if change >= 0 else "🔴"
        lines.append(
            f"{emoji} *{p['name']}*: ${p['price_usd']:,.2f} ({change:+.1f}%)"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────
# Register all handlers
# ─────────────────────────────────────────────
def register_handlers(app: Application):
    """Register all command and callback handlers."""
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(CommandHandler("sentiment", sentiment_command))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info("All handlers registered successfully.")
