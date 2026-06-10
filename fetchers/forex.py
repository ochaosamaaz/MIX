"""
Forex news fetcher.
Uses NewsAPI for forex/currency market news with strict filtering.
"""

import logging
from datetime import datetime, timedelta

import httpx

from config import settings

logger = logging.getLogger(__name__)

NEWSAPI_BASE = "https://newsapi.org/v2"

# Major forex pairs
TRACKED_PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/IDR"]

# Forex-specific keywords for better filtering
FOREX_QUERY = (
    '"forex" OR "currency pair" OR "EUR/USD" OR "GBP/USD" '
    'OR "USD/JPY" OR "exchange rate" OR "central bank" '
    'OR "interest rate decision" OR "Federal Reserve" '
    'OR "ECB" OR "Bank of England" OR "Bank of Japan" '
    'OR "DXY" OR "dollar index" OR "currency market"'
)

# Keywords that indicate NON-forex news (to filter out)
EXCLUDE_KEYWORDS = [
    "russell 2000", "s&p 500", "nasdaq", "dow jones",
    "small-cap", "large-cap", "ipo", "earnings report",
    "real estate", "housing market", "mortgage",
    "startup", "venture capital", "fundraising",
]


async def fetch_forex_news(limit: int = 5) -> dict:
    """
    Fetch latest forex-specific market news.
    Filters out stock/real estate news that accidentally matches.
    Returns dict with 'articles' list.
    """
    articles = []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            response = await client.get(
                f"{NEWSAPI_BASE}/everything",
                params={
                    "q": FOREX_QUERY,
                    "from": yesterday,
                    "sortBy": "relevancy",
                    "language": "en",
                    "pageSize": limit * 3,  # Fetch more, then filter
                    "apiKey": settings.NEWSAPI_KEY,
                },
            )
            response.raise_for_status()
            data = response.json()

            for article in data.get("articles", []):
                title = article.get("title", "")
                description = article.get("description", "")
                combined_text = f"{title} {description}".lower()

                # Skip articles that are clearly NOT forex
                is_forex = True
                for exclude in EXCLUDE_KEYWORDS:
                    if exclude in combined_text:
                        is_forex = False
                        break

                if is_forex:
                    articles.append({
                        "title": title,
                        "description": description,
                        "source": article.get("source", {}).get("name", "Unknown"),
                        "url": article.get("url", ""),
                        "published_at": article.get("publishedAt", ""),
                    })

                if len(articles) >= limit:
                    break

    except Exception as e:
        logger.error(f"Error fetching forex news: {e}")

    return {
        "category": "forex",
        "articles": articles,
        "tracked_pairs": TRACKED_PAIRS,
        "fetched_at": datetime.utcnow().isoformat(),
    }
