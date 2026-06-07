"""
US Economic News Alert module.
Provides pre-release notifications before major economic data releases
and post-release analysis of the actual vs expected results.

Uses a built-in economic calendar + NewsAPI for context.
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
)

NEWSAPI_BASE = "https://newsapi.org/v2"

# Major US economic events that move markets
# Format: (event_name, typical_impact, description)
MAJOR_EVENTS = [
    ("Non-Farm Payrolls (NFP)", "HIGH", "US employment data - major market mover"),
    ("CPI (Consumer Price Index)", "HIGH", "Inflation data - affects Fed policy"),
    ("FOMC Rate Decision", "HIGH", "Federal Reserve interest rate decision"),
    ("GDP (Gross Domestic Product)", "HIGH", "Overall economic growth"),
    ("PPI (Producer Price Index)", "MEDIUM", "Wholesale inflation indicator"),
    ("Retail Sales", "MEDIUM", "Consumer spending strength"),
    ("ISM Manufacturing PMI", "MEDIUM", "Manufacturing sector health"),
    ("ISM Services PMI", "MEDIUM", "Services sector health"),
    ("Unemployment Claims", "MEDIUM", "Weekly jobless claims"),
    ("Core PCE Price Index", "HIGH", "Fed's preferred inflation gauge"),
    ("ADP Employment", "MEDIUM", "Private sector jobs preview"),
    ("Consumer Confidence", "LOW", "Consumer sentiment indicator"),
    ("Durable Goods Orders", "MEDIUM", "Business investment proxy"),
    ("Housing Starts", "LOW", "Real estate sector health"),
    ("Trade Balance", "LOW", "Import/export difference"),
]


async def get_upcoming_events(language: str = "en") -> str:
    """
    Generate AI-powered preview of upcoming major US economic events.
    Acts as a pre-release alert with expected impact analysis.

    Args:
        language: 'en' or 'id'

    Returns:
        Formatted message string
    """
    lang_instruction = (
        "Respond in Bahasa Indonesia." if language == "id"
        else "Respond in English."
    )

    # Get recent economic news for context
    news_context = await _fetch_economic_news()

    prompt = f"""You are a professional economic calendar analyst for forex traders.

{lang_instruction}

Based on your knowledge of the current economic calendar and the news context below, provide an alert about the NEXT upcoming major US economic data releases (within the next 1-3 days).

News Context:
{news_context}

For each upcoming event, provide:
1. Event name
2. Expected release time (EST)
3. Previous value
4. Market consensus/forecast (if known)
5. Potential market impact (HIGH/MEDIUM/LOW)
6. Which currency pairs will be most affected
7. Brief pre-release analysis (what to watch for)

Format it clearly for a Telegram message. Use emojis for readability.
List 2-4 upcoming events maximum.
End with a brief "Trader's Note" about overall market positioning ahead of these releases.

If you don't know exact upcoming dates, provide the most likely next releases based on the typical economic calendar schedule.
"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a forex economic calendar expert. Provide accurate pre-release analysis for traders.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=800,
        )

        content = response.choices[0].message.content.strip()
        return _format_news_alert(content, alert_type="pre")

    except Exception as e:
        logger.error(f"Error generating US news alert: {e}")
        return "⚠️ Failed to generate US News Alert. Please try again later."


