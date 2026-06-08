"""
Signal TP/SL Monitoring module.
Tracks active signals and sends notifications when TP or SL is hit.
Uses Twelve Data API to check live prices.
"""

import logging
from datetime import datetime, timedelta

import httpx

from telegram.ext import ContextTypes

from config import settings

logger = logging.getLogger(__name__)

TWELVE_DATA_BASE = "https://api.twelvedata.com"

# In-memory storage for active signals
active_signals: list[dict] = []

# Max signal age (hours) before auto-expiring
MAX_SIGNAL_AGE_HOURS = 24


def add_active_signal(signal: dict):
    """Add a signal to the active monitoring list."""
    if signal.get("error"):
        return

    try:
        entry = _parse_price(signal.get("entry", 0))
        sl = _parse_price(signal.get("stop_loss", 0))
        tp1 = _parse_price(signal.get("tp1", 0))
        tp2 = _parse_price(signal.get("tp2", 0))
        tp3 = _parse_price(signal.get("tp3", 0))
    except (ValueError, TypeError):
        logger.error(f"Cannot parse signal prices for monitoring: {signal.get('pair')}")
        return

    if not entry or not sl:
        return

    tracked = {
        "pair": signal.get("pair", ""),
        "direction": signal.get("direction", ""),
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "tp1_hit": False,
        "tp2_hit": False,
        "tp3_hit": False,
        "sl_hit": False,
        "closed": False,
        "session": signal.get("session", "auto"),
        "created_at": datetime.utcnow().isoformat(),
    }

    active_signals.append(tracked)
    logger.info(f"Signal added to monitor: {tracked['pair']} {tracked['direction']} @ {entry}")


