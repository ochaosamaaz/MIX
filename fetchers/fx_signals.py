"""
FX Signal Generator — Quantum Physics Trading Algorithm.

Theory:
  If Open Price < Previous Open → Sweep PDL (Down)
  If Open Price > Previous Open → Sweep PDH (Up)

  After mission complete (took PDL or PDH), price follows structure/trend.
  Down doesn't mean bearish — after sweeping PDL, price can rebound (and vice versa).

Entry Setup (using Pivot Points):
  UP   → Entry at Pivot and S1 (buy the dip)
  DOWN → Entry at Pivot and R1 (sell the rally)

Validation:
  If DOWN and Open is BELOW Pivot → Entry at Pivot is INVALID (use R1 only)
  If UP and Open is ABOVE Pivot → Entry at Pivot is INVALID (use S1 only)
"""

import logging
from datetime import datetime

from openai import AsyncOpenAI

from config import settings
from fetchers.pivot import get_pivot_points

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
)

# Session-specific pairs
SESSION_PAIRS = {
    "asian": ["USD/JPY", "AUD/USD", "NZD/USD", "EUR/JPY", "AUD/JPY"],
    "london": ["EUR/USD", "GBP/USD", "EUR/GBP", "GBP/JPY", "USD/CHF"],
    "newyork": ["EUR/USD", "GBP/USD", "USD/CAD", "USD/JPY", "XAU/USD"],
}


async def generate_quantum_signal(session: str = "london", language: str = "en") -> dict:
    """
    Generate FX signal using the Quantum Physics Trading Algorithm.

    1. Get pivot points for session pairs
    2. Determine bias (Open vs Previous Open → PDH/PDL sweep)
    3. Calculate entry based on Pivot/S1/R1 with validation
    4. Use AI for final analysis and confirmation

    Args:
        session: 'asian', 'london', or 'newyork'
        language: 'en' or 'id'

    Returns:
        Dict with complete signal info
    """
    pairs = SESSION_PAIRS.get(session, SESSION_PAIRS["london"])

    # Analyze each pair and find the best setup
    best_setup = None
    all_analyses = []

    for pair in pairs[:3]:  # Analyze top 3 pairs for the session
        try:
            pivots = await get_pivot_points(pair)
            if pivots.get("error"):
                continue

            analysis = _analyze_quantum_bias(pivots)
            all_analyses.append(analysis)

            # Pick the best setup (valid entry with clear bias)
            if analysis.get("valid_entry") and (
                best_setup is None or analysis["confidence_score"] > best_setup["confidence_score"]
            ):
                best_setup = analysis

        except Exception as e:
            logger.error(f"Error analyzing {pair}: {e}")
            continue

    if not best_setup:
        # If no valid setup found, use AI to generate based on all analyses
        best_setup = all_analyses[0] if all_analyses else None

    if not best_setup:
        return {
            "error": True,
            "message": "No valid quantum setup found for this session.",
            "session": session,
        }

    # Use AI to refine and confirm the signal
    signal = await _ai_refine_signal(best_setup, session, language)

    return signal


