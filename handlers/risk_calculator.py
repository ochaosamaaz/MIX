"""
Risk Calculator handler.
Helps traders calculate proper position size based on their account and risk parameters.
"""

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from handlers.commands import get_lang

logger = logging.getLogger(__name__)

# Pip values for common pairs (per standard lot = 100,000 units)
PIP_VALUES = {
    "EURUSD": 10.0,
    "GBPUSD": 10.0,
    "AUDUSD": 10.0,
    "NZDUSD": 10.0,
    "USDCHF": 10.0,
    "USDCAD": 10.0,
    "USDJPY": 6.5,
    "EURJPY": 6.5,
    "GBPJPY": 6.5,
    "AUDJPY": 6.5,
    "EURGBP": 12.5,
    "EURAUD": 10.0,
    "XAUUSD": 10.0,
}


async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /risk command - calculate position size.

    Usage: /risk <balance> <pair> <entry> <stoploss> [risk%]
    Examples:
    /risk 1000 EURUSD 1.0850 1.0820
    /risk 5000 GBPJPY 192.50 191.80 2
    /risk 10000 XAUUSD 2350.00 2340.00 1.5
    """
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    if not context.args or len(context.args) < 4:
        await _send_usage(update, lang)
        return

    try:
        balance = float(context.args[0])
        pair = context.args[1].upper().replace("/", "")
        entry = float(context.args[2])
        stoploss = float(context.args[3])
        risk_percent = float(context.args[4]) if len(context.args) > 4 else 1.0

        if balance <= 0:
            await update.message.reply_text("⚠️ Balance must be greater than 0.")
            return
        if risk_percent <= 0 or risk_percent > 100:
            await update.message.reply_text("⚠️ Risk percent must be between 0.01 and 100.")
            return
        if entry == stoploss:
            await update.message.reply_text("⚠️ Entry and Stop Loss cannot be the same.")
            return

        direction = "BUY" if entry > stoploss else "SELL"
        pips = _calculate_pips(pair, entry, stoploss)
        if pips <= 0:
            await update.message.reply_text("⚠️ Invalid entry/stoploss combination.")
            return

        risk_amount = balance * (risk_percent / 100)
        pip_value = _get_pip_value(pair)
        lot_size = risk_amount / (pips * pip_value)

        message = _format_risk_result(
            balance=balance, pair=pair, direction=direction,
            entry=entry, stoploss=stoploss, risk_percent=risk_percent,
            risk_amount=risk_amount, pips=pips, pip_value=pip_value,
            lot_size=lot_size, lang=lang,
        )
        await update.message.reply_text(message)

    except ValueError:
        await update.message.reply_text(
            "⚠️ Invalid numbers. Check your input.\n\n"
            "Format: /risk <balance> <pair> <entry> <stoploss> [risk%]\n"
            "Example: /risk 1000 EURUSD 1.0850 1.0820 1"
        )
    except Exception as e:
        logger.error(f"Error in /risk command: {e}")
        await update.message.reply_text("⚠️ Error calculating risk. Please try again.")


def _calculate_pips(pair: str, entry: float, stoploss: float) -> float:
    """Calculate the number of pips between entry and stoploss."""
    diff = abs(entry - stoploss)
    if "JPY" in pair:
        return diff / 0.01
    elif "XAU" in pair:
        return diff / 0.10
    else:
        return diff / 0.0001


def _get_pip_value(pair: str) -> float:
    """Get pip value per standard lot for a pair."""
    return PIP_VALUES.get(pair.replace("/", ""), 10.0)


def _format_risk_result(
    balance, pair, direction, entry, stoploss,
    risk_percent, risk_amount, pips, pip_value, lot_size, lang
) -> str:
    """Format the risk calculation result."""
    direction_emoji = "🟢 BUY" if direction == "BUY" else "🔴 SELL"

    if lang == "id":
        msg = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💰 KALKULATOR RISIKO\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💼 Balance: ${balance:,.2f}\n"
            f"💱 Pair: {pair}\n"
            f"📊 Arah: {direction_emoji}\n\n"
            f"━━ PARAMETER ━━\n"
            f"▶️ Entry: {entry}\n"
            f"🛑 Stop Loss: {stoploss}\n"
            f"📏 Jarak SL: {pips:.1f} pips\n"
            f"⚠️ Risiko: {risk_percent}% = ${risk_amount:.2f}\n\n"
            f"━━ HASIL ━━\n"
            f"📐 Lot Size: {lot_size:.2f} lot\n"
            f"📐 Mini Lot: {lot_size * 10:.1f} mini lot\n"
            f"📐 Micro Lot: {lot_size * 100:.0f} micro lot\n\n"
        )
    else:
        msg = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💰 RISK CALCULATOR\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💼 Balance: ${balance:,.2f}\n"
            f"💱 Pair: {pair}\n"
            f"📊 Direction: {direction_emoji}\n\n"
            f"━━ PARAMETERS ━━\n"
            f"▶️ Entry: {entry}\n"
            f"🛑 Stop Loss: {stoploss}\n"
            f"📏 SL Distance: {pips:.1f} pips\n"
            f"⚠️ Risk: {risk_percent}% = ${risk_amount:.2f}\n\n"
            f"━━ RESULT ━━\n"
            f"📐 Lot Size: {lot_size:.2f} standard lot\n"
            f"📐 Mini Lot: {lot_size * 10:.1f} mini ({lot_size * 10 * 0.1:.2f} lot)\n"
            f"📐 Micro Lot: {lot_size * 100:.0f} micro ({lot_size * 100 * 0.01:.2f} lot)\n\n"
        )

    # Recommendation
    if lot_size >= 1:
        recommendation = f"✅ Recommended: {lot_size:.2f} lot"
    elif lot_size >= 0.1:
        recommendation = f"✅ Recommended: {lot_size:.2f} lot ({lot_size * 10:.1f} mini)"
    else:
        recommendation = f"✅ Recommended: {lot_size:.3f} lot ({lot_size * 100:.1f} micro)"

    msg += f"{recommendation}\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "💡 Tip: Never risk more than 1-2% per trade.\n"
    msg += "━━━━━━━━━━━━━━━━━━━━"

    return msg


async def _send_usage(update: Update, lang: str):
    """Send usage instructions."""
    if lang == "id":
        text = (
            "💰 Kalkulator Risiko - Ukuran Posisi\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Cara pakai:\n"
            "/risk <balance> <pair> <entry> <stoploss> [risk%]\n\n"
            "Contoh:\n"
            "• /risk 1000 EURUSD 1.0850 1.0820\n"
            "  (default risiko 1%)\n\n"
            "• /risk 5000 GBPJPY 192.50 191.80 2\n"
            "  (risiko 2%)\n\n"
            "• /risk 10000 XAUUSD 2350.00 2340.00 1.5\n"
            "  (Gold, risiko 1.5%)\n\n"
            "Pair yang didukung:\n"
            "EURUSD, GBPUSD, USDJPY, AUDUSD, USDCHF,\n"
            "NZDUSD, USDCAD, EURGBP, EURJPY, GBPJPY,\n"
            "AUDJPY, EURAUD, XAUUSD (Gold)\n\n"
            "💡 Default risk: 1% dari balance"
        )
    else:
        text = (
            "💰 Risk Calculator - Position Sizing\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Usage:\n"
            "/risk <balance> <pair> <entry> <stoploss> [risk%]\n\n"
            "Examples:\n"
            "• /risk 1000 EURUSD 1.0850 1.0820\n"
            "  (default 1% risk)\n\n"
            "• /risk 5000 GBPJPY 192.50 191.80 2\n"
            "  (2% risk)\n\n"
            "• /risk 10000 XAUUSD 2350.00 2340.00 1.5\n"
            "  (Gold, 1.5% risk)\n\n"
            "Supported pairs:\n"
            "EURUSD, GBPUSD, USDJPY, AUDUSD, USDCHF,\n"
            "NZDUSD, USDCAD, EURGBP, EURJPY, GBPJPY,\n"
            "AUDJPY, EURAUD, XAUUSD (Gold)\n\n"
            "💡 Default risk: 1% of balance"
        )

    await update.message.reply_text(text)


def register_risk_handler(app: Application):
    """Register the /risk command handler."""
    app.add_handler(CommandHandler("risk", risk_command))
    logger.info("Risk Calculator handler registered.")
