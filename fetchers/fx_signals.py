"""
FX Signal Generator.
Uses AI to generate forex trading signals with specific entry/exit levels
based on current market news, sentiment, and technical context.
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

# Major FX pairs to analyze
FX_PAIRS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF",
    "NZD/USD", "USD/CAD", "EUR/GBP", "EUR/JPY", "GBP/JPY",
]


async def generate_fx_signal(news_context: str = "", language: str = "en") -> dict:
    """
    Generate AI-powered FX trading signal with entry, SL, TP levels.

    Args:
        news_context: Recent forex news for context
        language: 'en' or 'id'

    Returns:
        Dict with signal details
    """
    lang_instruction = (
        "Respond in Bahasa Indonesia." if language == "id"
        else "Respond in English."
    )

    prompt = f"""You are a professional forex analyst. Based on current market conditions and the news context provided, generate ONE high-probability FX trading signal.

{lang_instruction}

News Context:
{news_context if news_context else "Use your knowledge of current market conditions."}

Generate a signal with this EXACT format (keep the labels in English for parsing, but explanation can be in the requested language):

PAIR: [e.g., EUR/USD]
DIRECTION: [BUY or SELL]
ENTRY: [price level]
STOP_LOSS: [price level]
TAKE_PROFIT_1: [price level]
TAKE_PROFIT_2: [price level]
TAKE_PROFIT_3: [price level]
RISK_REWARD: [ratio e.g., 1:2.5]
CONFIDENCE: [HIGH/MEDIUM/LOW]
TIMEFRAME: [e.g., H4, D1]
ANALYSIS: [2-3 sentences explaining the trade setup and reasoning]
KEY_LEVELS: [important support/resistance levels to watch]

Rules:
- Use realistic current market prices
- Stop loss should be at a logical technical level
- Multiple take profit levels for scaling out
- Include risk:reward ratio
- Be specific with price levels (to the pip)
"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert forex trader and analyst. You provide precise trading signals with specific entry and exit levels. Always use realistic current market prices.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=600,
        )

        content = response.choices[0].message.content.strip()
        signal = _parse_signal(content)
        signal["raw_text"] = content
        signal["generated_at"] = datetime.utcnow().isoformat()

        return signal

    except Exception as e:
        logger.error(f"Error generating FX signal: {e}")
        return {
            "error": True,
            "message": str(e),
            "generated_at": datetime.utcnow().isoformat(),
        }


def _parse_signal(text: str) -> dict:
    """Parse the AI-generated signal text into a structured dict."""
    signal = {}
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if ":" not in line:
            continue

        key, _, value = line.partition(":")
        key = key.strip().upper().replace(" ", "_")
        value = value.strip()

        if key == "PAIR":
            signal["pair"] = value
        elif key == "DIRECTION":
            signal["direction"] = value.upper()
        elif key == "ENTRY":
            signal["entry"] = value
        elif key == "STOP_LOSS":
            signal["stop_loss"] = value
        elif key == "TAKE_PROFIT_1":
            signal["tp1"] = value
        elif key == "TAKE_PROFIT_2":
            signal["tp2"] = value
        elif key == "TAKE_PROFIT_3":
            signal["tp3"] = value
        elif key == "RISK_REWARD":
            signal["risk_reward"] = value
        elif key == "CONFIDENCE":
            signal["confidence"] = value
        elif key == "TIMEFRAME":
            signal["timeframe"] = value
        elif key == "ANALYSIS":
            signal["analysis"] = value
        elif key == "KEY_LEVELS":
            signal["key_levels"] = value

    return signal


def format_signal_message(signal: dict) -> str:
    """Format signal dict into a beautiful Telegram message."""
    if signal.get("error"):
        return f"⚠️ Signal generation failed: {signal.get('message', 'Unknown error')}"

    direction = signal.get("direction", "N/A")
    direction_emoji = "🟢 BUY" if "BUY" in direction.upper() else "🔴 SELL"
    confidence = signal.get("confidence", "MEDIUM")

    if "HIGH" in confidence.upper():
        conf_emoji = "🔥🔥🔥"
    elif "MEDIUM" in confidence.upper():
        conf_emoji = "🔥🔥"
    else:
        conf_emoji = "🔥"

    msg = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ FX SIGNAL\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💱 Pair: {signal.get('pair', 'N/A')}\n"
        f"📊 Direction: {direction_emoji}\n"
        f"⏱ Timeframe: {signal.get('timeframe', 'H4')}\n"
        f"🎯 Confidence: {confidence} {conf_emoji}\n\n"
        f"━━ LEVELS ━━\n"
        f"▶️ Entry: {signal.get('entry', 'N/A')}\n"
        f"🛑 Stop Loss: {signal.get('stop_loss', 'N/A')}\n"
        f"✅ TP1: {signal.get('tp1', 'N/A')}\n"
        f"✅ TP2: {signal.get('tp2', 'N/A')}\n"
        f"✅ TP3: {signal.get('tp3', 'N/A')}\n"
        f"📐 Risk:Reward: {signal.get('risk_reward', 'N/A')}\n\n"
        f"━━ ANALYSIS ━━\n"
        f"📝 {signal.get('analysis', 'No analysis available.')}\n\n"
        f"🔑 Key Levels: {signal.get('key_levels', 'N/A')}\n\n"
        f"⚠️ Disclaimer: This is AI-generated analysis, not financial advice.\n"
        f"Always manage your risk properly.\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    return msg