def _analyze_quantum_bias(pivots: dict) -> dict:
    """
    Apply Quantum Physics theory to determine market bias and entry.

    Rules:
    - Open < Prev Open → DOWN (Sweep PDL)
    - Open > Prev Open → UP (Sweep PDH)

    Entry:
    - UP → Entry at Pivot (buy) and S1 (buy)
    - DOWN → Entry at Pivot (sell) and R1 (sell)

    Validation:
    - DOWN + Open below Pivot → Pivot entry INVALID
    - UP + Open above Pivot → Pivot entry INVALID
    """
    pair = pivots["pair"]
    open_price = pivots["open"]
    prev_open = pivots["prev_open"]
    pivot = pivots["pivot"]
    r1 = pivots["r1"]
    s1 = pivots["s1"]
    pdh = pivots["pdh"]
    pdl = pivots["pdl"]

    # Determine quantum bias
    if open_price < prev_open:
        bias = "DOWN"
        mission = "Sweep PDL"
        target_level = pdl
    else:
        bias = "UP"
        mission = "Sweep PDH"
        target_level = pdh

    # Determine entry levels
    entry_levels = []
    valid_entry = True
    pivot_valid = True

    if bias == "DOWN":
        # DOWN → Sell at Pivot and R1
        # Validation: If Open < Pivot → Pivot entry INVALID
        if open_price < pivot:
            pivot_valid = False
            entry_levels = [{"level": r1, "name": "R1", "type": "SELL"}]
        else:
            entry_levels = [
                {"level": pivot, "name": "Pivot", "type": "SELL"},
                {"level": r1, "name": "R1", "type": "SELL"},
            ]
        direction = "SELL"
        sl_level = r1 if not pivot_valid else pivots["r2"]
        tp1 = pdl
        tp2 = s1
        tp3 = pivots["s2"]

    else:  # UP
        # UP → Buy at Pivot and S1
        # Validation: If Open > Pivot → Pivot entry INVALID
        if open_price > pivot:
            pivot_valid = False
            entry_levels = [{"level": s1, "name": "S1", "type": "BUY"}]
        else:
            entry_levels = [
                {"level": pivot, "name": "Pivot", "type": "BUY"},
                {"level": s1, "name": "S1", "type": "BUY"},
            ]
        direction = "BUY"
        sl_level = s1 if not pivot_valid else pivots["s2"]
        tp1 = pdh
        tp2 = r1
        tp3 = pivots["r2"]

    # Primary entry = first valid level
    primary_entry = entry_levels[0]["level"] if entry_levels else pivot

    # Calculate confidence score
    confidence_score = 70  # Base
    if pivot_valid:
        confidence_score += 10  # Pivot entry valid = stronger
    # If bias is clear (large gap between open and prev_open)
    gap = abs(open_price - prev_open)
    avg_range = abs(pdh - pdl) if pdh != pdl else 0.001
    if gap / avg_range > 0.3:
        confidence_score += 15  # Strong gap = higher confidence

    confidence_score = min(confidence_score, 95)

    return {
        "pair": pair,
        "bias": bias,
        "mission": mission,
        "direction": direction,
        "target_level": target_level,
        "entry_levels": entry_levels,
        "primary_entry": primary_entry,
        "pivot_valid": pivot_valid,
        "sl": sl_level,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "pivots": pivots,
        "confidence_score": confidence_score,
        "valid_entry": True,
        "open_price": open_price,
        "prev_open": prev_open,
    }


async def _ai_refine_signal(setup: dict, session: str, language: str) -> dict:
    """
    Use AI to refine the quantum signal with market context and analysis.
    """
    lang_instruction = (
        "Respond in Bahasa Indonesia." if language == "id"
        else "Respond in English."
    )

    pair = setup["pair"]
    bias = setup["bias"]
    direction = setup["direction"]
    pivots = setup["pivots"]

    # Determine decimal format
    if "JPY" in pair.upper():
        fmt = ".3f"
    elif "XAU" in pair.upper():
        fmt = ".2f"
    else:
        fmt = ".5f"

    prompt = f"""You are a professional forex analyst using the Quantum Physics Trading Algorithm.

{lang_instruction}

SIGNAL DATA:
- Pair: {pair}
- Quantum Bias: {bias} (Mission: {setup['mission']})
- Open: {setup['open_price']:{fmt}} | Prev Open: {setup['prev_open']:{fmt}}
- Direction: {direction}
- Entry: {setup['primary_entry']:{fmt}} ({setup['entry_levels'][0]['name'] if setup['entry_levels'] else 'Pivot'})
- Stop Loss: {setup['sl']:{fmt}}
- TP1: {setup['tp1']:{fmt}} | TP2: {setup['tp2']:{fmt}} | TP3: {setup['tp3']:{fmt}}
- Pivot Valid: {setup['pivot_valid']}
- PDH: {pivots['pdh']:{fmt}} | PDL: {pivots['pdl']:{fmt}}
- Pivot: {pivots['pivot']:{fmt}} | R1: {pivots['r1']:{fmt}} | S1: {pivots['s1']:{fmt}}

Session: {session.upper()}

Provide a brief 2-3 sentence ANALYSIS explaining:
1. Why the quantum bias is {bias} (open vs prev open logic)
2. The entry setup and what to watch for
3. What happens after the PDL/PDH sweep mission completes

Keep it concise and actionable. Maximum 3 sentences.
"""

    analysis_text = ""
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a forex analyst specializing in the Quantum Physics Trading Algorithm. Be concise and precise."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=200,
        )
        analysis_text = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"AI refinement failed: {e}")
        analysis_text = f"Quantum bias: {bias}. {setup['mission']} in progress."

    # Build final signal dict
    signal = {
        "pair": pair,
        "session": session,
        "bias": bias,
        "mission": setup["mission"],
        "direction": direction,
        "entry": setup["primary_entry"],
        "entry_name": setup["entry_levels"][0]["name"] if setup["entry_levels"] else "Pivot",
        "alt_entry": setup["entry_levels"][1]["level"] if len(setup["entry_levels"]) > 1 else None,
        "alt_entry_name": setup["entry_levels"][1]["name"] if len(setup["entry_levels"]) > 1 else None,
        "stop_loss": setup["sl"],
        "tp1": setup["tp1"],
        "tp2": setup["tp2"],
        "tp3": setup["tp3"],
        "pivot": pivots["pivot"],
        "r1": pivots["r1"],
        "s1": pivots["s1"],
        "pdh": pivots["pdh"],
        "pdl": pivots["pdl"],
        "pivot_valid": setup["pivot_valid"],
        "confidence_score": setup["confidence_score"],
        "analysis": analysis_text,
        "open_price": setup["open_price"],
        "prev_open": setup["prev_open"],
        "generated_at": datetime.utcnow().isoformat(),
        "error": False,
    }

    return signal


