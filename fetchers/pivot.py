"""
Pivot Point Calculator module.
Fetches REAL OHLC data from Twelve Data API and calculates:
  Pivot (P) = (High + Low + Close) / 3
  R1 = (2 * P) - Low
  S1 = (2 * P) - High
  R2 = P + (High - Low)
  S2 = P - (High - Low)
  R3 = High + 2 * (P - Low)
  S3 = Low - 2 * (High - P)
"""

import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

TWELVE_DATA_BASE = "https://api.twelvedata.com"

# Map pair names to Twelve Data symbols
PAIR_SYMBOL_MAP = {
    "EUR/USD": "EUR/USD",
    "GBP/USD": "GBP/USD",
    "USD/JPY": "USD/JPY",
    "AUD/USD": "AUD/USD",
    "USD/CHF": "USD/CHF",
    "NZD/USD": "NZD/USD",
    "USD/CAD": "USD/CAD",
    "EUR/GBP": "EUR/GBP",
    "EUR/JPY": "EUR/JPY",
    "GBP/JPY": "GBP/JPY",
    "AUD/JPY": "AUD/JPY",
    "EUR/AUD": "EUR/AUD",
    "XAU/USD": "XAU/USD",
    "XAUUSD": "XAU/USD",
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "AUDUSD": "AUD/USD",
    "USDCHF": "USD/CHF",
    "NZDUSD": "NZD/USD",
    "USDCAD": "USD/CAD",
    "EURGBP": "EUR/GBP",
    "EURJPY": "EUR/JPY",
    "GBPJPY": "GBP/JPY",
    "AUDJPY": "AUD/JPY",
    "EURAUD": "EUR/AUD",
}


async def get_pivot_points(pair: str) -> dict:
    """
    Calculate daily pivot points for a given forex pair using REAL data from Twelve Data.

    Args:
        pair: Currency pair (e.g., "XAU/USD", "EURUSD", "EUR/USD")

    Returns:
        Dict with pivot levels, PDH, PDL, open, prev_open
    """
    # Normalize pair name
    pair_upper = pair.upper().replace("/", "")
    symbol = PAIR_SYMBOL_MAP.get(pair.upper(), PAIR_SYMBOL_MAP.get(pair_upper))

    if not symbol:
        # Try to format as XXX/YYY
        if len(pair_upper) == 6:
            symbol = f"{pair_upper[:3]}/{pair_upper[3:]}"
        else:
            symbol = pair.upper()

    try:
        ohlc = await _fetch_ohlc_twelvedata(symbol)

        if not ohlc or ohlc.get("error"):
            return {"error": True, "message": f"Cannot fetch OHLC for {pair}: {ohlc.get('message', 'Unknown error')}"}

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
            "pair": pair if "/" in pair else f"{pair_upper[:3]}/{pair_upper[3:]}",
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


async def _fetch_ohlc_twelvedata(symbol: str) -> dict:
    """
    Fetch previous day and day-before OHLC data from Twelve Data API.

    Returns:
        Dict with open, high, low, close (previous day) and prev_open (2 days ago)
    """
    api_key = settings.TWELVE_DATA_API_KEY

    if not api_key:
        logger.error("TWELVE_DATA_API_KEY not configured!")
        return {"error": True, "message": "Twelve Data API key not configured."}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Get last 2 daily candles
            response = await client.get(
                f"{TWELVE_DATA_BASE}/time_series",
                params={
                    "symbol": symbol,
                    "interval": "1day",
                    "outputsize": 2,
                    "apikey": api_key,
                    "order": "desc",
                },
            )
            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if data.get("status") == "error" or "code" in data:
                error_msg = data.get("message", "Unknown Twelve Data error")
                logger.error(f"Twelve Data API error for {symbol}: {error_msg}")
                return {"error": True, "message": error_msg}

            values = data.get("values", [])

            if not values or len(values) < 1:
                return {"error": True, "message": f"No OHLC data available for {symbol}"}

            # values[0] = most recent completed day (yesterday)
            # values[1] = day before (2 days ago) — for prev_open comparison
            latest = values[0]
            prev_day = values[1] if len(values) > 1 else values[0]

            result = {
                "open": float(latest["open"]),
                "high": float(latest["high"]),
                "low": float(latest["low"]),
                "close": float(latest["close"]),
                "prev_open": float(prev_day["open"]),
                "error": False,
            }

            logger.info(
                f"Twelve Data OHLC for {symbol}: "
                f"O={result['open']} H={result['high']} L={result['low']} C={result['close']} "
                f"PrevO={result['prev_open']}"
            )

            return result

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching Twelve Data for {symbol}: {e}")
        return {"error": True, "message": f"HTTP error: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Error fetching Twelve Data OHLC for {symbol}: {e}")
        return {"error": True, "message": str(e)}
