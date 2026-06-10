"""
Market Session Update module.
Provides market direction analysis at the open of each major trading session.
Now uses REAL prices from Twelve Data API so key levels are accurate.
"""

import logging
from datetime import datetime

import httpx
from openai import AsyncOpenAI

from config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
)

TWELVE_DATA_BASE = "https://api.twelvedata.com"

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
        "pairs": ["EUR/USD", "GBP/USD", "USD/CAD", "USD/JPY", "XAU/USD"],
        "characteristics": "High volatility, especially during London-NY overlap. US data releases drive moves.",
    },
}


async def _get_live_prices(pairs: list[str]) -> dict:
    """
    Fetch live prices for multiple pairs from Twelve Data.
    Returns dict like {"EUR/USD": 1.15724, "XAU/USD": 4331.59, ...}
    """
    api_key = settings.TWELVE_DATA_API_KEY
    if not api_key:
        return {}

    prices = {}
    # Twelve Data supports comma-separated symbols
    symbols = ",".join(pairs)

    try:
        async with httpx.AsyncClient(timeout=15) as http_client:
            response = await http_client.get(
                f"{TWELVE_DATA_BASE}/price",
                params={"symbol": symbols, "apikey": api_key},
            )
            response.raise_for_status()
            data = response.json()

            # Single symbol returns {"price": "..."}
            # Multiple symbols returns {"SYMBOL": {"price": "..."}, ...}
            if "price" in data:
                # Single symbol case
                if len(pairs) == 1:
                    prices[pairs[0]] = float(data["price"])
            else:
                for symbol, val in data.items():
                    if isinstance(val, dict) and "price" in val:
                        prices[symbol] = float(val["price"])

    except Exception as e:
        logger.error(f"Error fetching live prices: {e}")

    return prices


async def get_session_update(session: str, language: str = "en") -> str:
    """
    Generate market direction analysis for a specific trading session.
    Uses REAL live prices from Twelve Data for accurate key levels.
    """
    if session not in SESSIONS:
        return f"⚠️ Unknown session: {session}"

    session_info = SESSIONS[session]
    lang_instruction = (
        "Respond in Bahasa Indonesia." if language == "id"
        else "Respond in English."
    )

    # Fetch REAL live prices for session pairs
    live_prices = await _get_live_prices(session_info["pairs"])

    # Build price context for the AI
    price_context = ""
    if live_prices:
        price_lines = []
        for pair, price in live_prices.items():
            price_lines.append(f"  {pair}: {price}")
        price_context = "CURRENT LIVE PRICES (use these for key levels!):\n" + "\n".join(price_lines)
    else:
        price_context = "Note: Live prices unavailable. Use your best estimates based on recent market data."

    prompt = f"""You are a professional forex session analyst. Provide a market direction update for the {session_info['name']}.

{lang_instruction}

Session Info:
- Session: {session_info['name']}
- Hours: {session_info['hours_utc']} ({session_info['hours_wib']})
- Key Pairs: {', '.join(session_info['pairs'])}
- Characteristics: {session_info['characteristics']}

{price_context}

IMPORTANT: Use the CURRENT LIVE PRICES above for all key levels. Do NOT use outdated prices.
Key levels should be within realistic range of the current price (e.g., within 50-200 pips for forex, within $30-100 for Gold).

Provide the following for THIS session:

1. MARKET BIAS
   - Overall direction for the session (Bullish USD / Bearish USD / Neutral)
   - Key driver behind the bias

2. PAIRS TO WATCH (top 3-4 pairs for this session)
   For each pair:
   - Direction bias (Buy/Sell/Neutral)
   - Key level to watch (MUST be near the current live price!)
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
                    "content": (
                        f"You are a forex session analyst specializing in {session_info['name']} market analysis. "
                        f"You ALWAYS use current market prices for key levels. Never use outdated prices."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=700,
        )

        content = response.choices[0].message.content.strip()
        return _format_session_update(content, session_info, live_prices)

    except Exception as e:
        logger.error(f"Error generating session update for {session}: {e}")
        return f"⚠️ Failed to generate {session_info['name']} update. Please try again later."


async def get_all_sessions_summary(language: str = "en") -> str:
    """
    Get a brief summary of all session outlooks with real prices.
    """
    lang_instruction = (
        "Respond in Bahasa Indonesia." if language == "id"
        else "Respond in English."
    )

    # Fetch prices for major pairs
    major_pairs = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "XAU/USD"]
    live_prices = await _get_live_prices(major_pairs)

    price_context = ""
    if live_prices:
        price_lines = [f"  {pair}: {price}" for pair, price in live_prices.items()]
        price_context = "CURRENT LIVE PRICES:\n" + "\n".join(price_lines)

    prompt = f"""You are a forex market analyst. Provide a quick overview of market direction for ALL three major trading sessions today.

{lang_instruction}

{price_context}

IMPORTANT: Use the CURRENT LIVE PRICES above for all key levels. Do NOT use outdated prices.

For each session, provide in 2-3 lines:
1. Asian Session (Tokyo) - USD/JPY, AUD/USD focus
2. London Session - EUR/USD, GBP/USD focus
3. New York Session - Major pairs + US data impact

Include:
- Bias direction for each session
- One key pair to focus on per session
- One key level per session (must be near current price!)

Keep it concise and actionable. Use emojis for readability.
"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise forex session analyst. Always use current market prices for levels.",
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


def _format_session_update(content: str, session_info: dict, live_prices: dict = None) -> str:
    """Format session update with header/footer and live price info."""
    header = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{session_info['emoji']} SESSION UPDATE: {session_info['name'].upper()}\n"
        f"⏰ {session_info['hours_wib']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    # Add live prices header if available
    prices_header = ""
    if live_prices:
        price_lines = []
        for pair, price in live_prices.items():
            if "JPY" in pair:
                price_lines.append(f"  {pair}: {price:.3f}")
            elif "XAU" in pair:
                price_lines.append(f"  {pair}: {price:.2f}")
            else:
                price_lines.append(f"  {pair}: {price:.5f}")
        prices_header = "📍 Live Prices:\n" + "\n".join(price_lines) + "\n\n"

    footer = (
        "\n\n━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ AI-generated analysis. Not financial advice.\n"
        "Always manage your risk.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    return f"{header}{prices_header}{content}{footer}"