def format_quantum_signal(signal: dict) -> str:
    """Format Quantum Physics signal into a beautiful Telegram message."""
    if signal.get("error"):
        return f"⚠️ {signal.get('message', 'No valid signal for this session.')}"

    pair = signal["pair"]
    bias = signal["bias"]
    direction = signal["direction"]
    session = signal.get("session", "unknown").upper()

    # Determine decimal format
    if "JPY" in pair.upper():
        fmt = ".3f"
    elif "XAU" in pair.upper():
        fmt = ".2f"
    else:
        fmt = ".5f"

    # Direction emoji
    dir_emoji = "🟢 BUY (Long)" if direction == "BUY" else "🔴 SELL (Short)"

    # Bias emoji
    bias_emoji = "⬆️ UP" if bias == "UP" else "⬇️ DOWN"

    # Confidence
    conf = signal["confidence_score"]
    if conf >= 80:
        conf_bar = "🔥🔥🔥 HIGH"
    elif conf >= 65:
        conf_bar = "🔥🔥 MEDIUM"
    else:
        conf_bar = "🔥 LOW"

    # Session emoji
    session_emojis = {"ASIAN": "🌏", "LONDON": "🇬🇧", "NEWYORK": "🇺🇸"}
    sess_emoji = session_emojis.get(session, "🌐")

    # Build entry section
    entry_text = f"▶️ Entry: {signal['entry']:{fmt}} ({signal['entry_name']})"
    if signal.get("alt_entry"):
        entry_text += f"\n▶️ Alt Entry: {signal['alt_entry']:{fmt}} ({signal['alt_entry_name']})"

    # Pivot validity note
    pivot_note = ""
    if not signal["pivot_valid"]:
        if bias == "DOWN":
            pivot_note = "⚠️ Pivot entry INVALID (Open below Pivot)"
        else:
            pivot_note = "⚠️ Pivot entry INVALID (Open above Pivot)"

    msg = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚛️ QUANTUM SIGNAL {sess_emoji} {session}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💱 Pair: {pair}\n"
        f"📊 Direction: {dir_emoji}\n"
        f"⚛️ Quantum Bias: {bias_emoji}\n"
        f"🎯 Mission: {signal['mission']}\n"
        f"🎖 Confidence: {conf}% {conf_bar}\n\n"
        f"━━ QUANTUM LOGIC ━━\n"
        f"📍 Open: {signal['open_price']:{fmt}}\n"
        f"📍 Prev Open: {signal['prev_open']:{fmt}}\n"
        f"{'Open < Prev Open → Sweep PDL ⬇️' if bias == 'DOWN' else 'Open > Prev Open → Sweep PDH ⬆️'}\n\n"
        f"━━ ENTRY & LEVELS ━━\n"
        f"{entry_text}\n"
        f"🛑 Stop Loss: {signal['stop_loss']:{fmt}}\n"
        f"✅ TP1: {signal['tp1']:{fmt}}\n"
        f"✅ TP2: {signal['tp2']:{fmt}}\n"
        f"✅ TP3: {signal['tp3']:{fmt}}\n"
    )

    if pivot_note:
        msg += f"\n{pivot_note}\n"

    msg += (
        f"\n━━ PIVOT MAP ━━\n"
        f"🔴 R1: {signal['r1']:{fmt}}\n"
        f"⚪ Pivot: {signal['pivot']:{fmt}}\n"
        f"🟢 S1: {signal['s1']:{fmt}}\n"
        f"📊 PDH: {signal['pdh']:{fmt}} | PDL: {signal['pdl']:{fmt}}\n\n"
        f"━━ ANALYSIS ━━\n"
        f"📝 {signal['analysis']}\n\n"
        f"💡 After {signal['mission']}, watch for\n"
        f"structure shift & trend continuation.\n\n"
        f"⚠️ AI-generated signal. Not financial advice.\n"
        f"Always manage your risk!\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    return msg
