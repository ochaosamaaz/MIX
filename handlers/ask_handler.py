"""
Ask AI handler - free-form market questions.
Users can ask anything about markets and get AI-powered answers.
"""

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from openai import AsyncOpenAI
from config import settings
from fetchers import fetch_crypto_news, fetch_forex_news
from handlers.commands import get_lang
from utils import split_message as _split_message

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
)


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /ask command - answer any market-related question.
    Usage: /ask <question>
    """
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    if not context.args:
        if lang == "id":
            await update.message.reply_text(
                "🧠 Ask AI - Tanya Apapun Soal Market\n\n"
                "Cara pakai:\n"
                "/ask <pertanyaan>\n\n"
                "Contoh:\n"
                "• /ask Apa dampak kenaikan suku bunga ke EUR/USD?\n"
                "• /ask Bagaimana strategi trading saat NFP?\n"
                "• /ask Analisa teknikal GBP/USD H4\n"
                "• /ask Kenapa BTC turun hari ini?\n"
                "• /ask Apa itu divergence RSI?"
            )
        else:
            await update.message.reply_text(
                "🧠 Ask AI - Ask Anything About Markets\n\n"
                "Usage:\n"
                "/ask <question>\n\n"
                "Examples:\n"
                "• /ask What's the impact of Fed rate hike on USD/JPY?\n"
                "• /ask How to trade NFP news?\n"
                "• /ask Technical analysis GBP/USD H4\n"
                "• /ask Why is BTC dropping today?\n"
                "• /ask What is RSI divergence?"
            )
        return

    question = " ".join(context.args)

    loading_text = (
        "🧠 Thinking..." if lang == "en"
        else "🧠 Sedang berpikir..."
    )
    loading_msg = await update.message.reply_text(loading_text)

    try:
        # Fetch recent market news for context
        news_context = await _get_market_context()

        lang_instruction = (
            "Respond in Bahasa Indonesia." if lang == "id"
            else "Respond in English."
        )

        prompt = f"""You are a professional market analyst and trading mentor on Telegram.
A trader asks you: "{question}"

{lang_instruction}

Recent market context:
{news_context}

Rules:
- Answer clearly and concisely (suitable for Telegram message)
- Use emojis for readability
- If the question is about a specific pair, give actionable levels
- If it's about strategy, give practical tips
- If it's about fundamentals, explain the market impact
- Always add a brief disclaimer at the end
- Keep response under 500 words
- Format for readability with bullet points and sections
"""

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert financial market analyst and trading educator. "
                        "You provide clear, accurate, and actionable market insights. "
                        "You never give guaranteed predictions but offer educated analysis."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=700,
        )

        answer = response.choices[0].message.content.strip()

        header = "🧠 AI Market Analyst\n━━━━━━━━━━━━━━━━━━━━\n\n"
        footer = "\n\n━━━━━━━━━━━━━━━━━━━━\n⚠️ AI-generated analysis. Not financial advice."

        full_reply = f"{header}{answer}{footer}"

        if len(full_reply) > 4000:
            chunks = _split_message(full_reply)
            await loading_msg.edit_text(chunks[0])
            for chunk in chunks[1:]:
                await update.message.reply_text(chunk)
        else:
            await loading_msg.edit_text(full_reply)

    except Exception as e:
        logger.error(f"Error in /ask command: {e}")
        error_text = (
            "⚠️ Gagal mendapatkan jawaban. Coba lagi nanti."
            if lang == "id"
            else "⚠️ Failed to get an answer. Please try again later."
        )
        await loading_msg.edit_text(error_text)


async def _get_market_context() -> str:
    """Get brief market context from recent news."""
    context_parts = []
    try:
        crypto = await fetch_crypto_news(limit=3)
        for a in crypto.get("articles", [])[:3]:
            context_parts.append(f"[Crypto] {a['title']}")

        forex = await fetch_forex_news(limit=3)
        for a in forex.get("articles", [])[:3]:
            context_parts.append(f"[Forex] {a['title']}")
    except Exception as e:
        logger.error(f"Error getting market context for /ask: {e}")

    return "\n".join(context_parts) if context_parts else "No recent context available."


def register_ask_handler(app: Application):
    """Register the /ask command handler."""
    app.add_handler(CommandHandler("ask", ask_command))
    logger.info("Ask AI handler registered.")
