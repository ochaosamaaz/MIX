"""
Telegram bot command handlers.
Handles all user interactions with beautiful UI and inline keyboards.
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
from handlers.force_join import check_force_join, handle_check_joined
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
# /start command — Beautiful Main Menu
# ─────────────────────────────────────────────
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - beautiful welcome with main menu."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    # Check force join
    if not await check_force_join(update, context):
        return

    if lang == "id":
        welcome = (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "    🤖 AI MARKET NEWS BOT\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Selamat datang! Bot berita pasar\n"
            "bertenaga AI untuk trader.\n\n"
            "🪙 Crypto  •  📈 Saham US  •  💱 Forex\n\n"
            "━━ FITUR UTAMA ━━\n"
            "📰 Berita & Ringkasan AI\n"
            "📊 Analisis Sentimen Pasar\n"
            "✨ Sinyal FX Harian\n"
            "🌐 Update Sesi Trading\n"
            "🖥 Alert Data Ekonomi AS\n"
            "🧠 Tanya AI Soal Market\n"
            "💰 Kalkulator Risiko\n\n"
            "Pilih menu di bawah untuk mulai 👇"
        )
    else:
        welcome = (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "    🤖 AI MARKET NEWS BOT\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Welcome! AI-powered market news\n"
            "bot built for traders.\n\n"
            "🪙 Crypto  •  📈 US Stocks  •  💱 Forex\n\n"
            "━━ KEY FEATURES ━━\n"
            "📰 News & AI Summaries\n"
            "📊 Market Sentiment Analysis\n"
            "✨ Daily FX Signals\n"
            "🌐 Session Direction Updates\n"
            "🖥 US Economic Data Alerts\n"
            "🧠 Ask AI About Markets\n"
            "💰 Risk Calculator\n\n"
            "Choose a menu below to start 👇"
        )

    keyboard = [
        [
            InlineKeyboardButton("📰 News", callback_data="menu_news"),
            InlineKeyboardButton("📊 Sentiment", callback_data="menu_sentiment"),
        ],
        [
            InlineKeyboardButton("✨ FX Signal", callback_data="menu_signal"),
            InlineKeyboardButton("🌐 Sessions", callback_data="menu_session"),
        ],
        [
            InlineKeyboardButton("🖥 US News", callback_data="menu_usnews"),
            InlineKeyboardButton("📈 Weekly", callback_data="menu_weekly"),
        ],
        [
            InlineKeyboardButton("🧠 Ask AI", callback_data="menu_ask"),
            InlineKeyboardButton("💰 Risk Calc", callback_data="menu_risk"),
        ],
        [
            InlineKeyboardButton("📋 Tutorial", callback_data="menu_tutorial"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome, reply_markup=reply_markup)


# ─────────────────────────────────────────────
# /news command
# ─────────────────────────────────────────────
async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /news command - show market selection."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    # Check force join
    if not await check_force_join(update, context):
        return

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
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_back")],
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

    # Check force join
    if not await check_force_join(update, context):
        return

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
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup)


# ─────────────────────────────────────────────
# /tutorial command — Full Guide
# ─────────────────────────────────────────────
async def tutorial_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tutorial command - complete bot tutorial."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    # Check force join
    if not await check_force_join(update, context):
        return

    keyboard = [
        [
            InlineKeyboardButton("1️⃣ Market News", callback_data="tut_news"),
            InlineKeyboardButton("2️⃣ FX Signals", callback_data="tut_signal"),
        ],
        [
            InlineKeyboardButton("3️⃣ Sessions", callback_data="tut_session"),
            InlineKeyboardButton("4️⃣ US News", callback_data="tut_usnews"),
        ],
        [
            InlineKeyboardButton("5️⃣ Ask AI", callback_data="tut_ask"),
            InlineKeyboardButton("6️⃣ Risk Calc", callback_data="tut_risk"),
        ],
        [
            InlineKeyboardButton("7️⃣ Subscribe", callback_data="tut_subscribe"),
        ],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if lang == "id":
        text = (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "    📋 TUTORIAL & PANDUAN\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Pilih topik untuk melihat panduan\n"
            "lengkap cara menggunakan fitur:\n\n"
            "1️⃣ Market News — Berita & ringkasan\n"
            "2️⃣ FX Signals — Sinyal trading\n"
            "3️⃣ Sessions — Update per sesi\n"
            "4️⃣ US News — Alert data ekonomi\n"
            "5️⃣ Ask AI — Tanya apapun\n"
            "6️⃣ Risk Calc — Hitung lot size\n"
            "7️⃣ Subscribe — Langganan auto update\n\n"
            "Klik salah satu untuk belajar 👇"
        )
    else:
        text = (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "    📋 TUTORIAL & GUIDE\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Select a topic to see the full\n"
            "guide on how to use each feature:\n\n"
            "1️⃣ Market News — News & summaries\n"
            "2️⃣ FX Signals — Trading signals\n"
            "3️⃣ Sessions — Session updates\n"
            "4️⃣ US News — Economic data alerts\n"
            "5️⃣ Ask AI — Ask anything\n"
            "6️⃣ Risk Calc — Position sizing\n"
            "7️⃣ Subscribe — Auto update subscription\n\n"
            "Click one to learn more 👇"
        )

    await update.message.reply_text(text, reply_markup=reply_markup)


# ─────────────────────────────────────────────
# /lang command
# ─────────────────────────────────────────────
async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /lang command - switch language."""
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇮🇩 Indonesia", callback_data="lang_id"),
        ],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_back")],
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
            "✅ Anda sudah berlangganan update otomatis!\n\n"
            "Jadwal update:\n"
            "• ☀️ 07:00 — Briefing pagi\n"
            "• ✨ 08:00 — FX Signal\n"
            "• 🇬🇧 14:00 — London session\n"
            "• 🌙 18:00 — Ringkasan sore\n"
            "• 🇺🇸 19:30 — NY session\n"
            "• 🖥 20:00 — US News alert\n\n"
            "Gunakan /unsubscribe untuk berhenti."
            if lang == "id"
            else "✅ You're already subscribed!\n\n"
            "Update schedule:\n"
            "• ☀️ 07:00 — Morning briefing\n"
            "• ✨ 08:00 — FX Signal\n"
            "• 🇬🇧 14:00 — London session\n"
            "• 🌙 18:00 — Evening wrap-up\n"
            "• 🇺🇸 19:30 — NY session\n"
            "• 🖥 20:00 — US News alert\n\n"
            "Use /unsubscribe to stop."
        )
    else:
        subscribe_user(chat_id, lang)
        text = (
            "🔔 Berhasil berlangganan!\n\n"
            "Anda akan menerima update pasar otomatis:\n"
            "• ☀️ 07:00 — Briefing pagi\n"
            "• ✨ 08:00 — FX Signal harian\n"
            "• 🇬🇧 14:00 — London session update\n"
            "• 🌙 18:00 — Ringkasan sore\n"
            "• 🇺🇸 19:30 — NY session update\n"
            "• 🖥 20:00 — US News alert\n"
            "• 📊 Minggu — Analisa mingguan\n\n"
            "Gunakan /unsubscribe untuk berhenti."
            if lang == "id"
            else "🔔 Successfully subscribed!\n\n"
            "You'll receive auto market updates:\n"
            "• ☀️ 07:00 — Morning briefing\n"
            "• ✨ 08:00 — Daily FX Signal\n"
            "• 🇬🇧 14:00 — London session update\n"
            "• 🌙 18:00 — Evening wrap-up\n"
            "• 🇺🇸 19:30 — NY session update\n"
            "• 🖥 20:00 — US News alert\n"
            "• 📊 Sunday — Weekly analysis\n\n"
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
            "🔕 Berhasil berhenti berlangganan.\nAnda tidak akan menerima update otomatis lagi."
            if lang == "id"
            else "🔕 Successfully unsubscribed.\nYou won't receive auto updates anymore."
        )
    else:
        text = (
            "ℹ️ Anda belum berlangganan." if lang == "id"
            else "ℹ️ You're not subscribed yet."
        )

    await update.message.reply_text(text)