async def get_news_review(language: str = "en") -> str:
    """
    Generate post-release analysis of recent US economic data.
    Analyzes actual vs expected and market reaction.

    Args:
        language: 'en' or 'id'

    Returns:
        Formatted message string
    """
    lang_instruction = (
        "Respond in Bahasa Indonesia." if language == "id"
        else "Respond in English."
    )

    news_context = await _fetch_economic_news()

    prompt = f"""You are a professional forex analyst providing post-release economic data review.

{lang_instruction}

Based on the recent economic news below, provide a POST-RELEASE review of the latest US economic data that was released today or yesterday.

News Context:
{news_context}

For each recently released data point, analyze:
1. Event name
2. Actual result vs Forecast vs Previous
3. Whether it was better/worse than expected
4. Immediate market reaction (USD strength/weakness)
5. Impact on major pairs (EUR/USD, GBP/USD, USD/JPY)
6. What this means for Fed policy outlook
7. Trading implication going forward

Format clearly for Telegram. Use emojis.
End with "Market Outlook" - brief summary of what traders should focus on next.
"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a forex analyst specializing in post-release economic data review and its market impact.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=800,
        )

        content = response.choices[0].message.content.strip()
        return _format_news_alert(content, alert_type="post")

    except Exception as e:
        logger.error(f"Error generating news review: {e}")
        return "⚠️ Failed to generate US News Review. Please try again later."


async def get_weekly_analysis(language: str = "en") -> str:
    """
    Generate comprehensive weekly market analysis.

    Args:
        language: 'en' or 'id'

    Returns:
        Formatted weekly analysis message
    """
    lang_instruction = (
        "Respond in Bahasa Indonesia." if language == "id"
        else "Respond in English."
    )

    news_context = await _fetch_economic_news()

    prompt = f"""You are a senior forex market strategist providing a weekly analysis report.

{lang_instruction}

Based on the news context and your market knowledge, provide a comprehensive WEEKLY ANALYSIS covering:

1. WEEK IN REVIEW
   - Key events that moved markets this week
   - Major pair movements (EUR/USD, GBP/USD, USD/JPY, AUD/USD, Gold)
   - Biggest winners/losers

2. TECHNICAL OUTLOOK
   - Key support/resistance levels for major pairs
   - Chart patterns forming
   - Important moving average levels

3. WEEK AHEAD PREVIEW
   - Major scheduled events next week
   - Key levels to watch
   - Potential catalysts for volatility

4. TRADE IDEAS
   - 2-3 potential setups for next week
   - Each with direction, key level, and rationale

5. RISK EVENTS
   - What could disrupt the market
   - Geopolitical factors to monitor

News Context:
{news_context}

Format for Telegram with clear sections and emojis. Be specific with price levels.
"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior forex strategist providing institutional-quality weekly market analysis.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=1200,
        )

        content = response.choices[0].message.content.strip()
        return _format_weekly_analysis(content)

    except Exception as e:
        logger.error(f"Error generating weekly analysis: {e}")
        return "⚠️ Failed to generate weekly analysis. Please try again later."


async def _fetch_economic_news() -> str:
    """Fetch recent US economic/macro news for context."""
    try:
        async with httpx.AsyncClient(timeout=15) as http_client:
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            response = await http_client.get(
                f"{NEWSAPI_BASE}/everything",
                params={
                    "q": (
                        "US economy OR Federal Reserve OR inflation OR "
                        "employment data OR GDP OR CPI OR NFP OR FOMC"
                    ),
                    "from": yesterday,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 8,
                    "apiKey": settings.NEWSAPI_KEY,
                },
            )
            response.raise_for_status()
            data = response.json()

            articles = data.get("articles", [])
            if not articles:
                return "No recent economic news available."

            context_lines = []
            for article in articles[:8]:
                title = article.get("title", "")
                desc = article.get("description", "")
                context_lines.append(f"- {title}: {desc}")

            return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Error fetching economic news: {e}")
        return "Unable to fetch recent news context."


def _format_news_alert(content: str, alert_type: str = "pre") -> str:
    """Format the news alert with header/footer."""
    if alert_type == "pre":
        header = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🖥 US NEWS ALERT\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
        )
    else:
        header = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🖥 US NEWS REVIEW\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
        )

    footer = (
        "\n\n━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ Not financial advice. Always do your own analysis.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    return f"{header}{content}{footer}"


def _format_weekly_analysis(content: str) -> str:
    """Format weekly analysis with header/footer."""
    header = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🖥 WEEKLY MARKET ANALYSIS\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    footer = (
        "\n\n━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ This is AI-generated analysis, not financial advice.\n"
        "Always manage your risk and do your own research.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    return f"{header}{content}{footer}"