def _parse_price(value) -> float:
    """Parse price value from string or float."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = "".join(c for c in value if c.isdigit() or c == ".")
        return float(cleaned) if cleaned else 0.0
    return 0.0


def get_active_signals() -> list[dict]:
    """Get all currently active (non-closed) signals."""
    return [s for s in active_signals if not s["closed"]]


async def check_signals(context: ContextTypes.DEFAULT_TYPE):
    """
    Check all active signals against current market price.
    Called every 5 minutes by the scheduler.
    """
    if not active_signals:
        return

    _cleanup_expired_signals()

    signals_to_check = [s for s in active_signals if not s["closed"]]
    if not signals_to_check:
        return

    pairs = list(set(s["pair"] for s in signals_to_check))

    for pair in pairs:
        try:
            current_price = await _get_current_price(pair)
            if current_price is None:
                continue

            pair_signals = [s for s in signals_to_check if s["pair"] == pair]

            for signal in pair_signals:
                notifications = _check_signal_levels(signal, current_price)
                for notif in notifications:
                    await _send_notification(context, notif, signal, current_price)

        except Exception as e:
            logger.error(f"Error checking signal for {pair}: {e}")


def _check_signal_levels(signal: dict, current_price: float) -> list[str]:
    """Check if current price has hit any TP or SL levels."""
    notifications = []
    direction = signal["direction"]

    if direction == "BUY":
        if not signal["tp1_hit"] and signal["tp1"] and current_price >= signal["tp1"]:
            signal["tp1_hit"] = True
            notifications.append("tp1")
        if not signal["tp2_hit"] and signal["tp2"] and current_price >= signal["tp2"]:
            signal["tp2_hit"] = True
            notifications.append("tp2")
        if not signal["tp3_hit"] and signal["tp3"] and current_price >= signal["tp3"]:
            signal["tp3_hit"] = True
            signal["closed"] = True
            notifications.append("tp3")
        if not signal["sl_hit"] and signal["sl"] and current_price <= signal["sl"]:
            signal["sl_hit"] = True
            signal["closed"] = True
            notifications.append("sl")
    else:  # SELL
        if not signal["tp1_hit"] and signal["tp1"] and current_price <= signal["tp1"]:
            signal["tp1_hit"] = True
            notifications.append("tp1")
        if not signal["tp2_hit"] and signal["tp2"] and current_price <= signal["tp2"]:
            signal["tp2_hit"] = True
            notifications.append("tp2")
        if not signal["tp3_hit"] and signal["tp3"] and current_price <= signal["tp3"]:
            signal["tp3_hit"] = True
            signal["closed"] = True
            notifications.append("tp3")
        if not signal["sl_hit"] and signal["sl"] and current_price >= signal["sl"]:
            signal["sl_hit"] = True
            signal["closed"] = True
            notifications.append("sl")

    return notifications


async def _send_notification(context: ContextTypes.DEFAULT_TYPE, notif_type: str, signal: dict, current_price: float):
    """Send TP/SL hit notification to channel and subscribers."""
    pair = signal["pair"]
    direction = signal["direction"]
    entry = signal["entry"]

    if "JPY" in pair.upper():
        pip_div = 0.01
        fmt = ".3f"
    elif "XAU" in pair.upper():
        pip_div = 0.10
        fmt = ".2f"
    else:
        pip_div = 0.0001
        fmt = ".5f"

    if direction == "BUY":
        pips = (current_price - entry) / pip_div
    else:
        pips = (entry - current_price) / pip_div

    if notif_type == "sl":
        emoji = "🛑"
        status = "STOP LOSS HIT"
        result_emoji = "❌"
        pips_text = f"{pips:+.1f} pips"
    elif notif_type == "tp1":
        emoji = "✅"
        status = "TP1 HIT"
        result_emoji = "💰"
        pips_text = f"+{abs(pips):.1f} pips"
    elif notif_type == "tp2":
        emoji = "✅✅"
        status = "TP2 HIT"
        result_emoji = "💰💰"
        pips_text = f"+{abs(pips):.1f} pips"
    elif notif_type == "tp3":
        emoji = "✅✅✅"
        status = "TP3 HIT — FULL TARGET"
        result_emoji = "🏆💰💰💰"
        pips_text = f"+{abs(pips):.1f} pips"
    else:
        return

    dir_emoji = "🟢" if direction == "BUY" else "🔴"

    message = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} SIGNAL UPDATE\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{result_emoji} {status}\n\n"
        f"💱 Pair: {pair}\n"
        f"📊 Direction: {dir_emoji} {direction}\n"
        f"▶️ Entry: {entry:{fmt}}\n"
        f"📍 Current: {current_price:{fmt}}\n"
        f"📏 Result: {pips_text}\n\n"
    )

    if notif_type == "sl":
        message += (
            f"🛑 Stop Loss: {signal['sl']:{fmt}}\n\n"
            f"📋 Trade closed at loss.\n"
            f"Risk management protected the account.\n"
        )
    else:
        message += f"🎯 Target: {signal.get(notif_type, current_price):{fmt}}\n\n"
        if notif_type == "tp1":
            message += "📋 Consider moving SL to breakeven.\n"
        elif notif_type == "tp2":
            message += "📋 Take partial profit. Trail stop.\n"
        elif notif_type == "tp3":
            message += "📋 Full target hit! Trade complete. 🎉\n"

    if signal["closed"]:
        message += "\n🔒 Signal CLOSED.\n"
    else:
        remaining = []
        if not signal["tp2_hit"]:
            remaining.append("TP2")
        if not signal["tp3_hit"]:
            remaining.append("TP3")
        if remaining:
            message += f"\n⏳ Remaining targets: {', '.join(remaining)}\n"

    message += "━━━━━━━━━━━━━━━━━━━━"

    # Send to channel
    channel_id = settings.CHANNEL_ID
    if channel_id:
        try:
            await context.bot.send_message(chat_id=channel_id, text=message)
            logger.info(f"Sent {notif_type} notification to channel for {pair}")
        except Exception as e:
            logger.error(f"Failed to send notification to channel: {e}")

    # Send to subscribers
    from scheduler.jobs import subscribers
    for chat_id, prefs in list(subscribers.items()):
        if prefs.get("fx_signals", True):
            try:
                await context.bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                logger.error(f"Failed to send notification to {chat_id}: {e}")


async def _get_current_price(pair: str) -> float | None:
    """Get current price from Twelve Data API."""
    api_key = settings.TWELVE_DATA_API_KEY
    if not api_key:
        return None

    pair_upper = pair.upper().replace("/", "")
    if len(pair_upper) == 6:
        symbol = f"{pair_upper[:3]}/{pair_upper[3:]}"
    else:
        symbol = pair

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{TWELVE_DATA_BASE}/price",
                params={"symbol": symbol, "apikey": api_key},
            )
            response.raise_for_status()
            data = response.json()

            if "price" in data:
                return float(data["price"])
            return None

    except Exception as e:
        logger.error(f"Error fetching price for {pair}: {e}")
        return None


def _cleanup_expired_signals():
    """Remove signals older than MAX_SIGNAL_AGE_HOURS."""
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=MAX_SIGNAL_AGE_HOURS)

    for signal in active_signals:
        if signal["closed"]:
            continue
        try:
            created = datetime.fromisoformat(signal["created_at"])
            if created < cutoff:
                signal["closed"] = True
                logger.info(f"Expired signal: {signal['pair']} {signal['direction']}")
        except (ValueError, KeyError):
            pass