# ─────────────────────────────────────────────
# /help command
# ─────────────────────────────────────────────
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command - quick reference."""
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    if lang == "id":
        text = (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "    ❓ DAFTAR PERINTAH\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📰 MARKET NEWS\n"
            "/news — Berita pasar terbaru\n"
            "/sentiment — Analisis sentimen\n\n"
            "💱 FX TRADING\n"
            "/signal — Sinyal FX + entry/exit\n"
            "/session — Update per sesi trading\n"
            "/usnews — Alert data ekonomi AS\n"
            "/review — Analisa pasca rilis\n"
            "/weekly — Analisa mingguan\n\n"
            "🧠 TOOLS\n"
            "/ask <pertanyaan> — Tanya AI\n"
            "/risk <bal> <pair> <entry> <sl> — Hitung lot\n\n"
            "⚙️ SETTINGS\n"
            "/subscribe — Langganan auto update\n"
            "/unsubscribe — Berhenti langganan\n"
            "/lang — Ganti bahasa\n"
            "/tutorial — Panduan lengkap\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "    ❓ COMMAND LIST\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📰 MARKET NEWS\n"
            "/news — Latest market news\n"
            "/sentiment — Sentiment analysis\n\n"
            "💱 FX TRADING\n"
            "/signal — FX signal + entry/exit\n"
            "/session — Session direction update\n"
            "/usnews — US economic data alert\n"
            "/review — Post-release analysis\n"
            "/weekly — Weekly analysis\n\n"
            "🧠 TOOLS\n"
            "/ask <question> — Ask AI anything\n"
            "/risk <bal> <pair> <entry> <sl> — Lot calculator\n\n"
            "⚙️ SETTINGS\n"
            "/subscribe — Subscribe to auto updates\n"
            "/unsubscribe — Unsubscribe\n"
            "/lang — Switch language\n"
            "/tutorial — Full guide\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )

    await update.message.reply_text(text)


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

    # Handle "check_joined" callback (force join verification)
    if data == "check_joined":
        await handle_check_joined(update, context)
        return

    # ── Menu navigation ──
    if data == "menu_back":
        # Show main menu again
        if lang == "id":
            text = "🤖 Menu Utama — Pilih fitur:"
        else:
            text = "🤖 Main Menu — Choose a feature:"

        keyboard = [
            [
                InlineKeyboardButton("📰 News", callback_data="menu_news"),
                InlineKeyboardButton("📊 Sentiment", callback_data="menu_sentiment"),
            ],
            [
                InlineKeyboardButton("✨ FX Signal", callback_data="menu_signal"),
                InlineKeyboardButton("🌐 Sessions", callback_data="menu_session"),
            ],
            [
                InlineKeyboardButton("🖥 US News", callback_data="menu_usnews"),
                InlineKeyboardButton("📈 Weekly", callback_data="menu_weekly"),
            ],
            [
                InlineKeyboardButton("🧠 Ask AI", callback_data="menu_ask"),
                InlineKeyboardButton("💰 Risk Calc", callback_data="menu_risk"),
            ],
            [
                InlineKeyboardButton("📋 Tutorial", callback_data="menu_tutorial"),
                InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
            ],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ── Menu shortcuts ──
    if data == "menu_news":
        text = "📰 Pilih pasar:" if lang == "id" else "📰 Choose market:"
        keyboard = [
            [
                InlineKeyboardButton("🪙 Crypto", callback_data="news_crypto"),
                InlineKeyboardButton("📈 Stocks", callback_data="news_stocks"),
                InlineKeyboardButton("💱 Forex", callback_data="news_forex"),
            ],
            [InlineKeyboardButton("📊 All Markets", callback_data="news_all")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_back")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_sentiment":
        text = "📊 Pilih pasar:" if lang == "id" else "📊 Choose market:"
        keyboard = [
            [
                InlineKeyboardButton("🪙 Crypto", callback_data="sent_crypto"),
                InlineKeyboardButton("📈 Stocks", callback_data="sent_stocks"),
                InlineKeyboardButton("💱 Forex", callback_data="sent_forex"),
            ],
            [InlineKeyboardButton("📊 All Markets", callback_data="sent_all")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_back")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_signal":
        text = (
            "✨ Untuk mendapatkan sinyal FX, ketik:\n/signal"
            if lang == "id"
            else "✨ To get an FX signal, type:\n/signal"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_session":
        text = "🌐 Pilih sesi:" if lang == "id" else "🌐 Choose session:"
        keyboard = [
            [
                InlineKeyboardButton("🌏 Asian", callback_data="fx_session_asian"),
                InlineKeyboardButton("🇬🇧 London", callback_data="fx_session_london"),
                InlineKeyboardButton("🇺🇸 New York", callback_data="fx_session_newyork"),
            ],
            [InlineKeyboardButton("🌐 All Sessions", callback_data="fx_session_all")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_back")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_usnews":
        text = "🖥 US Economic News:" if lang == "id" else "🖥 US Economic News:"
        keyboard = [
            [
                InlineKeyboardButton("📢 Upcoming Alert", callback_data="fx_usnews_alert"),
                InlineKeyboardButton("📊 Post Review", callback_data="fx_usnews_review"),
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_back")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_weekly":
        text = (
            "📈 Untuk analisa mingguan, ketik:\n/weekly"
            if lang == "id"
            else "📈 For weekly analysis, type:\n/weekly"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_ask":
        if lang == "id":
            text = (
                "🧠 ASK AI — Tanya Apapun\n\n"
                "Ketik /ask diikuti pertanyaan:\n\n"
                "Contoh:\n"
                "• /ask Kenapa gold naik?\n"
                "• /ask Strategi trading NFP?\n"
                "• /ask Analisa EUR/USD H4"
            )
        else:
            text = (
                "🧠 ASK AI — Ask Anything\n\n"
                "Type /ask followed by your question:\n\n"
                "Examples:\n"
                "• /ask Why is gold rising?\n"
                "• /ask NFP trading strategy?\n"
                "• /ask EUR/USD H4 analysis"
            )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_risk":
        if lang == "id":
            text = (
                "💰 RISK CALCULATOR\n\n"
                "Ketik /risk diikuti parameter:\n"
                "/risk <balance> <pair> <entry> <sl> [risk%]\n\n"
                "Contoh:\n"
                "• /risk 1000 EURUSD 1.0850 1.0820\n"
                "• /risk 5000 XAUUSD 2350 2340 2"
            )
        else:
            text = (
                "💰 RISK CALCULATOR\n\n"
                "Type /risk followed by parameters:\n"
                "/risk <balance> <pair> <entry> <sl> [risk%]\n\n"
                "Examples:\n"
                "• /risk 1000 EURUSD 1.0850 1.0820\n"
                "• /risk 5000 XAUUSD 2350 2340 2"
            )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_tutorial":
        if lang == "id":
            text = (
                "📋 TUTORIAL — Pilih topik:"
            )
        else:
            text = (
                "📋 TUTORIAL — Choose topic:"
            )
        keyboard = [
            [
                InlineKeyboardButton("1️⃣ News", callback_data="tut_news"),
                InlineKeyboardButton("2️⃣ Signals", callback_data="tut_signal"),
            ],
            [
                InlineKeyboardButton("3️⃣ Sessions", callback_data="tut_session"),
                InlineKeyboardButton("4️⃣ US News", callback_data="tut_usnews"),
            ],
            [
                InlineKeyboardButton("5️⃣ Ask AI", callback_data="tut_ask"),
                InlineKeyboardButton("6️⃣ Risk", callback_data="tut_risk"),
            ],
            [InlineKeyboardButton("7️⃣ Subscribe", callback_data="tut_subscribe")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_back")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_settings":
        text = "⚙️ Settings:" if lang == "id" else "⚙️ Settings:"
        keyboard = [
            [
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
                InlineKeyboardButton("🇮🇩 Indonesia", callback_data="lang_id"),
            ],
            [
                InlineKeyboardButton("🔔 Subscribe", callback_data="settings_sub"),
                InlineKeyboardButton("🔕 Unsubscribe", callback_data="settings_unsub"),
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_back")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ── Tutorial callbacks ──
    if data.startswith("tut_"):
        topic = data.replace("tut_", "")
        text = _get_tutorial_text(topic, lang)
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Tutorial", callback_data="menu_tutorial")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_back")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ── Settings callbacks ──
    if data == "settings_sub":
        if not is_subscribed(chat_id):
            subscribe_user(chat_id, lang)
            text = "🔔 Subscribed!" if lang == "en" else "🔔 Berlangganan!"
        else:
            text = "✅ Already subscribed." if lang == "en" else "✅ Sudah berlangganan."
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_settings")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "settings_unsub":
        if is_subscribed(chat_id):
            unsubscribe_user(chat_id)
            text = "🔕 Unsubscribed." if lang == "en" else "🔕 Berhenti langganan."
        else:
            text = "ℹ️ Not subscribed." if lang == "en" else "ℹ️ Belum berlangganan."
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_settings")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ── Language switch ──
    if data.startswith("lang_"):
        new_lang = data.replace("lang_", "")
        user_languages[chat_id] = new_lang
        set_user_language(chat_id, new_lang)

        if new_lang == "id":
            text = "✅ Bahasa diubah ke Bahasa Indonesia."
        else:
            text = "✅ Language switched to English."

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ── News requests ──
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
            try:
                data_result = await _fetch_market(m)
                articles = data_result.get("articles", [])
                summary = await summarize_news(articles, m, lang)

                if m == "crypto" and data_result.get("prices"):
                    price_text = _format_prices(data_result["prices"])
                    message_parts.append(f"{price_text}\n\n{summary}")
                else:
                    cat_emoji = {"crypto": "🪙", "stocks": "📈", "forex": "💱"}
                    header = f"{cat_emoji.get(m, '📊')} {m.upper()} NEWS\n"
                    message_parts.append(f"{header}\n{summary}")
            except Exception as e:
                logger.error(f"Error processing {m} news: {e}")
                cat_emoji = {"crypto": "🪙", "stocks": "📈", "forex": "💱"}
                message_parts.append(
                    f"{cat_emoji.get(m, '📊')} {m.upper()} NEWS\n\n"
                    f"⚠️ Error fetching {m} news. Please try again later."
                )

        separator = "\n\n" + "━" * 20 + "\n\n"
        full_message = separator.join(message_parts)

        if len(full_message) > 4000:
            for part in message_parts:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=part)
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
            try:
                await query.message.delete()
            except Exception:
                pass
        else:
            try:
                await query.edit_message_text(full_message)
            except Exception:
                await query.edit_message_text(
                    "⚠️ Error displaying news. Please try /news again."
                )
        return

    # ── Sentiment requests ──
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
            try:
                data_result = await _fetch_market(m)
                articles = data_result.get("articles", [])
                sentiment = await analyze_sentiment(articles, m, lang)
                sentiment_msg = format_sentiment_message(sentiment, m)
                message_parts.append(sentiment_msg)
            except Exception as e:
                logger.error(f"Error analyzing {m} sentiment: {e}")
                message_parts.append(f"⚠️ Error analyzing {m} sentiment.")

        full_message = "\n".join(message_parts)
        try:
            await query.edit_message_text(full_message)
        except Exception:
            await query.edit_message_text(
                "⚠️ Error displaying sentiment. Please try /sentiment again."
            )
        return


# ─────────────────────────────────────────────
# Tutorial text generator
# ─────────────────────────────────────────────
def _get_tutorial_text(topic: str, lang: str) -> str:
    """Get tutorial text for a specific topic."""
    tutorials = {
        "news": {
            "en": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "📰 TUTORIAL: MARKET NEWS\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Get AI-summarized market news\n"
                "for Crypto, US Stocks, and Forex.\n\n"
                "HOW TO USE:\n"
                "1. Type /news or click 📰 News\n"
                "2. Choose: Crypto, Stocks, Forex, or All\n"
                "3. Bot fetches latest news + AI summary\n\n"
                "WHAT YOU GET:\n"
                "• Top 5 headlines from each market\n"
                "• AI-generated concise summary\n"
                "• Crypto live prices included\n\n"
                "💡 TIP: Use /sentiment for market\n"
                "mood analysis with score (-100 to +100)"
            ),
            "id": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "📰 TUTORIAL: MARKET NEWS\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Dapatkan berita pasar yang diringkas\n"
                "AI untuk Crypto, Saham US, dan Forex.\n\n"
                "CARA PAKAI:\n"
                "1. Ketik /news atau klik 📰 News\n"
                "2. Pilih: Crypto, Stocks, Forex, atau All\n"
                "3. Bot ambil berita terbaru + ringkasan AI\n\n"
                "YANG DIDAPAT:\n"
                "• 5 headline teratas tiap pasar\n"
                "• Ringkasan AI yang singkat & padat\n"
                "• Harga crypto live\n\n"
                "💡 TIP: Pakai /sentiment untuk analisis\n"
                "mood pasar dengan skor (-100 sampai +100)"
            ),
        },
        "signal": {
            "en": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "✨ TUTORIAL: FX SIGNALS\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Get AI-generated forex trading signals\n"
                "with precise entry & exit levels.\n\n"
                "HOW TO USE:\n"
                "1. Type /signal\n"
                "2. Wait for AI to analyze market\n"
                "3. Receive signal with levels\n\n"
                "SIGNAL INCLUDES:\n"
                "• Pair & Direction (BUY/SELL)\n"
                "• Entry Price\n"
                "• Stop Loss\n"
                "• Take Profit 1, 2, 3\n"
                "• Risk:Reward Ratio\n"
                "• Confidence Level\n"
                "• Analysis & Key Levels\n\n"
                "⚠️ Always use proper risk management!\n"
                "Never risk more than 1-2% per trade."
            ),
            "id": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "✨ TUTORIAL: FX SIGNALS\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Dapatkan sinyal forex dari AI\n"
                "dengan level entry & exit spesifik.\n\n"
                "CARA PAKAI:\n"
                "1. Ketik /signal\n"
                "2. Tunggu AI analisa pasar\n"
                "3. Terima sinyal dengan level\n\n"
                "SINYAL BERISI:\n"
                "• Pair & Arah (BUY/SELL)\n"
                "• Harga Entry\n"
                "• Stop Loss\n"
                "• Take Profit 1, 2, 3\n"
                "• Rasio Risk:Reward\n"
                "• Level Confidence\n"
                "• Analisis & Level Kunci\n\n"
                "⚠️ Selalu gunakan risk management!\n"
                "Jangan risiko lebih dari 1-2% per trade."
            ),
        },
        "session": {
            "en": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🌐 TUTORIAL: SESSION UPDATES\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Get market direction analysis\n"
                "for each major trading session.\n\n"
                "SESSIONS:\n"
                "🌏 Asian  — 07:00-16:00 WIB\n"
                "🇬🇧 London — 14:00-23:00 WIB\n"
                "🇺🇸 New York — 19:00-04:00 WIB\n\n"
                "HOW TO USE:\n"
                "1. Type /session\n"
                "2. Choose a session\n"
                "3. Get: bias, pairs to watch,\n"
                "   volatility, and strategy\n\n"
                "💡 TIP: Check session update before\n"
                "placing any trade for that session."
            ),
            "id": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🌐 TUTORIAL: SESSION UPDATES\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Dapatkan analisis arah market\n"
                "untuk setiap sesi trading.\n\n"
                "SESI:\n"
                "🌏 Asian  — 07:00-16:00 WIB\n"
                "🇬🇧 London — 14:00-23:00 WIB\n"
                "🇺🇸 New York — 19:00-04:00 WIB\n\n"
                "CARA PAKAI:\n"
                "1. Ketik /session\n"
                "2. Pilih sesi\n"
                "3. Dapat: bias, pair to watch,\n"
                "   volatilitas, dan strategi\n\n"
                "💡 TIP: Cek session update sebelum\n"
                "buka posisi di sesi tersebut."
            ),
        },
        "usnews": {
            "en": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🖥 TUTORIAL: US NEWS ALERTS\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Get notified before & after major\n"
                "US economic data releases.\n\n"
                "TWO MODES:\n"
                "📢 Alert — Before data release\n"
                "   Shows: expected, previous,\n"
                "   impact level, pairs affected\n\n"
                "📊 Review — After data release\n"
                "   Shows: actual vs expected,\n"
                "   market reaction, outlook\n\n"
                "HOW TO USE:\n"
                "• /usnews — Choose alert or review\n"
                "• /review — Direct post-release analysis\n\n"
                "💡 TIP: High-impact events (NFP, CPI,\n"
                "FOMC) move markets 50-200 pips!"
            ),
            "id": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🖥 TUTORIAL: US NEWS ALERTS\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Notifikasi sebelum & sesudah rilis\n"
                "data ekonomi AS.\n\n"
                "DUA MODE:\n"
                "📢 Alert — Sebelum rilis data\n"
                "   Isi: expected, previous,\n"
                "   level impact, pair terpengaruh\n\n"
                "📊 Review — Setelah rilis data\n"
                "   Isi: actual vs expected,\n"
                "   reaksi market, outlook\n\n"
                "CARA PAKAI:\n"
                "• /usnews — Pilih alert atau review\n"
                "• /review — Langsung analisa pasca rilis\n\n"
                "💡 TIP: Event high-impact (NFP, CPI,\n"
                "FOMC) bisa gerakin 50-200 pips!"
            ),
        },
        "ask": {
            "en": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🧠 TUTORIAL: ASK AI\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Ask any market-related question\n"
                "and get an AI-powered answer.\n\n"
                "HOW TO USE:\n"
                "/ask <your question here>\n\n"
                "EXAMPLES:\n"
                "• /ask Why is gold rising today?\n"
                "• /ask EUR/USD technical analysis\n"
                "• /ask How to trade during NFP?\n"
                "• /ask What is RSI divergence?\n"
                "• /ask Best strategy for ranging market\n\n"
                "WORKS FOR:\n"
                "✅ Technical analysis questions\n"
                "✅ Fundamental analysis\n"
                "✅ Trading strategies\n"
                "✅ Market education\n"
                "✅ Specific pair analysis\n\n"
                "💡 TIP: Be specific in your question\n"
                "for better answers!"
            ),
            "id": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🧠 TUTORIAL: ASK AI\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Tanya apapun soal market\n"
                "dan dapatkan jawaban dari AI.\n\n"
                "CARA PAKAI:\n"
                "/ask <pertanyaan kamu>\n\n"
                "CONTOH:\n"
                "• /ask Kenapa gold naik hari ini?\n"
                "• /ask Analisa teknikal EUR/USD\n"
                "• /ask Cara trading saat NFP?\n"
                "• /ask Apa itu RSI divergence?\n"
                "• /ask Strategi terbaik saat ranging\n\n"
                "BISA UNTUK:\n"
                "✅ Pertanyaan teknikal\n"
                "✅ Analisa fundamental\n"
                "✅ Strategi trading\n"
                "✅ Edukasi market\n"
                "✅ Analisa pair spesifik\n\n"
                "💡 TIP: Semakin spesifik pertanyaan,\n"
                "semakin bagus jawabannya!"
            ),
        },
        "risk": {
            "en": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "💰 TUTORIAL: RISK CALCULATOR\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Calculate proper position size\n"
                "based on your risk parameters.\n\n"
                "FORMAT:\n"
                "/risk <balance> <pair> <entry> <sl> [risk%]\n\n"
                "EXAMPLES:\n"
                "• /risk 1000 EURUSD 1.0850 1.0820\n"
                "  → $1000 balance, 1% risk (default)\n\n"
                "• /risk 5000 GBPJPY 192.50 191.80 2\n"
                "  → $5000 balance, 2% risk\n\n"
                "• /risk 10000 XAUUSD 2350 2340 1.5\n"
                "  → $10000 balance, 1.5% risk on Gold\n\n"
                "OUTPUT:\n"
                "• Exact lot size (standard/mini/micro)\n"
                "• Pips to SL\n"
                "• Dollar risk amount\n"
                "• Recommendation\n\n"
                "💡 TIP: Never risk more than 2%!"
            ),
            "id": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "💰 TUTORIAL: RISK CALCULATOR\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Hitung ukuran posisi yang tepat\n"
                "berdasarkan parameter risiko.\n\n"
                "FORMAT:\n"
                "/risk <balance> <pair> <entry> <sl> [risk%]\n\n"
                "CONTOH:\n"
                "• /risk 1000 EURUSD 1.0850 1.0820\n"
                "  → Balance $1000, risiko 1% (default)\n\n"
                "• /risk 5000 GBPJPY 192.50 191.80 2\n"
                "  → Balance $5000, risiko 2%\n\n"
                "• /risk 10000 XAUUSD 2350 2340 1.5\n"
                "  → Balance $10000, risiko 1.5% Gold\n\n"
                "OUTPUT:\n"
                "• Lot size tepat (standard/mini/micro)\n"
                "• Jarak SL dalam pips\n"
                "• Jumlah risiko dalam dollar\n"
                "• Rekomendasi\n\n"
                "💡 TIP: Jangan risiko lebih dari 2%!"
            ),
        },
        "subscribe": {
            "en": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🔔 TUTORIAL: AUTO UPDATES\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Subscribe to get automatic market\n"
                "updates throughout the day.\n\n"
                "HOW TO SUBSCRIBE:\n"
                "Type /subscribe\n\n"
                "SCHEDULE (WIB):\n"
                "☀️ 07:00 — Morning market briefing\n"
                "🌏 07:15 — Asian session update\n"
                "✨ 08:00 — Daily FX signal\n"
                "🇬🇧 14:00 — London session update\n"
                "🌙 18:00 — Evening wrap-up\n"
                "🇺🇸 19:30 — NY session update\n"
                "🖥 20:00 — US News alert\n"
                "📊 Sun 20:00 — Weekly analysis\n\n"
                "TO UNSUBSCRIBE:\n"
                "Type /unsubscribe\n\n"
                "💡 All times are WIB (Asia/Jakarta)"
            ),
            "id": (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🔔 TUTORIAL: AUTO UPDATES\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Berlangganan untuk menerima update\n"
                "pasar otomatis sepanjang hari.\n\n"
                "CARA BERLANGGANAN:\n"
                "Ketik /subscribe\n\n"
                "JADWAL (WIB):\n"
                "☀️ 07:00 — Briefing pagi\n"
                "🌏 07:15 — Asian session update\n"
                "✨ 08:00 — FX Signal harian\n"
                "🇬🇧 14:00 — London session update\n"
                "🌙 18:00 — Ringkasan sore\n"
                "🇺🇸 19:30 — NY session update\n"
                "🖥 20:00 — US News alert\n"
                "📊 Minggu 20:00 — Analisa mingguan\n\n"
                "BERHENTI LANGGANAN:\n"
                "Ketik /unsubscribe\n\n"
                "💡 Semua waktu dalam WIB (Asia/Jakarta)"
            ),
        },
    }

    topic_data = tutorials.get(topic, tutorials["news"])
    return topic_data.get(lang, topic_data["en"])


# ─────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────
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
    lines = ["🪙 CRYPTO PRICES\n"]
    for p in prices:
        change = p.get("change_24h", 0)
        emoji = "🟢" if change >= 0 else "🔴"
        lines.append(
            f"{emoji} {p['name']}: ${p['price_usd']:,.2f} ({change:+.1f}%)"
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
    app.add_handler(CommandHandler("tutorial", tutorial_command))

    # IMPORTANT: Register callback handler EXCLUDING fx_ and qsig_ patterns
    # Those are handled by fx_handlers.py which is registered separately
    app.add_handler(CallbackQueryHandler(
        button_callback,
        pattern="^(?!fx_|qsig_).*$"
    ))

    logger.info("All handlers registered successfully.")
