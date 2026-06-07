"""
Market Session Update module.
Provides market direction analysis at the open of each major trading session:
- Asian Session (Tokyo): 00:00 - 09:00 UTC (07:00 - 16:00 WIB)
- London Session: 07:00 - 16:00 UTC (14:00 - 23:00 WIB)
- New York Session: 12:00 - 21:00 UTC (19:00 - 04:00 WIB)
"""

import logging
from datetime import datetime

from openai import AsyncOpenAI

from config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
)

# Session definitions with their characteristics
SESSIONS = {
    "asian": {
        "name": "Asian Session (Tokyo)",
        "emoji": "🌏",
        "hours_utc": "00:00 - 09:00 UTC",
        "hours_wib": "07:00 - 16:00 WIB",
        "pairs": ["USD/JPY", "AUD/USD", "NZD/USD", "AUD/JPY", "EUR/JPY"],
        "characteristics": "Usually lower volatility, range-bound. JPY and AUD pairs most active.",
    },
    "london": {
        "name": "London Session",
        "emoji": "🇬🇧",
        "hours_utc": "07:00 - 16:00 UTC",
        "hours_wib": "14:00 - 23:00 WIB",
        "pairs": ["EUR/USD", "GBP/USD", "EUR/GBP", "USD/CHF", "GBP/JPY"],
        "characteristics": "Highest liquidity. Major breakouts often occur. EUR and GBP pairs most active.",
    },
    "newyork": {
        "name": "New York Session",
        "emoji": "🇺🇸",
        "hours_utc": "12:00 - 21:00 UTC",
        "hours_wib": "19:00 - 04:00 WIB",
        "pairs": ["EUR/USD", "GBP/USD", "USD/CAD", "USD/JPY", "Gold (XAU/USD)"],
        "characteristics": "High volatility, especially during London-NY overlap. US data releases drive moves.",
    },
}


async def get_session_update(session: str, language: str = "en") -> str:
    """
    Generate market direction analysis for a specific trading session.

    Args:
        session: 'asian', 'london', or 'newyork'
        language: 'en' or 'id'

    Returns:
        Formatted session update message
    """
    if session not in SESSIONS:
        return f"⚠️ Unknown session: {session}"

    session_info = SESSIONS[session]
    lang_instruction = (
        "Respond in Bahasa Indonesia." if language == "id"
        else "Respond in English."
    )

    prompt = f"""You are a professional forex session analyst. Provide a market direction update for the {session_info['name']}.

{lang_instruction}

Session Info:
- Session: {session_info['name']}
- Hours: {session_info['hours_utc']} ({session_info['hours_wib']})
- Key Pairs: {', '.join(session_info['pairs'])}
- Characteristics: {session_info['characteristics']}

Provide the following for THIS session:

1. MARKET BIAS
   - Overall direction for the session (Bullish USD / Bearish USD / Neutral)
   - Key driver behind the bias

2. PAIRS TO WATCH (top 3-4 pairs for this session)
   For each pair:
   - Direction bias (Buy/Sell/Neutral)
   - Key level to watch
   - Brief reasoning

3. SESSION OUTLOOK
   - Expected volatility (Low/Medium/High)
   - Key events during this session (if any)
   - Strategy suggestion (range trading / breakout / trend following)

4. RISK NOTES
   - What could invalidate the bias
   - Major news events to be aware of

Format for Telegram with clear sections and emojis. Be concise and actionable.
"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a forex session analyst specializing in {session_info['name']} market analysis. Provide actionable session updates for traders.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=700,
        )

        content = response.choices[0].message.content.strip()
        return _format_session_update(content, session_info)

    except Exception as e:
        logger.error(f"Error generating session update for {session}: {e}")
        return f"⚠️ Failed to generate {session_info['name']} update. Please try again later."


async def get_all_sessions_summary(language: str = "en") -> str:
    """
    Get a brief summary of all session outlooks.

    Args:
        language: 'en' or 'id'

    Returns:
        Combined session summary message
    """
    lang_instruction = (
        "Respond in Bahasa Indonesia." if language == "id"
        else "Respond in English."
    )

    prompt = f"""You are a forex market analyst. Provide a quick overview of market direction for ALL three major trading sessions today.

{lang_instruction}

For each session, provide in 2-3 lines:
1. Asian Session (Tokyo) - USD/JPY, AUD/USD focus
2. London Session - EUR/USD, GBP/USD focus
3. New York Session - Major pairs + US data impact

Include:
- Bias direction for each session
- One key pair to focus on per session
- One key level per session

Keep it concise and actionable. Use emojis for readability.
"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise forex session analyst. Provide brief, actionable session summaries.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=500,
        )

        content = response.choices[0].message.content.strip()

        header = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🌐 SESSION UPDATE - ALL SESSIONS\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        footer = (
            "\n\n━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ AI-generated analysis. Not financial advice.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )

        return f"{header}{content}{footer}"

    except Exception as e:
        logger.error(f"Error generating session summary: {e}")
        return "⚠️ Failed to generate session summary. Please try again later."


def _format_session_update(content: str, session_info: dict) -> str:
    """Format session update with header/footer."""
    header = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{session_info['emoji']} SESSION UPDATE: {session_info['name'].upper()}\n"
        f"⏰ {session_info['hours_wib']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    footer = (
        "\n\n━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ AI-generated analysis. Not financial advice.\n"
        "Always manage your risk.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    return f"{header}{content}{footer}"
