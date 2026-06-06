"""
Forex news fetcher.
Uses NewsAPI for forex/currency market news.
"""

import logging
from datetime import datetime, timedelta

import httpx

from config import settings

logger = logging.getLogger(__name__)

NEWSAPI_BASE = "https://newsapi.org/v2"

# Major forex pairs
TRACKED_PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/IDR"]


async def fetch_forex_news(limit: int = 5) -> dict:
    """
    Fetch latest forex market news.
    Returns dict with 'articles' list.
    """
    articles = []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            response = await client.get(
                f"{NEWSAPI_BASE}/everything",
                params={
                    "q": (
                        "forex OR currency market OR exchange rate "
                        "OR dollar OR EUR/USD OR central bank rate"
                    ),
                    "from": yesterday,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": limit,
                    "apiKey": settings.NEWSAPI_KEY,
                },
            )
            response.raise_for_status()
            data = response.json()

            for article in data.get("articles", [])[:limit]:
                articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "url": article.get("url", ""),
                    "published_at": article.get("publishedAt", ""),
                })

    except Exception as e:
        logger.error(f"Error fetching forex news: {e}")

    return {
        "category": "forex",
        "articles": articles,
        "tracked_pairs": TRACKED_PAIRS,
        "fetched_at": datetime.utcnow().isoformat(),
    }
