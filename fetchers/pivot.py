"""
Pivot Point Calculator module.
Calculates Daily Pivot Points, Support (S1, S2, S3), and Resistance (R1, R2, R3)
using the Standard (Floor) Pivot method.

Formula:
  Pivot (P) = (High + Low + Close) / 3
  R1 = (2 * P) - Low
  S1 = (2 * P) - High
  R2 = P + (High - Low)
  S2 = P - (High - Low)
  R3 = High + 2 * (P - Low)
  S3 = Low - 2 * (High - P)
"""

import logging
from datetime import datetime, timedelta

import httpx

from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)


async def get_pivot_points(pair: str) -> dict:
    """
    Calculate daily pivot points for a given forex pair.
    Uses previous day's High, Low, Close + Open comparison.

    Returns:
        Dict with pivot levels, PDH, PDL, open, prev_open
    """
    pair_clean = pair.upper().replace("/", "")

    try:
        ohlc = await _fetch_ohlc_data(pair_clean)

        if not ohlc or ohlc.get("error"):
            return {"error": True, "message": f"Cannot fetch OHLC for {pair}"}

        high = ohlc["high"]
        low = ohlc["low"]
        close = ohlc["close"]
        open_price = ohlc["open"]
        prev_open = ohlc.get("prev_open", open_price)

        # Calculate pivot points (Standard/Floor method)
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = high + 2 * (pivot - low)
        s3 = low - 2 * (high - pivot)

        # PDH / PDL = Previous Day High / Low
        pdh = high
        pdl = low

        return {
            "pair": pair,
            "open": round(open_price, 5),
            "prev_open": round(prev_open, 5),
            "high": round(high, 5),
            "low": round(low, 5),
            "close": round(close, 5),
            "pivot": round(pivot, 5),
            "r1": round(r1, 5),
            "r2": round(r2, 5),
            "r3": round(r3, 5),
            "s1": round(s1, 5),
            "s2": round(s2, 5),
            "s3": round(s3, 5),
            "pdh": round(pdh, 5),
            "pdl": round(pdl, 5),
            "error": False,
        }

    except Exception as e:
        logger.error(f"Error calculating pivots for {pair}: {e}")
        return {"error": True, "message": str(e)}


async def _fetch_ohlc_data(pair: str) -> dict:
    """
    Fetch previous day OHLC data using AI estimation.
    For production, replace with a proper OHLC API (e.g., Twelve Data, OANDA).
    """
    return await _ai_estimate_ohlc(pair)


async def _ai_estimate_ohlc(pair: str) -> dict:
    """
    Use AI to provide current realistic OHLC data for pivot calculation.
    """
    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )

    formatted_pair = f"{pair[:3]}/{pair[3:]}"

    prompt = f"""You are a forex market data provider. Provide the PREVIOUS TRADING DAY's OHLC candle data for {formatted_pair}, and also the OPEN price from 2 days ago.

Return ONLY these numbers in this exact format (no other text, no explanation):
OPEN: <price>
HIGH: <price>
LOW: <price>
CLOSE: <price>
PREV_OPEN: <open price from 2 days ago>

Rules:
- Use realistic CURRENT market prices (as of today)
- Be precise: 5 decimal places for most pairs, 3 for JPY pairs, 2 for XAUUSD
- HIGH must be the highest, LOW must be the lowest
- OPEN and CLOSE must be between HIGH and LOW"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You provide accurate forex OHLC data. Return only numbers, no explanations."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=100,
        )

        content = response.choices[0].message.content.strip()
        return _parse_ohlc_response(content)

    except Exception as e:
        logger.error(f"AI OHLC estimation failed for {pair}: {e}")
        return {"error": True}


def _parse_ohlc_response(text: str) -> dict:
    """Parse AI OHLC response into dict."""
    result = {}
    for line in text.strip().split("\n"):
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().upper().replace(" ", "_")
        try:
            val = float(value.strip())
            if key == "OPEN":
                result["open"] = val
            elif key == "HIGH":
                result["high"] = val
            elif key == "LOW":
                result["low"] = val
            elif key == "CLOSE":
                result["close"] = val
            elif key == "PREV_OPEN":
                result["prev_open"] = val
        except ValueError:
            continue

    if "open" in result and "high" in result and "low" in result and "close" in result:
        if "prev_open" not in result:
            result["prev_open"] = result["open"]
        return result

    return {"error": True}
